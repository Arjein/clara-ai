"""
Gmail Message Composer

This module provides functionality for creating and sending email messages via Gmail, including:
- Creating draft replies to existing email threads
- Formatting emails with proper headers and metadata
- Encoding messages according to Gmail API requirements
- Managing email thread state after message creation

The GmailMessageComposer handles all aspects of email composition and delivery
while maintaining proper Gmail threading and conversation structure.
"""
import base64
import logging
from email.message import EmailMessage
from objects.retry_utils import exponential_backoff_retry
from googleapiclient.errors import HttpError

class GmailMessageComposer:
    """
    Handles creation of Gmail drafts and messages.
    
    This class provides specialized methods for composing and sending
    emails through the Gmail API, ensuring proper message formatting,
    threading, and metadata to maintain conversation context.
    """
    
    def __init__(self, service):
        """
        Initialize with an authenticated Gmail service.
        
        Args:
            service (googleapiclient.discovery.Resource): Authenticated Gmail API service
                object used to interact with the Gmail API.
        """
        self.logger = logging.getLogger("ClaraSecretary")
        self.service = service
        
    @exponential_backoff_retry(
        max_retries=4,
        base_delay=2.0,
        retryable_exceptions=(HttpError, ConnectionError, TimeoutError)
    )
    def _create_draft_api_call(self, user_id, body):
        """
        Create a draft message via Gmail API with retry logic.
        
        Args:
            user_id (str): The user ID to create the draft for
            body (dict): The draft data to create
            
        Returns:
            dict: The created draft object from the Gmail API
            
        Raises:
            HttpError: If the API call fails after retries
        """
        return self.service.users().drafts().create(userId=user_id, body=body).execute()
    
    @exponential_backoff_retry(
        max_retries=4,
        base_delay=2.0,
        retryable_exceptions=(HttpError, ConnectionError, TimeoutError)
    )
    def _send_message_api_call(self, user_id, body):
        """
        Send a draft message via Gmail API with retry logic.
        
        Args:
            user_id (str): The user ID to send the message as
            body (dict): The message data to send
            
        Returns:
            dict: The sent message object from the Gmail API
            
        Raises:
            HttpError: If the API call fails after retries
        """
        return self.service.users().drafts().send(userId=user_id, body=body).execute()
    
    def create_draft(self, thread, response_text):
        """
        Create a draft email as a reply to a thread.
        
        This method handles the complete process of drafting a reply to an existing
        email thread, including:
        1. Setting up proper email headers for thread continuity
        2. Formatting the message with sender, recipient, and subject information
        3. Encoding the message in Gmail's required format
        4. Creating the draft via the Gmail API
        5. Updating the thread state to reflect the draft creation
        
        Args:
            thread (GmailThread): GmailThread object containing the conversation
                to reply to. Must have messages with proper metadata.
            response_text (str): Plain text content for the email reply
            
        Returns:
            dict: The created draft object from the Gmail API or None on error
            
        Raises:
            Exception: If message creation or API request fails
        """
        try:
            # Log thread information for debugging
            self.logger.debug(f"Thread ID: {thread.id}")
            self.logger.debug(f"Last message ID: {thread.messages[-1].message_id}")
            self.logger.debug(f"Subject: {thread.subject}")

            # Create the draft email
            draft = EmailMessage()
            draft.set_content(response_text)

            # Use the exact original subject - Gmail is strict about this
            original_subject = thread.subject
            draft['Subject'] = original_subject

            # Set proper headers for a reply
            draft['In-Reply-To'] = thread.messages[-1].reply_to
            
            # References should include the whole chain of message IDs
            references = []
            for message in thread.messages:
                if message.message_id:
                    references.append(message.message_id)
            draft['References'] = ' '.join(references)

            # Set sender and recipient
            draft['To'] = thread.messages[-1].sender_email
            draft['From'] = thread.messages[-1].recipient_email

            # Encode the message
            encoded_message = base64.urlsafe_b64encode(draft.as_bytes()).decode()

            # Create the message with threadId
            create_message = {
                "message": {
                    "raw": encoded_message,
                    "threadId": thread.id
                },
                "threadId": thread.id
            }

            # Create the draft via API
            draft_result = self._create_draft_api_call(user_id="me", body=create_message)
            
            self.logger.info(f"Draft created successfully with ID: {draft_result.get('id')}")
            self.logger.debug(f"Draft thread ID: {draft_result.get('message', {}).get('threadId')}")
            
            # Update thread state
            thread.draft_ready = True
            thread.reply_class = None
            thread.pre_reply_class = None
            
            return draft_result
                
        except Exception as e:
            self.logger.error(f"Error creating draft: {e}")
            return None
            
    def send_message(self, draft_id):
        """
        Send a draft message.
        
        This method sends an existing draft email by its ID. It converts
        a saved draft into a sent message through the Gmail API.
        
        Args:
            draft_id (str): The ID of the draft to send
            
        Returns:
            dict: The sent message object from the Gmail API or None on error
            
        Raises:
            Exception: If the API request fails or draft doesn't exist
        """
        try:
            result = self._send_message_api_call(user_id="me", body={"id": draft_id})
            self.logger.info(f"Message sent successfully with ID: {result.get('id')}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            return None