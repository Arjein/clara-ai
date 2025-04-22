class DraftMessage:
    """
    A class to represent a draft message in an email client.
    """

    def __init__(self, threadId, subject: str, body: str, in_reply_to, references):
        self.thread_id = threadId
        self.subject = subject
        self.body = body
        self.in_reply_to = in_reply_to
        self.references = references

    def __repr__(self):
        return f"DraftMessage(threadId={self.thread_id}\nsubject={self.subject}\nbody={self.body}\nin_reply_to={self.in_reply_to}\nreferences={self.references})"
    
    def toJson(self):
        """
        Convert the DraftMessage object to a JSON-compatible dictionary.
        
        Returns:
            dict: A dictionary representation of the DraftMessage object.
        """
        return {
            'threadId': self.thread_id,
            'Subject': self.subject,
            'body': self.body,
            'In_Reply_To': self.in_reply_to,
            'References': self.references
        }
