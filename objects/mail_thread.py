from abc import ABC, abstractmethod
from objects.message import Message
import datetime


class MailThread:
    """
    This class represents a mail thread in the system.
    """

    def __init__(self, threadDict: dict = None):
        if threadDict is None:
            threadDict = {}
            
        self.id = threadDict.get('id')
        self.histroy_id = threadDict.get('history_id')
        self.subject = threadDict.get('subject')
        self.messages = threadDict.get('messages', [])
        self.label_ids = threadDict.get('label_ids', [])
        self.last_updated = threadDict.get('last_updated', datetime.datetime.now())
        self.reply_class = threadDict.get('reply_class', None)
        self.pre_reply_class = threadDict.get('pre_reply_class', None)
        self.draft_ready = threadDict.get('draft_ready', None)
        self.replied = threadDict.get('replied', None)
        

    @classmethod
    def fromJson(cls, json_data):
        """
        Creates a MailThread object from a JSON serializable dictionary.
        
        Args:
            json_data (dict): The JSON dictionary containing thread data
            
        Returns:
            MailThread: A new MailThread object constructed from the JSON data
        """
        # Create a copy of the JSON data to avoid modifying the original
        thread_dict = json_data.copy()
        
        # Convert the ISO format date string back to datetime object if it exists
        if 'last_updated' in thread_dict and thread_dict['last_updated']:
            try:
                thread_dict['last_updated'] = datetime.datetime.fromisoformat(thread_dict['last_updated'])
            except (ValueError, TypeError):
                # If conversion fails, keep the original value
                pass
        
        # Convert message dictionaries to Message objects if they exist
        if 'messages' in thread_dict and thread_dict['messages']:
            messages = []
            for msg_data in thread_dict['messages']:
                if isinstance(msg_data, dict):
                    messages.append(Message.fromJson(msg_data))
                else:
                    messages.append(msg_data)
            thread_dict['messages'] = messages
        
        # Create and return a new MailThread object
        return cls(thread_dict)
    
    
    def toJson(self):
        """
        Converts the MailThread object to a JSON serializable dictionary.
        """
        message_list = [message.toJson() if hasattr(message, 'toJson') else message for message in self.messages]
        
        return {
            'id': self.id,
            'history_id': self.histroy_id,  # Note: keeping original typo
            'subject': self.subject,
            'messages': message_list,
            'label_ids': self.label_ids,
            'last_updated': self.last_updated.isoformat() if isinstance(self.last_updated, datetime.datetime) else self.last_updated,
            'pre_reply_class': self.pre_reply_class,
            'reply_class': self.reply_class,
            'draft_ready': self.draft_ready,
            'replied': self.replied,
        }

    def __str__(self):
        return f"MailThread(id:{self.id}\nSubject: {self.subject}\nPre_reply_class: {self.pre_reply_class}\nReply_class={self.reply_class}\nDraft_ready: {self.draft_ready}\nReplied:{self.replied}\nLast_updated: {self.last_updated})"

    def create_prompt_for_response(self):
        """
        Returns the messages in chronological order.
        """
        sorted_mails = sorted(self.messages, key=lambda x: x.date)
        result = ''
        for mail in sorted_mails:
            result += f'Date: {mail.date} \nFrom: {mail.sender_email}\nTo: {mail.recipient_email}\n'
            result+= mail.subject
            body_content = mail.clean_body if hasattr(mail, 'clean_body') else mail.body
            result += f'\n{body_content}\n'
            result += '---\n'
            
        
        return result
    
    def save_thread(self, base_path='threads'):
        """
        Save the thread to a file.
        
        Args:
            base_path (str): Base directory to save threads
        
        Returns:
            str: Path where the thread was saved
        """
        import os
        import json
        
        # Create directories if they don't exist
        os.makedirs(base_path, exist_ok=True)
        os.makedirs(f"{base_path}/draft_ready", exist_ok=True)
        
        # Determine file paths for both possible locations
        standard_path = f"{base_path}/thread_{self.id}.json"
        draft_ready_path = f"{base_path}/draft_ready/thread_{self.id}.json"
        
        # Determine correct current path based on thread status
        if self.draft_ready:
            current_path = draft_ready_path
            old_path = standard_path
        else:
            current_path = standard_path
            old_path = draft_ready_path
        
        # Remove file from incorrect location if it exists
        if os.path.exists(old_path):
            os.remove(old_path)
            print(f"Removed outdated thread file: {old_path}")
        
        # Write thread to correct location
        with open(current_path, 'w') as file:
            file.write(json.dumps(self.toJson(), indent=4))
        
        print(f"Thread saved to: {current_path}")
        return current_path
    
    def extract_thread(self, thread):
        """
        This method should be implemented by subclasses to extract thread information
        """
        pass


