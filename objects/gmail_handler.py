import base64
import datetime
from email.message import EmailMessage
import json
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pickle

import requests
from objects.gmail_thread import GmailThread
from user import AppUser
from labels import clara_labels
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/gmail.labels',
    'https://www.googleapis.com/auth/gmail.modify',
    ]
class GmailHandler:
    def __init__(self):
        self.service = self.authenticate_gmail()
        self.labels_dict = self.initialize_labels()
        AppUser.label_id_encode_dict = self.labels_dict


    def initialize_labels(self):
        """Initialize labels for the user and return a name-to-id mapping."""
        # Get existing labels first - avoid duplicate API calls
        label_api_response = self.service.users().labels().list(userId='me').execute()
        
        # Create both a list of names and a name-to-id mapping in one pass
        existing_labels = {}
        for label in label_api_response.get('labels', []):
            existing_labels[label['name']] = label['id']
        
        # Track which labels were created
        created_labels = []
        
        # Create missing labels
        for c_label in clara_labels:
            label_name = c_label['name']
            if label_name not in existing_labels:
                print(f"Creating label: {label_name}")
                try:
                    # Make a clean copy of the label definition without problematic fields
                    label_to_create = {
                        "name": label_name,
                        "labelListVisibility": c_label.get("labelListVisibility", "labelShow"),
                        "messageListVisibility": c_label.get("messageListVisibility", "show")
                    }
                    
                    # Create the label and get its ID
                    result = self.service.users().labels().create(
                        userId='me',  # Use 'me' instead of AppUser.email for consistency
                        body=label_to_create
                    ).execute()
                    
                    # Add to our tracked labels
                    existing_labels[label_name] = result['id']
                    created_labels.append(label_name)
                except Exception as e:
                    print(f"Error creating label '{label_name}': {e}")
            else:
                print(f"Label already exists: {label_name}")
        
        # If we created any labels, we're done - return the complete mapping
        if not created_labels:
            return existing_labels
        
        # For extra safety, if labels were created, refresh our label list
        # This ensures we have the most current IDs
        if created_labels:
            print(f"Created {len(created_labels)} new labels")
            label_api_response = self.service.users().labels().list(userId='me').execute()
            # Update our mapping with fresh data
            for label in label_api_response.get('labels', []):
                existing_labels[label['name']] = label['id']
        
        return existing_labels

    @classmethod
    def authenticate_gmail(self):
        """Authenticate the user and return the Gmail API service."""
        creds = None
        # The file token.pickle stores the user's access and refresh tokens.
        if os.path.exists('token.json'):
            with open('token.json', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials/credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.json', 'wb') as token:
                pickle.dump(creds, token)
            AppUser.is_authenticated = True
        
        # Create the Gmail API service 
        service = build('gmail', 'v1', credentials=creds)
        
        # Get user profile and set AppUser properties
        try:
            profile = service.users().getProfile(userId='me').execute()
            AppUser.email = profile['emailAddress']
            print(f"Authenticated as: {AppUser.email}")
            
            # Optionally, get name information from People API
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
                    print(f"User: {AppUser.name} {AppUser.surname}")
                else:
                    # Fallback: Parse from email if name not available
                    email_parts = AppUser.email.split('@')[0].split('.')
                    if len(email_parts) >= 2:
                        AppUser.name = email_parts[0].capitalize() + ' (Parsed)'
                        AppUser.surname = email_parts[1].capitalize()+ ' (Parsed)'
                    else:
                        # If email doesn't contain a period, use as first name
                        AppUser.name = email_parts[0].capitalize()
                        AppUser.surname = ""
            except Exception as name_error:
                print(f"Could not fetch user name: {name_error}")
                # Parse name from email address as fallback
                email_name = AppUser.email.split('@')[0]
                AppUser.name = email_name.split('.')[0].capitalize() if '.' in email_name else email_name
                AppUser.surname = email_name.split('.')[1].capitalize() if '.' in email_name else ""
        except Exception as profile_error:
            print(f"Could not fetch user profile: {profile_error}")
        
        return service

    def fetch_single_thread(self, thread_id):
        """
        Fetch a single thread by ID.
        
        Args:
            thread_id: The ID of the thread to fetch.
        
        Returns:
            GmailThread: The fetched thread object.
        """
        try:
            # Get thread data by ID
            tdata = self.service.users().threads().get(userId='me', id=thread_id).execute()
            thread =  GmailThread(tdata)
            thread.save_thread(self)
            return thread
        
        except Exception as error:
            print(f'[DEBUG] An error occurred fetching thread {thread_id}: {error}')
            return None
        
    def fetch_threads(self, user_id='me', query='', limit=10):
        """
        Get all the threads from the user's mailbox that match the query.
        Returns a tuple of (threads requiring response, all threads)
        
        Args:
            service: Gmail API service
            user_id: User ID to fetch threads for (default: 'me')
            query: Query string to filter threads
            limit: Maximum number of threads to fetch
            analyze_threads: Whether to analyze threads during fetch (default: True)
        
        Returns:
            tuple: (threads requiring response, all threads)
        """
        try:
            # Initialize empty lists for threads
            all_threads: GmailThread = []
            print(f"[DEBUG] Starting thread fetch with query: '{query}'")
            # Get threads from Gmail API
            threads = self.service.users().threads().list(userId=user_id, q=query, maxResults=limit).execute().get('threads', [])
            
            if not threads:
                print("[DEBUG] No threads found matching query in Gmail API")
                return []
                
            print(f"[DEBUG] Found {len(threads)} threads in Gmail API, processing details...")
            
            # Process each thread
            for thread in threads:
                try:
                    # Get thread data by ID
                    tdata = self.service.users().threads().get(userId=user_id, id=thread["id"]).execute()
                    thread_object = GmailThread(tdata)
                    if not thread_object.pre_reply_class and thread_object.replied == False:
                        thread_object.label_ids.append(self.labels_dict['CLARA - IGNORED'])
                        
                    all_threads.append(thread_object)
                    
                except Exception as thread_error:
                    print(f"[DEBUG] Error processing thread {thread.get('id', 'unknown')}: {str(thread_error)}")
                    continue
                
            print(f"[DEBUG] Processed {len(all_threads)} total threads!")
            
            # Save each thread using its save_thread method
            for thread in all_threads:
                thread.save_thread(self)
            
            return all_threads
        
        except Exception as error:
            print(f'[DEBUG] An error occurred fetching threads: {error}')
            import traceback
            print(traceback.format_exc())
            return []
        

    
    def create_draft(self, thread: GmailThread, response_clean):
        

        # Make sure thread has all the necessary information
        print(f"Thread ID: {thread.id}")
        print(f"Last message ID: {thread.messages[-1].message_id}")
        print(f"Subject: {thread.subject}")

        # Create the draft
        draft = EmailMessage()
        draft.set_content(response_clean)

        # Make sure the subject matches EXACTLY - Gmail is strict about this
        # If the original doesn't have "Re:", don't add it
        original_subject = thread.subject
        draft['Subject'] = original_subject

        # Set proper headers for a reply
        draft['In-Reply-To'] = thread.messages[-1].reply_to
        # References should include the whole chain of message IDs
        references = []
        for message in thread.messages:
            if message.message_id:
                references.append(message.message_id)
        draft['References'] = ' '.join(references)

        # Set sender and recipient
        draft['To'] = thread.messages[-1].sender_email
        draft['From'] = thread.messages[-1].recipient_email

        # Encode the message
        encoded_message = base64.urlsafe_b64encode(draft.as_bytes()).decode()

        # Create the message with threadId
        create_message = {
            "message": {
                "raw": encoded_message,
                "threadId": thread.id  # This should be in the message metadata
            },
            "threadId": thread.id,  # This should be in the outer request
            
        }

        # Create the draft with explicit debugging
        try:
            draft = (
                self.service.users()
                .drafts()
                .create(userId="me", body=create_message)
                .execute()
            )
            print(f"Draft created successfully with ID: {draft.get('id')}")
            print(f"Draft thread ID: {draft.get('message', {}).get('threadId')}")
            thread.replied = True
            thread.reply_class = None
            thread.pre_reply_class = None
           # Burda Threadi bir daha api ile cek ki guncellensin
            
        except Exception as e:
            print(f"Error creating draft: {e}")

