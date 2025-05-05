"""
Application User Singleton for Clara AI

This module provides a centralized way to manage the current user's information
and authentication state throughout the application.
"""
import json
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime

class AppUser:
    """
    Singleton class representing the current application user.
    
    This class stores the user's information and authentication state,
    providing global access to user data across the application.
    """
    
    # User information
    email = None
    name = None
    surname = None
    is_authenticated = False
    last_update = None
    
    # Gmail-specific data
    label_id_encode_dict = {}
    
    # JSON file path for user data
    USER_DATA_FILE = "user_data.json"
    
    @classmethod
    def get_full_name(cls):
        """Get the user's full name."""
        if cls.name and cls.surname:
            return f"{cls.name} {cls.surname}"
        elif cls.name:
            return cls.name
        else:
            return "Unknown User"
    
    @classmethod
    def load_from_json(cls, email: str) -> bool:
        """
        Load user data from JSON file.
        
        Args:
            email (str): Email of the user to load
            
        Returns:
            bool: True if user data was loaded successfully, False otherwise
        """
        logger = logging.getLogger("ClaraSecretary")
        
        try:
            if os.path.exists(cls.USER_DATA_FILE):
                with open(cls.USER_DATA_FILE, 'r') as file:
                    user_data = json.load(file)
                    
                    # Check if this is the same user
                    if user_data.get('email') == email:
                        cls.email = user_data.get('email')
                        cls.name = user_data.get('name')
                        cls.surname = user_data.get('surname')
                        cls.is_authenticated = user_data.get('is_authenticated', False)
                        cls.last_update = user_data.get('last_update')
                        cls.label_id_encode_dict = user_data.get('label_id_encode_dict', {})
                        
                        logger.info(f"Loaded user data for {email} from JSON file")
                        return True
            
            logger.info(f"No existing data found for user {email}")
            return False
        
        except Exception as e:
            logger.error(f"Error loading user data: {e}")
            return False

    @classmethod
    def save_as_json(cls) -> bool:
        """
        Save user data to JSON file.
        
        Returns:
            bool: True if user data was saved successfully, False otherwise
        """
        logger = logging.getLogger("ClaraSecretary")
        
        try:
            user_data = {
                'email': cls.email,
                'name': cls.name,
                'surname': cls.surname,
                'is_authenticated': cls.is_authenticated,
                'last_update': cls.last_update,
                'label_id_encode_dict': cls.label_id_encode_dict
            }
            
            with open(cls.USER_DATA_FILE, 'w') as file:
                json.dump(user_data, file, indent=2, default=str)
                
            logger.info(f"Saved user data for {cls.email} to JSON file")
            return True
            
        except Exception as e:
            logger.error(f"Error saving user data: {e}")
            return False
    
    @classmethod
    def update_last_email_time(cls, timestamp) -> bool:
        """
        Update the last email update time and save to JSON file.
        
        Args:
            timestamp: Timestamp of the last processed email
            
        Returns:
            bool: True if update was successful, False otherwise
        """
        logger = logging.getLogger("ClaraSecretary")
        
        try:
            # Convert to ISO format string if it's a datetime object
            if isinstance(timestamp, datetime):
                cls.last_update = timestamp.isoformat()
            else:
                cls.last_update = timestamp
                
            # Save the updated user data
            return cls.save_as_json()
            
        except Exception as e:
            logger.error(f"Error updating last email time: {e}")
            return False
    
    @classmethod
    def get_last_email_update_time(cls) -> Optional[str]:
        """
        Get the last email update time.
        
        Returns:
            Optional[str]: The last update time as an ISO format string, or None if not set
        """
        return cls.last_update