"""
Main Gmail Handler

This module implements the Facade design pattern to provide a unified interface
to the complex Gmail API subsystem. The GmailHandler coordinates all Gmail operations
through specialized component classes, including:

- Authentication and user profile management
- Label creation and application
- Thread fetching and organization
- Message composition and sending

By centralizing these operations, the GmailHandler simplifies client code
and provides a consistent API for interacting with Gmail while delegating
the actual implementation to specialized components.
"""
import logging
from objects.gmail_auth import GmailAuthManager
from objects.gmail_label_manager import GmailLabelManager
from objects.gmail_thread_manager import GmailThreadManager
from objects.gmail_message_composer import GmailMessageComposer

class GmailHandler:
    """
    Main facade class to handle Gmail operations by coordinating specialized components.
    
    This class follows the Facade design pattern to simplify access to the Gmail API
    by providing a high-level interface that delegates to specialized components.
    It maintains backward compatibility with existing code while providing a more
    modular and maintainable implementation.
    """
    
    def __init__(self):
        """
        Initialize the Gmail handler and its component managers.
        
        The initialization process:
        1. Sets up a logger for tracking operations
        2. Authenticates with Gmail API
        3. Initializes all specialized components with the authenticated service
        4. Ensures all required labels exist
        
        This creates a fully configured handler ready to perform Gmail operations.
        """
        self.logger = logging.getLogger("ClaraSecretary")
        
        # Initialize authentication manager and get the service
        self.auth_manager = GmailAuthManager()
        self.service = self.auth_manager.authenticate()
        
        # Initialize component managers with the authenticated service
        self.label_manager = GmailLabelManager(self.service)
        self.labels_dict = self.label_manager.initialize_labels()
        
        self.thread_manager = GmailThreadManager(self.service, self.label_manager)
        self.message_composer = GmailMessageComposer(self.service)
    
    @classmethod
    def authenticate_gmail(cls):
        """
        Class method for backward compatibility with existing code.
        
        This static method maintains compatibility with older code that directly
        called the authenticate_gmail method. It delegates to the GmailAuthManager.
        
        Returns:
            googleapiclient.discovery.Resource: Authenticated Gmail API service object
        """
        auth_manager = GmailAuthManager()
        return auth_manager.authenticate()
    
    def fetch_single_thread(self, thread_id):
        """
        Fetch a single thread by ID.
        
        Retrieves a specific Gmail thread and processes it into a GmailThread object.
        This method delegates to the thread manager component for the actual implementation.
        
        Args:
            thread_id (str): The ID of the thread to fetch
            
        Returns:
            GmailThread: The fetched thread object or None on error
        """
        return self.thread_manager.fetch_single_thread(thread_id)
    
    def fetch_threads(self, user_id='me', query='', limit=10):
        """
        Get threads from the user's mailbox that match the query.
        
        This method fetches multiple Gmail threads matching a search query,
        with support for limiting results and specifying the user account.
        It delegates to the thread manager component for the actual implementation.
        
        Args:
            user_id (str): User ID to fetch threads for (default: 'me')
            query (str): Query string to filter threads using Gmail search syntax
            limit (int): Maximum number of threads to fetch
            
        Returns:
            list: List of GmailThread objects matching the query
        """
        return self.thread_manager.fetch_threads(query=query, limit=limit, user_id=user_id)
    
    def create_draft(self, thread, response_clean):
        """
        Create a draft email as a reply to a thread.
        
        This method creates a draft reply to an existing email thread,
        formatting it properly to maintain the conversation structure.
        It delegates to the message composer component for the actual implementation.
        
        Args:
            thread (GmailThread): GmailThread object to reply to
            response_clean (str): Plain text content for the email
            
        Returns:
            dict: The created draft object or None on error
        """
        return self.message_composer.create_draft(thread, response_clean)
    
    # Will not be used, maybe in the future.
    def send_message(self, draft_id):
        """
        Send a draft message.
        
        This method sends an existing draft email, converting it into a sent message.
        It delegates to the message composer component for the actual implementation.
        
        Args:
            draft_id (str): The ID of the draft to send
            
        Returns:
            dict: The sent message object or None on error
        """
        return self.message_composer.send_message(draft_id)

