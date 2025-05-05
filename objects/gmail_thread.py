from datetime import datetime
import logging
from objects.gmail_message import GmailMessage
from objects.mail_thread import MailThread
from dateutil import parser
from user import AppUser

class GmailThread(MailThread):

    def __init__(self, thread: dict):
        """
        Initialize a Gmail thread from raw Gmail API data.
        
        Args:
            thread (dict): Raw thread data from the Gmail API, containing
                messages and metadata about the conversation thread.
        """
        self.logger = logging.getLogger("ClaraSecretary")
        thread_dict = self.extract_thread(thread)
        super().__init__(thread_dict)

    def extract_thread(self, thread: dict):
        
        messages = [GmailMessage(message) for message in thread['messages']]   
        label_ids = []

        # Extract labels from messages
        for message in messages:
            if message.label_ids:
                # Add any new label IDs that aren't already in our list
                for label_id in message.label_ids:
                    if label_id not in label_ids and label_id != 'SENT' and label_id != 'DRAFT':
                        label_ids.append(label_id)

        # Process dates with a more flexible parser
        valid_dates = []
        for message in messages:
            if message.date:
                if isinstance(message.date, datetime):
                    valid_dates.append(message.date)
                else:
                    try:
                        # Use dateutil.parser instead of fromisoformat
                        date_obj = parser.parse(message.date)
                        valid_dates.append(date_obj)
                    except Exception as e:
                        self.logger.warning(f"Could not parse date value: {message.date}, Error: {e}")
        
        # Set last updated date to the most recent message date
        last_updated = max(valid_dates) if valid_dates else datetime.now()
        
        # Determine thread state based on labels
        replied = any(label in messages[-1].label_ids for label in ['SENT'])
        draft_ready = any(label in messages[-1].label_ids for label in ['DRAFT'])
        
        # Set appropriate reply classification based on thread state
        if replied:
            label_ids.append(AppUser.label_id_encode_dict['CLARA - REPLIED'])
            draft_ready = False
            reply_class = None
        else:
            # Classify thread based on Clara AI labels
            if AppUser.label_id_encode_dict['CLARA - IGNORED'] in label_ids:
                reply_class='ignore'
            elif AppUser.label_id_encode_dict['CLARA - FYI'] in label_ids:
                reply_class='notify'
            elif AppUser.label_id_encode_dict['CLARA - NEEDS YOUR INPUT'] in label_ids:
                reply_class='info_required'
            elif AppUser.label_id_encode_dict['CLARA - READY TO SEND'] in label_ids:
                reply_class='respond'
            else:
                reply_class = None

        # Create the structured thread dictionary
        extracted_thread = {
            'id': thread['id'],
            'history_id': thread['historyId'],
            'messages': messages,
            'subject': messages[0].subject,
            'label_ids': label_ids,
            'last_updated': last_updated,
            'latest_from': messages[-1].sender_email,
            'latest_to': messages[-1].recipient_email,
            'reply_class': reply_class,
            'pre_reply_class': any(label in messages[-1].label_ids for label in ['IMPORTANT', 'CATEGORY_PERSONAL']),
            'draft_ready': draft_ready,
            'replied': replied
        }
        return extracted_thread
    
    def save_thread(self, gmail_handler=None, base_path='threads'):
        
        # Skip API call if no handler provided (for testing/migration)
        if gmail_handler is None:
            self.logger.debug(f"Skipping label update for thread {self.id} (no Gmail API handler)")
            # Update the last email time in CosmosDB
            #AppUser.update_last_email_time(self.last_updated)
            return
            
        # Track labels to be removed
        removed_labels = []

        # Update labels based on thread state
        if self.replied:
            # If thread has been replied to, remove all classification labels
            for label_name in ['CLARA - IGNORED', 'CLARA - FYI', 
                             'CLARA - NEEDS YOUR INPUT', 'CLARA - READY TO SEND']:
                if AppUser.label_id_encode_dict[label_name] in self.label_ids:
                    removed_labels.append(AppUser.label_id_encode_dict[label_name])
                    self.label_ids.remove(AppUser.label_id_encode_dict[label_name])
        else:
            # If thread hasn't been replied to, remove the REPLIED label if present
            if AppUser.label_id_encode_dict['CLARA - REPLIED'] in self.label_ids:
                removed_labels.append(AppUser.label_id_encode_dict['CLARA - REPLIED'])
                self.label_ids.remove(AppUser.label_id_encode_dict['CLARA - REPLIED'])

        # Log label modifications for debugging
        self.logger.debug(f'AddLabelIds: {self.label_ids}')
        self.logger.debug(f'Removed Labels: {removed_labels}')
        
        # Apply label modifications via Gmail API
        label_modifications = {
            'addLabelIds': self.label_ids,
            "removeLabelIds": removed_labels
        }
        gmail_handler.service.users().threads().modify(id=self.id, userId='me', body=label_modifications).execute()
        
        # Update the last email time in CosmosDB
        #AppUser.update_last_email_time(self.last_updated)
        self.logger.debug(f"Updated user's last email time to {self.last_updated}")




