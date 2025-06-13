"""
SQLite database module for storing YouTube video information.
"""

import sqlite3
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
import sys

# Configure logger
logger = logging.getLogger(__name__)

class YouTubeDatabase:
    """Database handler for YouTube video information."""
    
    def __init__(self, db_path: str = None):
        """
        Initialize the database connection.
        
        Args:
            db_path: Optional path to the database file
        """
        try:
            # Get the project root directory (2 levels up from this file)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            
            # Create data directory if it doesn't exist
            data_dir = os.path.join(project_root, 'data')
            if not os.path.exists(data_dir):
                logger.info(f"Creating data directory at {data_dir}")
                os.makedirs(data_dir)
            
            # Set default database path if not provided
            if db_path is None:
                db_path = os.path.join(data_dir, 'youtube_videos.db')
            
            logger.info(f"Using database at: {db_path}")
            
            # Ensure the directory exists
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
            
            # Test if we can write to the directory
            test_file = os.path.join(os.path.dirname(db_path), '.test_write')
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                logger.info("Directory is writable")
            except Exception as e:
                logger.error(f"Cannot write to directory: {e}")
                raise
            
            self.conn = sqlite3.connect(db_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            
            # Test the connection
            self.cursor.execute("SELECT 1")
            logger.info("Database connection successful")
            
            # Create tables if they don't exist
            self._create_tables()
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def _create_tables(self):
        """Create necessary tables if they don't exist."""
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS videos (
                    url TEXT PRIMARY KEY,
                    title TEXT,
                    channel TEXT,
                    length TEXT,
                    views TEXT,
                    upload_date TEXT,
                    thumbnail_url TEXT,
                    is_shorts BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            self.conn.commit()
            logger.info("Tables created successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise

    def add_video(self, video_data: Dict[str, Any]) -> bool:
        """
        Add a video to the database.
        
        Args:
            video_data: Dictionary containing video information
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO videos 
                (url, title, channel, length, views, upload_date, thumbnail_url, is_shorts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                video_data['url'],
                video_data['title'],
                video_data['channel'],
                video_data['length'],
                video_data['views'],
                video_data.get('upload_date'),
                video_data.get('thumbnail_url', 'Unknown'),
                video_data.get('is_shorts', False)
            ))
            self.conn.commit()
            logger.info(f"Added video: {video_data['url']}")
            return True
        except Exception as e:
            logger.error(f"Error adding video: {e}")
            return False

    def get_pending_video(self) -> Optional[Dict[str, Any]]:
        """Get a single video that needs upload date processing"""
        try:
            query = """
                SELECT * FROM videos 
                WHERE upload_date IS NULL 
                AND length != 'SHORTS seconds'
                LIMIT 1
            """
            logger.info(f"Executing query: {query}")
            self.cursor.execute(query)
            result = self.cursor.fetchone()
            if result:
                logger.info(f"Found pending video: {result}")
            return result
        except Exception as e:
            logger.error(f"Error getting pending video: {e}")
            return None

    def update_video(self, url: str, updates: Dict[str, Any]) -> bool:
        """
        Update video information.
        
        Args:
            url: Video URL
            updates: Dictionary of fields to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Build the SET clause
            set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
            values = list(updates.values())
            values.append(url)  # Add URL for WHERE clause
            
            self.cursor.execute(f'''
                UPDATE videos 
                SET {set_clause}
                WHERE url = ?
            ''', values)
            self.conn.commit()
            logger.info(f"Updated video: {url}")
            return True
        except Exception as e:
            logger.error(f"Error updating video: {e}")
            return False

    def list_all_videos(self) -> List[Dict[str, Any]]:
        """
        List all videos in the database.
        
        Returns:
            List[Dict[str, Any]]: List of video data
        """
        try:
            self.cursor.execute('SELECT * FROM videos')
            return [dict(row) for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error listing videos: {e}")
            return []

    def close(self):
        """Close the database connection."""
        try:
            self.conn.close()
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")
    
    def get_video(self, youtube_url: str) -> Optional[Dict[str, Any]]:
        """
        Get video information from the database.
        
        Args:
            youtube_url: The YouTube URL to look up
            
        Returns:
            Optional[Dict[str, Any]]: Video information if found, None otherwise
        """
        try:
            self.cursor.execute("SELECT * FROM videos WHERE url = ?", (youtube_url,))
            row = self.cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'title': row[1],
                    'url': row[2],
                    'thumbnail_url': row[3],
                    'channel': row[4],
                    'length': row[5],
                    'metadata': row[6],
                    'is_short': bool(row[7]),
                    'upload_date': row[8],
                    'created_at': row[9]
                }
            return None
        except Exception as e:
            logger.error(f"Error getting video from database: {e}")
            return None

    def update_video_upload_date(self, url: str) -> None:
        """
        Update the upload_date field for a video to the current timestamp.
        
        Args:
            url: YouTube video URL
        """
        try:
            with self.conn as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE videos SET upload_date = CURRENT_TIMESTAMP WHERE url = ?",
                    (url,)
                )
                conn.commit()
                logger.info(f"Updated upload_date for video: {url}")
        except Exception as e:
            logger.error(f"Error updating upload_date: {e}")
            raise 