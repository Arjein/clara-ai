import json
import os

from objects.mail_thread import MailThread


class LocalDBManager:
    def __init__(self, db_path: str):
        self.basetablepath = 'threads'
    

    def upsert_thread(self, thread: MailThread):
        """Upsert a thread into the local database"""
        # Create the directory if it doesn't exist
        os.makedirs(self.basetablepath, exist_ok=True)
        
        # Save the thread to a JSON file
        thread_exists = self._find_thread_file(thread.thread_id)
        if thread_exists:
            # If the thread exists, update it
            self._update_thread(thread)
        else:
            # If the thread doesn't exist, create a new one
            self._create_thread(thread)

        file_path = os.path.join(self.basetablepath, f"thread_{thread.thread_id}.json")
        with open(file_path, 'w') as file:
            json.dump(thread.toJson(), file, indent=4)
    
    def _create_thread(self, thread: MailThread):
        """Create a new thread file"""
        file_path = os.path.join(self.basetablepath, f"thread_{thread.thread_id}.json")
        with open(file_path, 'w') as file:
            json.dump(thread.toJson(), file, indent=4)
        print(f"Thread {thread.thread_id} created at {file_path}")

    def _update_thread(self, thread: MailThread):
        """Update an existing thread file"""
        file_path = os.path.join(self.basetablepath, f"thread_{thread.thread_id}.json")
        with open(file_path, 'w') as file:
            json.dump(thread.toJson(), file, indent=4)
        print(f"Thread {thread.thread_id} updated at {file_path}")


    def _find_thread_file(self, thread_id: str) -> str:
        """Find the file path for a given thread ID"""
        file_path = os.path.join(self.basetablepath, f"thread_{thread_id}.json")
        if os.path.exists(file_path):
            return file_path
        return None