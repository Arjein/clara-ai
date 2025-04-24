"""
Database handler for Clara AI thread storage using SQLite.

This module provides functionality for storing and retrieving email thread data
using SQLite, providing better performance and query capabilities than
file-based storage while maintaining simplicity and zero-configuration.
"""

import json
import sqlite3
import os
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import threading

class ThreadDatabase:
    """
    Handles thread storage and retrieval using SQLite.
    
    This class provides methods to store, retrieve, and query email thread data
    in a SQLite database, offering improved performance and reliability over
    file-based storage while maintaining simplicity.
    """
    
    def __init__(self, db_path: str = "clara_threads.db"):
        """
        Initialize the thread database.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.logger = logging.getLogger("ClaraSecretary")
        self.db_path = db_path
        self.connection = None
        self.lock = threading.Lock()  # Thread safety
        
        # Initialize database if it doesn't exist
        self._initialize_db()
    
    def _get_connection(self):
        """Get a connection to the database with proper settings."""
        if self.connection is None:
            self.connection = sqlite3.connect(
                self.db_path, 
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
                check_same_thread=False  # Allow access from different threads
            )
            # Enable foreign keys and other settings
            self.connection.execute("PRAGMA foreign_keys = ON")
            # Use Row factory for better results
            self.connection.row_factory = sqlite3.Row
        
        return self.connection
    
    def _initialize_db(self):
        """Initialize the database schema if it doesn't exist."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Create threads table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS threads (
                id TEXT PRIMARY KEY,
                history_id TEXT,
                subject TEXT,
                last_updated TIMESTAMP,
                latest_from TEXT,
                latest_to TEXT,
                reply_class TEXT,
                pre_reply_class INTEGER,
                draft_ready INTEGER,
                replied INTEGER,
                thread_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Create labels table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS thread_labels (
                thread_id TEXT,
                label_id TEXT,
                PRIMARY KEY (thread_id, label_id),
                FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE
            )
            ''')
            
            # Create index
            cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_threads_last_updated ON threads(last_updated)
            ''')
            
            conn.commit()
            self.logger.info("Thread database initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise
    
    def save_thread(self, thread_data: Dict[str, Any], draft_ready: bool = False) -> bool:
        """
        Save a thread to the database.
        
        Args:
            thread_data: Thread data to save (from MailThread.toJson())
            draft_ready: Whether this thread has a draft ready
            
        Returns:
            bool: Success status
        """
        try:
            with self.lock:  # Thread safety
                conn = self._get_connection()
                cursor = conn.cursor()
                
                # Extract key fields
                thread_id = thread_data.get('id')
                history_id = thread_data.get('history_id')
                subject = thread_data.get('subject')
                last_updated = thread_data.get('last_updated')
                latest_from = thread_data.get('latest_from')
                latest_to = thread_data.get('latest_to')
                reply_class = thread_data.get('reply_class')
                pre_reply_class = 1 if thread_data.get('pre_reply_class') else 0
                draft_ready_value = 1 if thread_data.get('draft_ready') or draft_ready else 0
                replied = 1 if thread_data.get('replied') else 0
                
                # The thread_data is already serialized properly by MailThread.toJson()
                thread_json = json.dumps(thread_data)
                
                # Save thread data
                cursor.execute('''
                INSERT OR REPLACE INTO threads 
                (id, history_id, subject, last_updated, latest_from, latest_to, 
                 reply_class, pre_reply_class, draft_ready, replied, thread_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    thread_id, history_id, subject, last_updated, latest_from, latest_to,
                    reply_class, pre_reply_class, draft_ready_value, replied, thread_json
                ))
                
                # Clear existing labels
                cursor.execute('DELETE FROM thread_labels WHERE thread_id = ?', (thread_id,))
                
                # Save labels - ensure unique labels only
                labels = thread_data.get('label_ids', [])
                if labels:
                    # Use a set to ensure uniqueness
                    unique_labels = set(labels)
                    for label_id in unique_labels:
                        cursor.execute(
                            'INSERT INTO thread_labels (thread_id, label_id) VALUES (?, ?)',
                            (thread_id, label_id)
                        )
                
                conn.commit()
                self.logger.debug(f"Thread {thread_id} saved to database")
                return True
                
        except Exception as e:
            self.logger.error(f"Error saving thread to database: {e}")
            if conn:
                conn.rollback()
            return False
    
    def get_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a thread from the database by ID.
        
        Args:
            thread_id: ID of the thread to retrieve
            
        Returns:
            The thread data or None if not found
        """
        try:
            with self.lock:  # Thread safety
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('SELECT thread_data FROM threads WHERE id = ?', (thread_id,))
                result = cursor.fetchone()
                
                if result:
                    return json.loads(result[0])
                return None
                
        except Exception as e:
            self.logger.error(f"Error retrieving thread from database: {e}")
            return None
    
    def get_all_threads(self, limit: int = 100, draft_ready: bool = None) -> List[Dict[str, Any]]:
        """
        Get all threads from the database.
        
        Args:
            limit: Maximum number of threads to retrieve
            draft_ready: Filter by draft_ready status if not None
            
        Returns:
            List of thread data dictionaries
        """
        try:
            with self.lock:  # Thread safety
                conn = self._get_connection()
                cursor = conn.cursor()
                
                query = 'SELECT thread_data FROM threads'
                params = []
                
                if draft_ready is not None:
                    query += ' WHERE draft_ready = ?'
                    params.append(1 if draft_ready else 0)
                
                query += ' ORDER BY last_updated DESC LIMIT ?'
                params.append(limit)
                
                cursor.execute(query, params)
                results = cursor.fetchall()
                
                return [json.loads(row[0]) for row in results]
                
        except Exception as e:
            self.logger.error(f"Error retrieving threads from database: {e}")
            return []
    
    def get_latest_update_time(self) -> Optional[datetime]:
        """
        Get the latest thread update time.
        
        Returns:
            datetime: The latest thread update time or None
        """
        try:
            with self.lock:  # Thread safety
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('SELECT MAX(last_updated) FROM threads')
                result = cursor.fetchone()
                
                if result and result[0]:
                    return result[0]
                return None
                
        except Exception as e:
            self.logger.error(f"Error retrieving latest update time: {e}")
            return None
    
    def get_threads_by_classification(self, classification: str) -> List[Dict[str, Any]]:
        """
        Get threads by classification.
        
        Args:
            classification: The classification to filter by
            
        Returns:
            List of thread data dictionaries
        """
        try:
            with self.lock:  # Thread safety
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute(
                    'SELECT thread_data FROM threads WHERE reply_class = ? ORDER BY last_updated DESC',
                    (classification,)
                )
                results = cursor.fetchall()
                
                return [json.loads(row[0]) for row in results]
                
        except Exception as e:
            self.logger.error(f"Error retrieving threads by classification: {e}")
            return []
    
    def delete_thread(self, thread_id: str) -> bool:
        """
        Delete a thread from the database.
        
        Args:
            thread_id: ID of the thread to delete
            
        Returns:
            bool: Success status
        """
        try:
            with self.lock:  # Thread safety
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute('DELETE FROM threads WHERE id = ?', (thread_id,))
                conn.commit()
                
                deleted = cursor.rowcount > 0
                if deleted:
                    self.logger.debug(f"Thread {thread_id} deleted from database")
                
                return deleted
                
        except Exception as e:
            self.logger.error(f"Error deleting thread from database: {e}")
            if conn:
                conn.rollback()
            return False
    
    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None