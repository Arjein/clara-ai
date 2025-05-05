"""
Gmail Authentication Manager

This module handles all authentication-related operations with the Gmail API, including:
- OAuth 2.0 authentication flow
- Token refresh and persistence
- User profile retrieval and parsing
- Integration with the People API for additional user information

The GmailAuthManager class centralizes all authentication concerns to provide a clean
interface for obtaining an authenticated service object that can be used for Gmail operations.
"""
import os
import pickle
import logging
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from user import AppUser

class GmailAuthManager:
    """
    Handles Gmail API authentication and user profile retrieval.
    
    This class manages the OAuth 2.0 authentication flow with Google's APIs,
    handles credential persistence, and extracts user information from the
    authenticated profile. It serves as the entry point for all Gmail API
    interactions by providing an authenticated service object.
    """
    
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.compose',
        'https://www.googleapis.com/auth/userinfo.profile',
        'https://www.googleapis.com/auth/gmail.labels',
        'https://www.googleapis.com/auth/gmail.modify',
    ]
    
    def __init__(self, token_path='token.json', credentials_path='credentials/credentials.json'):
        """
        Initialize the authentication manager with paths to credential files.
        
        Args:
            token_path (str): Path to the token file that stores OAuth credentials
                between sessions. Default is 'token.json'.
            credentials_path (str): Path to the client secrets file downloaded
                from the Google API Console. Default is 'credentials/credentials.json'.
        """
        self.logger = logging.getLogger("ClaraSecretary")
        self.token_path = token_path
        self.credentials_path = credentials_path
        self.service = None
        self.flow = None
        
    def authenticate(self):
        """
        Authenticate with Gmail API and return the service object.
        
        This method handles the complete OAuth 2.0 flow, including:
        1. Loading existing credentials if available
        2. Refreshing expired credentials
        3. Initiating the OAuth flow if needed
        4. Saving credentials for future use
        5. Retrieving user profile information
        
        Returns:
            googleapiclient.discovery.Resource: The authenticated Gmail API service
                object that can be used for all Gmail operations.
        
        Raises:
            FileNotFoundError: If the credentials file doesn't exist.
            google.auth.exceptions.RefreshError: If token refresh fails.
        """
        creds = None
        # Load existing credentials if available
        if os.path.exists(self.token_path):
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
                
        # If no credentials or they're invalid, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES)
                creds = flow.run_local_server(port=0)
                
            # Save the credentials for the next run
            with open(self.token_path, 'wb') as token:
                pickle.dump(creds, token)
            AppUser.is_authenticated = True
        
        # Create the Gmail API service
        self.service = build('gmail', 'v1', credentials=creds)
        self._populate_user_info(creds)
        
        return self.service
    
    def _populate_user_info(self, creds):
        """
        Populate user information from Gmail and People API.
        
        This method:
        1. Retrieves the user's email address from Gmail API
        2. Attempts to get the user's name from People API
        3. Falls back to parsing the name from email if necessary
        
        Args:
            creds (google.oauth2.credentials.Credentials): The OAuth credentials
                to use for the API requests.
        """
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            AppUser.email = profile['emailAddress']
            self.logger.info(f"Authenticated as: {AppUser.email}")
            
            # Get additional user information from People API
            try:
                people_service = build('people', 'v1', credentials=creds)
                people_result = people_service.people().get(
                    resourceName='people/me',
                    personFields='names'
                ).execute()
                
                if 'names' in people_result and people_result['names']:
                    name_data = people_result['names'][0]
                    AppUser.name = name_data.get('givenName', 'Unknown')
                    AppUser.surname = name_data.get('familyName', 'User')
                    self.logger.info(f"User: {AppUser.name} {AppUser.surname}")
                
            except Exception as name_error:
                self.logger.error(f"Could not fetch user name: {name_error}")
                
        except Exception as profile_error:
            self.logger.error(f"Could not fetch user profile: {profile_error}")
    
    