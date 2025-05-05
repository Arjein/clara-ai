import logging
import traceback
from objects.gmail_thread import GmailThread
from objects.gmail_utils import parse_timestamp_from_query
from objects.retry_utils import exponential_backoff_retry
from googleapiclient.errors import HttpError

class GmailThreadManager:
    
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
        
        return self.service.users().threads().get(userId=user_id, id=thread_id).execute()
    
    @exponential_backoff_retry(
        max_retries=3,
        base_delay=2.0,
        retryable_exceptions=(HttpError, ConnectionError, TimeoutError)
    )
    def _list_threads(self, user_id, query, limit):
        response = self.service.users().threads().list(
            userId=user_id, 
            q=query, 
            maxResults=limit
        ).execute()
        return response.get('threads', [])
    
    def fetch_threads(self, query='', limit=10, user_id='me'):
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