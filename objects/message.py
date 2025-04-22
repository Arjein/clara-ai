class Message:
    """
    Base class for all message types in the system.
    Now modified to be non-abstract for database serialization/deserialization.
    """
    def __init__(self, message: dict):
        self.id = message.get('id')
        self.message_id = message.get('message_id')
        self.thread_id = message.get('thread_id')
        self.subject = message.get('subject')
        self.label_ids = message.get('label_ids')
        self.snippet = message.get('snippet')
        self.sender_name = message.get('sender_name')
        self.sender_email = message.get('sender_email')
        self.recipient_name = message.get('recipient_name')
        self.recipient_email = message.get('recipient_email')
        self.cc = message.get('cc')
        self.date = message.get('date')
        self.reply_to = message.get('reply_to')
        self.references = message.get('references')
        self.body_encrypted = message.get('body_encrypted')
        self.body = message.get('body')
        self.clean_body = message.get('clean_body')
        
    def extract_message(self, message):
        """
        Default implementation for the extract_message method.
        Subclasses should override this method to provide specific extraction logic.
        """
        # Default implementation just returns the message as is
        return message

    @classmethod
    def fromJson(cls, json_data):
        """
        Create a Message object from JSON data.
        
        Args:
            json_data (dict): The JSON data representing a message.
            
        Returns:
            Message: A new Message object initialized with the JSON data.
        """
        return cls(json_data)

    def toJson(self):
        return {
            'id': self.id,
            'message_id': self.message_id,
            'thread_id': self.thread_id,
            'subject': self.subject,
            'label_ids': self.label_ids,
            'snippet': self.snippet,
            'sender_name': self.sender_name,
            'sender_email': self.sender_email,
            'recipient_name': self.recipient_name,
            'recipient_email': self.recipient_email,
            'cc': self.cc,
            'date': self.date,
            'reply_to': self.reply_to,
            'references': self.references,
            'body_encrypted': self.body_encrypted,
            'body': self.body,
            'clean_body': self.clean_body
        }
    
    def __str__(self):
        return f"""------------------------
        MESSAGE\n
        id={self.id}
        thread_id={self.thread_id}
        message_id={self.message_id}
        label_ids={self.label_ids}
        subject={self.subject}
        snippet={self.snippet}
        sender_name={self.sender_name}
        sender_email={self.sender_email}
        recipient_name={self.recipient_name}
        recipient_email={self.recipient_email}
        cc={self.cc}
        date={self.date}
        reply_to={self.reply_to}
        references={self.references}
        body_encrypted={self.body_encrypted}
        body={self.body}
        clean_body={self.clean_body}
        )\n
        ------------------------\n
        """
