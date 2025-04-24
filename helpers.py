import datetime
import json
import logging
import os
import traceback

from agents.email_response import EmailResponse
from objects.gmail_thread import GmailThread
from objects.mail_thread import MailThread


def load_saved_threads(base_path='threads'):
    """
    Load all saved threads from the database.
    
    This function retrieves all threads from the SQLite database
    and returns them as MailThread objects along with the latest timestamp.
    
    Args:
        base_path: Legacy parameter kept for backwards compatibility
        
    Returns:
        tuple: (list of thread objects, latest timestamp)
    """
    logger = logging.getLogger("ClaraSecretary")
    
    # Get the database instance
    db = GmailThread.get_db()
    
    # Create a list to hold all threads
    threads = []
    
    try:
        # Get normal threads from database
        normal_threads = db.get_all_threads(draft_ready=False)
        # Get draft_ready threads from database
        draft_ready_threads = db.get_all_threads(draft_ready=True)
        
        logger.info(f"Found {len(normal_threads)} active threads and {len(draft_ready_threads)} draft_ready threads")
        
        # Convert normal threads to MailThread objects
        for thread_data in normal_threads:
            try:
                thread = MailThread.fromJson(thread_data)
                threads.append(thread)
            except Exception as e:
                logger.error(f"Error loading thread {thread_data.get('id', 'unknown')}: {e}")
        
        # Convert draft_ready threads to MailThread objects
        for thread_data in draft_ready_threads:
            try:
                thread = MailThread.fromJson(thread_data)
                threads.append(thread)
            except Exception as e:
                logger.error(f"Error loading thread {thread_data.get('id', 'unknown')}: {e}")
        
        # Sort threads by last_updated (newest first)
        threads.sort(key=lambda t: t.last_updated.replace(tzinfo=datetime.timezone.utc) if t.last_updated 
                else datetime.datetime.min.replace(tzinfo=datetime.timezone.utc), 
                reverse=True)
        
        logger.info(f"Successfully loaded {len(threads)} threads")
        
        # Get the latest timestamp
        current_last_update_time = db.get_latest_update_time()
        
        # If no timestamp from DB, use the most recent thread
        if current_last_update_time is None and threads:
            current_last_update_time = threads[0].last_updated
    
    except Exception as e:
        logger.error(f"Error loading threads from database: {e}")
        logger.debug(traceback.format_exc())
        threads = []
        current_last_update_time = None
    
    return threads, current_last_update_time 


def get_threads_require_process(all_threads):
    """
    Get all threads that require processing.
    
    Args:
        all_threads: List of thread objects
        
    Returns:
        list: Threads that need processing
    """
    threads_require_process = []
    for thread in all_threads:
        if thread.pre_reply_class and thread.reply_class == None and thread.draft_ready == False and thread.replied == False:
            print('Did we reply to this thread: ', thread.replied)
            threads_require_process.append(thread)
    
    return threads_require_process


def process_thread(thread: GmailThread, gmail_handler, secretary_agent, logger=None):
    """
    Process a thread with the secretary agent.
    
    Args:
        thread: Thread to process
        gmail_handler: Gmail handler instance
        secretary_agent: Secretary agent instance
        logger: Optional logger instance
        
    Returns:
        bool: Success status
    """
    if logger is None:
        logger = logging.getLogger("ClaraSecretary")
    try: 
        body = thread.create_prompt_for_response()
        email_input = {
            'subject': thread.subject,
            'email_thread': body,
        }
        print(f"Processsing: {thread.subject}")
        response = secretary_agent.generate_response({"email_input": email_input})
        classification = response.get("classification_result")
        print('Classification:', classification)
        thread.reply_class = classification
        
        # Update the last_updated timestamp to now
        thread.last_updated = datetime.datetime.now()

        if classification != 'ignore' and classification != 'notify':
            # Create a draft response
            resp = response['structured_response']
            response_clean = EmailResponse.format_email(resp)
            gmail_handler.create_draft(thread, response_clean)
        
        label_to_add = None
        if classification == 'ignore':
            label_to_add = gmail_handler.labels_dict['CLARA - IGNORED']
        elif classification == 'notify':
            label_to_add = gmail_handler.labels_dict['CLARA - FYI']
        elif classification == 'info_required':
            label_to_add = gmail_handler.labels_dict['CLARA - NEEDS YOUR INPUT']
        elif classification == 'respond':
            label_to_add = gmail_handler.labels_dict['CLARA - READY TO SEND']
        
        # Only add label if it doesn't already exist in the list
        if label_to_add and label_to_add not in thread.label_ids:
            thread.label_ids.append(label_to_add)
            
        thread.save_thread(gmail_handler=gmail_handler)
        return True
    
    except Exception as e:
        print(f"Error processing thread {thread.id}: {e}")
        logger.error(f"Error processing thread {thread.id}: {e}")
        logger.debug(traceback.format_exc())
        thread.processing_error = str(e)
        thread.save_thread(gmail_handler=gmail_handler)
        return False




