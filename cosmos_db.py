"""
Azure CosmosDB Handler for Clara AI Users

This module provides a specialized interface for Azure CosmosDB operations
with MongoDB API, focusing specifically on user information storage.
"""

import os
import logging
import traceback
from typing import Dict, Any, Optional, Union
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from user import AppUser
import dotenv

# Load environment variables
_ = dotenv.load_dotenv()

class CosmosDB:
    """
    Singleton class for managing Azure CosmosDB connections and Users collection.
    
    This class provides a centralized interface for user operations:
    - Storing user profiles
    - Tracking last email update times
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance of CosmosDB handler."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """
        Initialize the CosmosDB connection and create Users collection if needed.
        
        Note: Direct instantiation is discouraged - use get_instance() instead.
        """
        self.logger = logging.getLogger("ClaraSecretary")
        
        # Get connection string from environment variables
        conn_string = os.getenv("MONGODB_CONNECTION_STRING")
        db_name = os.getenv("MONGODB_DATABASE", "clara-ai-database")
        
        if not conn_string:
            self.logger.error("CosmosDB connection string not found in environment variables")
            raise ValueError("CosmosDB connection string not found")
        
        try:
            # Connect to Azure CosmosDB
            self.client = MongoClient(conn_string)
            self.db = self.client[db_name]
            
            # Test connection
            self.client.admin.command('ping')
            self.logger.info("Connected to Azure CosmosDB successfully")
            
            # Initialize the Users collection only
            self.users_collection = self.db["Users"]
            
            # Create index on email field
            self.users_collection.create_index("email", unique=True)
            
            self.logger.debug("CosmosDB Users collection initialized successfully")
            
        except ConnectionFailure as e:
            self.logger.error(f"CosmosDB connection error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"CosmosDB initialization error: {e}")
            self.logger.debug(traceback.format_exc())
            raise
    
    def get_user(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get a user by email address.
        
        Args:
            email: User's email address
            
        Returns:
            User document or None if not found
        """
        try:
            return self.users_collection.find_one({"email": email})
        except Exception as e:
            self.logger.error(f"Error retrieving user from CosmosDB: {e}")
            return None
    
    def save_user(self, user_data: Dict[str, Any]) -> bool:
        """
        Save or update a user document.
        
        Args:
            user_data: User data to save
            
        Returns:
            Success status
        """
        try:
            email = user_data.get("email")
            if not email:
                self.logger.error("Cannot save user: email field is required")
                return False
            
            # Update user if exists, insert if not
            result = self.users_collection.update_one(
                {"email": email},
                {"$set": user_data},
                upsert=True
            )
            
            success = result.acknowledged
            if success:
                self.logger.debug(f"User {email} saved to CosmosDB")
            return success
            
        except Exception as e:
            self.logger.error(f"Error saving user to CosmosDB: {e}")
            return False
    
    def update_user_last_email_time(self, email: str, timestamp: Union[datetime, str]) -> bool:
        """
        Update the last email update time for a user.
        
        Args:
            email: User's email address
            timestamp: The datetime of the last email processed
            
        Returns:
            Success status
        """
        try:
            # Ensure timestamp is stored as ISO string
            if isinstance(timestamp, datetime):
                timestamp = timestamp.isoformat()
                
            result = self.users_collection.update_one(
                {"email": email},
                {"$set": {"last_email_update": timestamp}},
                upsert=True
            )
            
            success = result.acknowledged
            if success:
                self.logger.debug(f"Last email update time for {email} set to {timestamp}")
            return success
            
        except Exception as e:
            self.logger.error(f"Error updating last email time: {e}")
            return False
    
    def get_user_last_email_time(self, email: str) -> Optional[str]:
        """
        Get the last email update time for a user.
        
        Args:
            email: User's email address
            
        Returns:
            ISO format timestamp string or None if not found
        """
        try:
            user = self.users_collection.find_one(
                {"email": email},
                {"last_email_update": 1}
            )
            
            if user and "last_email_update" in user:
                return user["last_email_update"]
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting last email time: {e}")
            return None
    
    def close(self):
        """Close the database connection."""
        if hasattr(self, 'client') and self.client:
            self.client.close()
            self.logger.debug("CosmosDB connection closed")