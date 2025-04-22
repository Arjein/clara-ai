from datetime import datetime
from objects.gmail_message import GmailMessage
from objects.mail_thread import MailThread
from dateutil import parser

from user import AppUser  # Add this import


class GmailThread(MailThread):
    """
    This class represents a Gmail thread in the system.
    """

    def __init__(self, thread: dict):
        thread_dict = self.extract_thread(thread)
        super().__init__(thread_dict)

    def extract_thread(self, thread: dict):

        messages = [GmailMessage(message) for message in thread['messages']]   
        label_ids = []

        for message in messages:
            if message.label_ids:
                # Add any new label IDs that aren't already in our list
                for label_id in message.label_ids:
                    if label_id not in label_ids and label_id != 'SENT' and label_id != 'DRAFT':
                        label_ids.append(label_id)
        print('Label IDs:', label_ids)

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
                        print(f"Warning: Could not parse date value: {message.date}, Error: {e}")
        
        last_updated = max(valid_dates) if valid_dates else datetime.now()
        
        # Make this bETTERRR
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
            'replied': any(label in messages[-1].label_ids for label in ['SENT', 'DRAFT']),
            'pre_reply_class': all(label in messages[-1].label_ids for label in ['IMPORTANT', 'CATEGORY_PERSONAL']),
        }
        return extracted_thread
    

    def save_thread(self, gmail_handler=None, base_path='threads'):
        super().save_thread()
        
        label_modifications = {
                'addLabelIds': self.label_ids,
            }
        
        gmail_handler.service.users().threads().modify(id=self.id, userId='me', body=label_modifications).execute()

        
        

        
