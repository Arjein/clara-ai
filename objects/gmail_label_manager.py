"""
Gmail Label Manager

This module provides functionality for managing Gmail labels, including:
- Creating custom labels for Clara AI
- Retrieving and organizing existing labels
- Applying and removing labels from threads and messages

The GmailLabelManager ensures consistent label organization across the application
by providing a centralized way to interact with Gmail's labeling system.
"""
import logging
from labels import clara_labels
from user import AppUser

class GmailLabelManager:
    """
    Handles Gmail label creation, retrieval, and management.
    
    This class provides a centralized way to manage Gmail labels,
    ensuring that all required Clara AI labels exist and providing
    methods to apply or remove labels from threads.
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
        self.labels_dict = {}
        
    def initialize_labels(self):
        """
        Initialize labels for the user and return a name-to-id mapping.
        
        This method:
        1. Retrieves the user's existing Gmail labels
        2. Creates any missing Clara AI labels defined in the labels module
        3. Builds a dictionary mapping label names to their unique IDs
        4. Stores the mapping in the AppUser for global access
        
        Returns:
            dict: A mapping of label names to their IDs
        """
        # Get existing labels first - avoid duplicate API calls
        label_api_response = self.service.users().labels().list(userId='me').execute()
        
        # Create a name-to-id mapping
        existing_labels = {}
        for label in label_api_response.get('labels', []):
            existing_labels[label['name']] = label['id']
        
        # Track which labels were created
        created_labels = []
        
        # Create missing labels
        for c_label in clara_labels:
            label_name = c_label['name']
            if label_name not in existing_labels:
                self.logger.info(f"Creating label: {label_name}")
                try:
                    # Make a clean copy of the label definition
                    label_to_create = {
                        "name": label_name,
                        "labelListVisibility": c_label.get("labelListVisibility", "labelShow"),
                        "messageListVisibility": c_label.get("messageListVisibility", "show")
                    }
                    
                    # Create the label and get its ID
                    result = self.service.users().labels().create(
                        userId='me',
                        body=label_to_create
                    ).execute()
                    
                    # Add to our tracked labels
                    existing_labels[label_name] = result['id']
                    created_labels.append(label_name)
                except Exception as e:
                    self.logger.error(f"Error creating label '{label_name}': {e}")
        
        # If labels were created, refresh our label list to ensure we have the most current IDs
        if created_labels:
            self.logger.info(f"Created {len(created_labels)} new labels")
            label_api_response = self.service.users().labels().list(userId='me').execute()
            # Update our mapping with fresh data
            for label in label_api_response.get('labels', []):
                existing_labels[label['name']] = label['id']
        
        self.labels_dict = existing_labels
        # Store in AppUser for global access
        AppUser.label_id_encode_dict = existing_labels
        
        return existing_labels
        
    def apply_labels(self, thread_id, add_labels=None, remove_labels=None):
        """
        Apply or remove labels from a Gmail thread.
        
        This method modifies the labels applied to a Gmail thread by adding
        and/or removing specified labels in a single API call.
        
        Args:
            thread_id (str): The ID of the thread to modify
            add_labels (list): List of label IDs to add to the thread
            remove_labels (list): List of label IDs to remove from the thread
            
        Returns:
            dict: API response from the modify request
            
        Raises:
            Exception: If the API call fails
        """
        add_labels = add_labels or []
        remove_labels = remove_labels or []
        
        self.logger.debug(f'AddLabelIds: {add_labels}')
        self.logger.debug(f'Removed Labels: {remove_labels}')
        
        label_modifications = {
            'addLabelIds': add_labels,
            'removeLabelIds': remove_labels
        }
        
        response = self.service.users().threads().modify(
            id=thread_id, 
            userId='me', 
            body=label_modifications
        ).execute()
        
        return response