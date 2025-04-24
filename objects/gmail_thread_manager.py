"""
Gmail Thread Manager

This module handles all thread-related operations with the Gmail API, including:
- Fetching single threads by ID
- Retrieving multiple threads matching search criteria
- Processing thread metadata and content
- Managing thread state within the Clara AI system

The GmailThreadManager provides a robust interface for working with Gmail threads
while handling error cases and applying appropriate thread processing logic.
"""
import logging
import traceback
from objects.gmail_thread import GmailThread
from objects.gmail_utils import parse_timestamp_from_query
from objects.retry_utils import exponential_backoff_retry
from googleapiclient.errors import HttpError

class GmailThreadManager:
    """
    Handles Gmail thread fetching and processing.
    
    This class encapsulates all thread-related operations, providing methods
    to fetch both individual threads and collections of threads based on
    Gmail query syntax. It also applies processing logic to categorize and
    label threads appropriately for the Clara AI system.
    """
    
    def __init__(self, service, label_manager):
        """
        Initialize with authenticated Gmail service and label manager.
        
        Args:
            service (googleapiclient.discovery.Resource): Authenticated Gmail API service
                object used to interact with the Gmail API.
            label_manager (GmailLabelManager): Instance of GmailLabelManager
                used to manipulate labels on threads.
        """
        self.logger = logging.getLogger("ClaraSecretary")
        self.service = service
        self.label_manager = label_manager

    @exponential_backoff_retry(
        max_retries=3,
        base_delay=2.0,
        retryable_exceptions=(HttpError, ConnectionError, TimeoutError)
    )
    def _fetch_thread_data(self, user_id, thread_id):
        """
        Fetch thread data from Gmail API with retry logic.
        
        This method is wrapped with exponential backoff retry to handle
        transient API errors and rate limits gracefully.
        
        Args:
            user_id (str): The user ID to fetch data for
            thread_id (str): The ID of the thread to fetch
            
        Returns:
            dict: Raw thread data from Gmail API
            
        Raises:
            HttpError: If the API request fails after retries
        """
        return self.service.users().threads().get(userId=user_id, id=thread_id).execute()
    
    @exponential_backoff_retry(
        max_retries=3,
        base_delay=2.0,
        retryable_exceptions=(HttpError, ConnectionError, TimeoutError)
    )
    def _list_threads(self, user_id, query, limit):
        """
        List threads from Gmail API with retry logic.
        
        This method is wrapped with exponential backoff retry to handle
        transient API errors and rate limits gracefully.
        
        Args:
            user_id (str): The user ID to fetch data for
            query (str): Gmail search query
            limit (int): Maximum number of threads to return
            
        Returns:
            list: List of thread metadata from Gmail API
            
        Raises:
            HttpError: If the API request fails after retries
        """
        response = self.service.users().threads().list(
            userId=user_id, 
            q=query, 
            maxResults=limit
        ).execute()
        return response.get('threads', [])
        
    def fetch_single_thread(self, thread_id):
        """
        Fetch a single thread by ID.
        
        This method retrieves a specific Gmail thread, creates a GmailThread
        object with the data, and ensures thread state is persisted.
        
        Args:
            thread_id (str): The ID of the thread to fetch
            
        Returns:
            GmailThread: The fetched thread object or None on error
            
        Raises:
            Exception: Handles and logs any exceptions during thread retrieval
        """
        try:
            # Get thread data by ID
            tdata = self._fetch_thread_data(user_id='me', thread_id=thread_id)
            thread = GmailThread(tdata)
            thread.save_thread(self.label_manager)
            return thread
        
        except Exception as error:
            self.logger.error(f'An error occurred fetching thread {thread_id}: {error}')
            return None
    
    def fetch_threads(self, query='', limit=10, user_id='me'):
        """
        Get threads from the user's mailbox that match the query.
        
        This method provides the core functionality for retrieving Gmail threads:
        1. Executes a Gmail API search using the provided query
        2. Processes each retrieved thread into a GmailThread object
        3. Applies label classifications based on thread analysis
        4. Persists thread state with the label manager
        5. Handles errors gracefully at both the collection and individual thread level
        
        Args:
            query (str): Query string using Gmail's search syntax
                (e.g., 'from:example@gmail.com after:2023/01/01')
            limit (int): Maximum number of threads to fetch
            user_id (str): User ID to fetch threads for (default: 'me')
            
        Returns:
            list: List of GmailThread objects matching the query
            
        Raises:
            Exception: Handles and logs any exceptions during the process
        """
        try:
            all_threads = []
            self.logger.debug(f"Starting thread fetch with query: '{query}'")
            
            # Extract timestamp information from the query if present
            parse_timestamp_from_query(query)
            
            # Get threads from Gmail API
            threads = self._list_threads(user_id=user_id, query=query, limit=limit)
            
            if not threads:
                self.logger.debug("No threads found matching query in Gmail API")
                return []
                
            self.logger.debug(f"Found {len(threads)} threads in Gmail API, processing details...")
            
            # Process each thread
            for thread in threads:
                try:
                    # Get thread data by ID
                    tdata = self._fetch_thread_data(user_id=user_id, thread_id=thread["id"])
                    thread_object = GmailThread(tdata)
                    self.logger.debug(f'Extracted: {thread_object.subject}')
                    
                    # Add the IGNORED label if thread doesn't have any special status
                    if (thread_object.pre_reply_class != True and 
                        thread_object.draft_ready != True and 
                        thread_object.replied != True):
                        thread_object.label_ids.append(self.label_manager.labels_dict['CLARA - IGNORED'])
                        
                    all_threads.append(thread_object)
                except Exception as thread_error:
                    self.logger.error(f"Error processing thread {thread.get('id', 'unknown')}: {str(thread_error)}")
                    continue
                
            self.logger.debug(f"Processed {len(all_threads)} total threads!")
            
            # Save each thread using its save_thread method
            for thread in all_threads:
                thread.save_thread(self.label_manager)
            
            return all_threads
        
        except Exception as error:
            self.logger.error(f'An error occurred fetching threads: {error}')
            self.logger.debug(traceback.format_exc())
            return []