
from objects.message import Message
import base64
class GmailMessage(Message):
    def __init__(self, message: dict):
        message_dict = self.extract_message(message)
        super().__init__(message_dict)

    def extract_message(self, message):
        """
        Extracts the relevant information from the Gmail message.
        """
        # Extracting the relevant fields from the message
        headers = {header['name']: header['value'] for header in message['payload']['headers']}
        recipient = headers.get('To', None)
        from_ = headers.get('From', None)
        sender_name, sender_email = self.parse_sender(from_)
        recipient_name, recipient_email = self.parse_sender(recipient)
        subject = headers.get('Subject', None)
        cc = headers.get('Cc', None)
        thread_id = message.get('threadId', None)
        label_ids = message.get('labelIds', None)
        date = headers.get('Date', None)  # Extract the datetime from headers
        id = message['id']
        message_id = headers.get('Message-ID', None)
        reply_to = headers.get('In-Reply-To', None)
        references = headers.get('References', None)
        snippet = message['snippet']

        # Handle different possible message structures
        if ('parts' in message['payload'] and 
            len(message['payload']['parts']) > 0 and 
            'body' in message['payload']['parts'][0] and 
            'data' in message['payload']['parts'][0]['body']):
            body_encrypted = message['payload']['parts'][0]['body']['data']
        elif 'body' in message['payload'] and 'data' in message['payload']['body']:
            body_encrypted = message['payload']['body']['data']
        else:
            body_encrypted = ""  # Default to empty string if no body data found
            
        
        
        if body_encrypted:
            body = base64.urlsafe_b64decode(body_encrypted).decode("utf-8")
            clean_body = self.parse_email_body(body)
        else:
            body = ""
            clean_body = ""
            

        size = message.get('sizeEstimate', None)
        

        extracted_message = {
            'id': id,
            'message_id': message_id,
            'thread_id': thread_id,
            'subject' : subject,
            'label_ids': label_ids,
            'snippet': snippet,
            'sender_name': sender_name,
            'sender_email': sender_email,
            'recipient_name': recipient_name,
            'recipient_email': recipient_email,
            'cc': cc,
            'date': date,
            'reply_to': reply_to,
            'references': references,
            'body_encrypted': body_encrypted,        
            'body': body,
            'clean_body': clean_body  # Add the clean body without quoted content

        }
        
        return extracted_message
    
    def parse_email_body(self, body):
        """
        Parses the email body to extract only the new content, removing quoted replies.
        
        Returns:
            str: The cleaned body content without quoted parts
        """
        import re
        
        # Pattern to match common reply headers like "On [date], [name] wrote:"
        reply_header_patterns = [
            r'On\s+.*?wrote:',  # Matches "On [date/time], [name] wrote:"
            r'From:.*?\n',      # Matches "From: [sender]"
            r'-{3,}Original Message-{3,}',  # Matches "--- Original Message ---"
            r'_{3,}',          # Matches underscores used as separators
        ]
        
        # Join patterns with OR operator
        combined_pattern = '|'.join(reply_header_patterns)
        
        # Split by any of these patterns
        parts = re.split(combined_pattern, body, flags=re.IGNORECASE | re.DOTALL)
        
        if parts:
            # The first part should be the new content
            clean_body = parts[0].strip()
            return clean_body
        
        return body  # Return original if parsing fails

    @staticmethod
    def parse_sender(from_field):
        # Parse the sender field to extract name and email
        import re
        match = re.match(r"(.*) <(.*)>", from_field)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        return None, from_field.strip()
    
    def __str__(self):
        return super().__str__()
        