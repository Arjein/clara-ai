"""
Gmail Utilities Module

This module provides utility functions for working with Gmail API data, including:
- Timestamp parsing and conversion
- Date formatting for Gmail queries
- Common data processing helpers

These utilities help standardize operations across the Clara AI Gmail components
and simplify complex data handling tasks.
"""
import datetime
import logging

logger = logging.getLogger("ClaraSecretary")

def parse_timestamp_from_query(query):
    try:
        # Extract timestamp from after: parameter
        if 'after:' not in query:
            return None, None
            
        date_part = query.split('after:')[-1].strip()
        # Check if it's a timestamp (numeric)
        if date_part.isdigit():
            # Convert timestamp to datetime
            timestamp = int(date_part)
            date_obj = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
            formatted_date = date_obj.strftime('%Y-%m-%d %H:%M:%S %Z')
            logger.debug(f"Date extracted from query timestamp: '{formatted_date}' (from timestamp {timestamp})")
            return timestamp, formatted_date
        else:
            # Handle as regular date format if not numeric
            logger.debug(f"Date extracted from query (non-timestamp): '{date_part}'")
            return date_part, date_part
    except Exception as e:
        logger.debug(f"Error parsing date from query: {e}")
        return None, None