import datetime
import json
import logging
import os
import traceback

from agents.email_response import EmailResponse
from objects.gmail_thread import GmailThread
from objects.mail_thread import MailThread


def load_saved_threads(base_path='threads'):
    """Load all saved thread JSON files and initialize MailThread objects"""
    threads = []
    
    # Make sure both directories exist
    os.makedirs(base_path, exist_ok=True)
    os.makedirs(os.path.join(base_path, "draft_ready"), exist_ok=True)
    
    # Get files from main threads directory
    thread_files = [f for f in os.listdir(base_path) 
                   if f.startswith("thread_") and f.endswith(".json")]
    
    # Get files from replied directory
    replied_files = [f for f in os.listdir(os.path.join(base_path, "draft_ready")) 
                    if f.startswith("thread_") and f.endswith(".json")]
    
    print(f"Found {len(thread_files)} active threads and {len(replied_files)} draft_ready threads")
    
    # Process main thread files
    for file_name in thread_files:
        file_path = os.path.join(base_path, file_name)
        try:
            with open(file_path, 'r') as file:
                thread_data = json.load(file)
                thread = MailThread.fromJson(thread_data)
                threads.append(thread)
        except Exception as e:
            print(f"Error loading thread file {file_name}: {e}")
    
    # Process replied thread files
    for file_name in replied_files:
        file_path = os.path.join(base_path, "draft_ready", file_name)
        try:
            with open(file_path, 'r') as file:
                thread_data = json.load(file)
                thread = MailThread.fromJson(thread_data)
                threads.append(thread)
        except Exception as e:
            print(f"Error loading thread file {file_name}: {e}")
    
    # Sort threads by last_updated (newest first)
    threads.sort(key=lambda t: t.last_updated.replace(tzinfo=datetime.timezone.utc) if t.last_updated 
             else datetime.datetime.min.replace(tzinfo=datetime.timezone.utc), 
             reverse=True)
    
    print(f"Successfully loaded {len(threads)} threads")
    current_last_update_time = threads[0].last_updated if threads else None
    return threads, current_last_update_time 



def get_threads_require_process(all_threads):
    
    threads_require_process = []
    for thread in all_threads:
        if thread.pre_reply_class and thread.reply_class == None and thread.draft_ready == False and thread.replied == False:
            print('Did we reply to this thread: ', thread.replied)
            threads_require_process.append(thread)
    
    return threads_require_process

def process_thread(thread: GmailThread, gmail_handler, secretary_agent, logger=None):
    if logger is None:
        logger = logging.getLogger("ClaraSecretary")
    try: 
        body = thread.create_prompt_for_response()
        email_input = {
            'subject': thread.subject,
            'email_thread': body,
        }
        print(f"Processsing: {thread.subject}")
        #response = secretary_agent.secretary_agent.invoke({"email_input": email_input})
        response = secretary_agent.generate_response({"email_input": email_input})
        classification = response.get("classification_result")
        print('Classification:', classification)
        thread.reply_class = classification
        
        #TODO: Update the last_updated timestamp to now  Not sure how it works 
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




