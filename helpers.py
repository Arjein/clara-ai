import datetime
import logging
import traceback
from user import AppUser
from agents.email_response import EmailResponse


def load_saved_threads(base_path='threads'):
    """
    Get the last email update time from CosmosDB and return an empty thread list.
    
    This function no longer loads threads from the file system but instead
    just retrieves the last email update time from CosmosDB.
    
    Args:
        base_path: Legacy parameter kept for backwards compatibility
        
    Returns:
        tuple: (empty list, last update timestamp from CosmosDB)
    """
    logger = logging.getLogger("ClaraSecretary")
    
    try:
        # Get the user's last email update time from CosmosDB
        current_last_update_time = AppUser.get_last_email_update_time()
        logger.info("Retrieved last email update time from CosmosDB")
        
        # If timestamp is a string, convert to datetime
        if isinstance(current_last_update_time, str):
            try:
                current_last_update_time = datetime.datetime.fromisoformat(current_last_update_time)
                logger.info(f"Converted timestamp from database: {current_last_update_time}")
            except ValueError:
                logger.warning(f"Invalid timestamp format in database: {current_last_update_time}")
                current_last_update_time = None
    
    except Exception as e:
        logger.error(f"Error retrieving last email update time: {e}")
        logger.debug(traceback.format_exc())
        current_last_update_time = None
    
    # Return empty threads list and last update time
    return [], current_last_update_time 


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


def process_thread(thread, gmail_handler, secretary_agent, logger=None):
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
        
        # Apply label changes through Gmail API
        label_modifications = {
            'addLabelIds': thread.label_ids,
            "removeLabelIds": []
        }
        gmail_handler.service.users().threads().modify(id=thread.id, userId='me', body=label_modifications).execute()
        
        # Update last email time in CosmosDB after successful processing
        AppUser.update_last_email_time(thread.last_updated)
        logger.info(f"Updated last email time in CosmosDB to {thread.last_updated}")
        
        return True
    
    except Exception as e:
        print(f"Error processing thread {thread.id}: {e}")
        logger.error(f"Error processing thread {thread.id}: {e}")
        logger.debug(traceback.format_exc())
        thread.processing_error = str(e)
        return False




