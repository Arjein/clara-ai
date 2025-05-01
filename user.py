"""
Application User Singleton for Clara AI

This module provides a centralized way to manage the current user's information
and authentication state throughout the application.
"""
import logging
from typing import Dict, Any, Optional

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
    
    # Gmail-specific data
    label_id_encode_dict = {}
    
    @classmethod
    def get_full_name(cls):
        """Get the user's full name."""
        if cls.name and cls.surname:
            return f"{cls.name} {cls.surname}"
        elif cls.name:
            return cls.name
        elif cls.email:
            # Extract name from email
            return cls.email.split('@')[0]
        else:
            return "Unknown User"
    
    @classmethod
    def get_user_id(cls):
        """Get a consistent user ID for the database."""
        return cls.email or "default_user"
    
    @classmethod
    def save_to_db(cls):
        """Save the current user information to CosmosDB."""
        if not cls.email:
            return False
        
        try:
            from cosmos_db import CosmosDB
            cosmos_db = CosmosDB.get_instance()
            
            user_data = {
                "email": cls.email,
                "name": cls.name,
                "surname": cls.surname,
                "full_name": cls.get_full_name()
            }
            
            return cosmos_db.save_user(user_data)
        except Exception as e:
            logger = logging.getLogger("ClaraSecretary")
            logger.error(f"Error saving user to database: {e}")
            return False
    
    @classmethod
    def load_from_db(cls, email: str) -> bool:
        """
        Load user information from CosmosDB.
        
        Args:
            email: User's email address
            
        Returns:
            bool: Success status
        """
        if not email:
            return False
        
        try:
            from cosmos_db import CosmosDB
            cosmos_db = CosmosDB.get_instance()
            
            user_data = cosmos_db.get_user(email)
            if not user_data:
                return False
            
            cls.email = user_data.get("email")
            cls.name = user_data.get("name")
            cls.surname = user_data.get("surname")
            
            return True
        except Exception as e:
            logger = logging.getLogger("ClaraSecretary")
            logger.error(f"Error loading user from database: {e}")
            return False
    
    @classmethod
    def get_last_email_update_time(cls) -> Optional[str]:
        """Get the user's last email update time from CosmosDB."""
        if not cls.email:
            return None
        
        try:
            from cosmos_db import CosmosDB
            cosmos_db = CosmosDB.get_instance()
            # TODO EDIT THIS
            return  #cosmos_db.get_user_last_email_time(cls.email)
        except Exception as e:
            logger = logging.getLogger("ClaraSecretary")
            logger.error(f"Error getting last email update time: {e}")
            return None
    
    @classmethod
    def update_last_email_time(cls, timestamp):
        """Update the user's last email update time in CosmosDB."""
        if not cls.email:
            return False
        
        try:
            from cosmos_db import CosmosDB
            cosmos_db = CosmosDB.get_instance()
            
            return None #cosmos_db.update_user_last_email_time(cls.email, timestamp)
        except Exception as e:
            logger = logging.getLogger("ClaraSecretary")
            logger.error(f"Error updating last email time: {e}")
            return False



