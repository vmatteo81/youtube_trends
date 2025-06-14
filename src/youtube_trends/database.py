"""Google Firestore database module for storing YouTube video information."""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import sys
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud.exceptions import NotFound

# Configure logger
logger = logging.getLogger(__name__)

class YouTubeDatabase:
    """Database handler for YouTube video information using Google Firestore."""
    
    def __init__(self, project_id: str = None, collection_name: str = "youtube_videos"):
        """
        Initialize the Firestore database connection.
        
        Args:
            project_id: Google Cloud Project ID (if None, uses default from environment)
            collection_name: Firestore collection name for storing videos
        """
        try:
            # Get project root directory (3 levels up from this file)
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            credentials_path = os.path.join(project_root, 'firestore-access.json')
            
            # Set credentials environment variable if file exists
            if os.path.exists(credentials_path):
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
                logger.info(f"Using credentials from: {credentials_path}")
            else:
                logger.warning(f"Credentials file not found at: {credentials_path}")
                logger.info("Falling back to environment GOOGLE_APPLICATION_CREDENTIALS")
            
            # Initialize Firestore client
            if project_id:
                self.db = firestore.Client(project=project_id)
            else:
                # Use default project from environment (GOOGLE_CLOUD_PROJECT)
                self.db = firestore.Client()
            
            self.collection_name = collection_name
            self.collection = self.db.collection(collection_name)
            
            # Test the connection
            test_doc = self.collection.document('_test_connection')
            test_doc.set({'test': True, 'timestamp': datetime.now()})
            test_doc.delete()
            
            logger.info(f"Firestore connection successful. Using collection: {collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Firestore database: {e}")
            logger.error("Make sure firestore-access.json exists in project root or GOOGLE_APPLICATION_CREDENTIALS is set")
            raise

    def _get_document_id(self, url: str) -> str:
        """
        Generate a document ID from the video URL.
        
        Args:
            url: YouTube video URL
            
        Returns:
            str: Document ID for Firestore
        """
        # Extract video ID from URL or use a hash of the full URL
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()

    def add_video(self, video_data: Dict[str, Any]) -> bool:
        """
        Add a video to the Firestore database.
        
        Args:
            video_data: Dictionary containing video information
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            doc_id = self._get_document_id(video_data['url'])
            
            # Prepare document data
            doc_data = {
                'url': video_data['url'],
                'title': video_data['title'],
                'language': video_data['language'],
                'categories': video_data['categories'],
                'length': video_data['length'],
                'upload_date': video_data.get('upload_date'),
                'thumbnail_url': video_data.get('thumbnail_url', 'Unknown'),
                'is_shorts': video_data.get('is_shorts', False),
                'created_at': datetime.now()
            }
            
            # Use set() to create or update the document
            self.collection.document(doc_id).set(doc_data)
            logger.info(f"Added video to Firestore: {video_data['url']}")
            return True
        except Exception as e:
            logger.error(f"Error adding video to Firestore: {e}")
            return False

    def get_pending_videos_by_category_language(self, language_category_combinations: List[tuple]) -> List[Dict[str, Any]]:
        """Get one video per category per language combination using separate queries"""
        selected_videos = []
        
        try:
            for language, category in language_category_combinations:
                # Make a separate query for each language-category combination
                query = (self.collection
                        .where(filter=FieldFilter('upload_date', '==', None))
                        .where(filter=FieldFilter('is_shorts', '==', False))
                        .where(filter=FieldFilter('language', '==', language))
                        .where(filter=FieldFilter('categories', '==', category))
                        .order_by('created_at')
                        .limit(1))
                
                docs = list(query.stream())
                
                if docs:
                    result = docs[0].to_dict()
                    result['id'] = docs[0].id  # Add document ID
                    selected_videos.append(result)
                    logger.info(f"Selected video for language={language}, category={category}: {result['url']}")
                else:
                    logger.info(f"No video found for language={language}, category={category}")
            
            if not selected_videos:
                logger.info("No videos available for upload")
            else:
                logger.info(f"Found {len(selected_videos)} videos for different language-category combinations")
            
            return selected_videos
        except Exception as e:
            logger.error(f"Error getting pending videos from Firestore: {e}")
            return []

    def update_video(self, url: str, updates: Dict[str, Any]) -> bool:
        """
        Update video information in Firestore.
        
        Args:
            url: Video URL
            updates: Dictionary of fields to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            doc_id = self._get_document_id(url)
            doc_ref = self.collection.document(doc_id)
            
            # Update the document
            doc_ref.update(updates)
            logger.info(f"Updated video in Firestore: {url}")
            return True
        except Exception as e:
            logger.error(f"Error updating video in Firestore: {e}")
            return False

    def list_all_videos(self) -> List[Dict[str, Any]]:
        """
        List all videos in the Firestore database.
        
        Returns:
            List[Dict[str, Any]]: List of video data
        """
        try:
            docs = self.collection.stream()
            videos = []
            for doc in docs:
                video_data = doc.to_dict()
                video_data['id'] = doc.id  # Add document ID
                videos.append(video_data)
            return videos
        except Exception as e:
            logger.error(f"Error listing videos from Firestore: {e}")
            return []

    def close(self):
        """Close the Firestore connection (no explicit close needed for Firestore)."""
        try:
            # Firestore client doesn't require explicit closing
            logger.info("Firestore connection closed (no explicit close needed)")
        except Exception as e:
            logger.error(f"Error closing Firestore connection: {e}")
    
    def get_video(self, youtube_url: str) -> Optional[Dict[str, Any]]:
        """
        Get video information from Firestore.
        
        Args:
            youtube_url: The YouTube URL to look up
            
        Returns:
            Optional[Dict[str, Any]]: Video information if found, None otherwise
        """
        try:
            doc_id = self._get_document_id(youtube_url)
            doc_ref = self.collection.document(doc_id)
            doc = doc_ref.get()
            
            if doc.exists:
                video_data = doc.to_dict()
                video_data['id'] = doc.id  # Add document ID
                return video_data
            return None
        except Exception as e:
            logger.error(f"Error getting video from Firestore: {e}")
            return None

    def update_video_upload_date(self, url: str) -> None:
        """
        Update the upload_date field for a video to the current timestamp.
        
        Args:
            url: YouTube video URL
        """
        try:
            doc_id = self._get_document_id(url)
            doc_ref = self.collection.document(doc_id)
            
            doc_ref.update({
                'upload_date': datetime.now()
            })
            logger.info(f"Updated upload_date for video in Firestore: {url}")
        except Exception as e:
            logger.error(f"Error updating upload_date in Firestore: {e}")
            raise

    def get_pending_videos_by_category_language(self, language_category_combinations: List[tuple]) -> List[Dict[str, Any]]:
        """Get one video per category per language combination using separate queries"""
        selected_videos = []
        
        try:
            for language, category in language_category_combinations:
                # Make a separate query for each language-category combination
                query = (self.collection
                        .where(filter=FieldFilter('upload_date', '==', None))
                        .where(filter=FieldFilter('is_shorts', '==', False))
                        .where(filter=FieldFilter('language', '==', language))
                        .where(filter=FieldFilter('categories', '==', category))
                        .order_by('created_at')
                        .limit(1))
                
                docs = list(query.stream())
                
                if docs:
                    result = docs[0].to_dict()
                    result['id'] = docs[0].id  # Add document ID
                    selected_videos.append(result)
                    logger.info(f"Selected video for language={language}, category={category}: {result['url']}")
                else:
                    logger.info(f"No video found for language={language}, category={category}")
            
            if not selected_videos:
                logger.info("No videos available for upload")
            else:
                logger.info(f"Found {len(selected_videos)} videos for different language-category combinations")
            
            return selected_videos
        except Exception as e:
            logger.error(f"Error getting pending videos from Firestore: {e}")
            return []