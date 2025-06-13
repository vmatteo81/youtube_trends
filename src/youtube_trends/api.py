"""
YouTube API client module for fetching trending videos.
"""

import os
from googleapiclient.discovery import build
from dotenv import load_dotenv

class YouTubeAPI:
    """YouTube API client for fetching trending videos."""
    
    def __init__(self):
        """Initialize the YouTube API client."""
        load_dotenv()
        self.api_key = os.getenv('YOUTUBE_API_KEY')
        if not self.api_key:
            raise ValueError("YouTube API key not found. Please set YOUTUBE_API_KEY in .env file")
        
        self.service = build('youtube', 'v3', developerKey=self.api_key)
    
    def get_trending_videos(self, region_code='IT', max_results=10):
        """
        Fetch trending videos for a specific region.
        
        Args:
            region_code (str): The region code (default: 'IT' for Italy)
            max_results (int): Maximum number of results to return (default: 10)
        
        Returns:
            list: List of trending videos with their details
        """
        try:
            request = self.service.videos().list(
                part='snippet,statistics',
                chart='mostPopular',
                regionCode=region_code,
                maxResults=max_results
            )
            response = request.execute()
            
            trending_videos = []
            for item in response['items']:
                video = {
                    'title': item['snippet']['title'],
                    'channel_title': item['snippet']['channelTitle'],
                    'published_at': item['snippet']['publishedAt'],
                    'view_count': item['statistics'].get('viewCount', 'N/A'),
                    'like_count': item['statistics'].get('likeCount', 'N/A'),
                    'video_id': item['id'],
                    'url': f"https://www.youtube.com/watch?v={item['id']}"
                }
                trending_videos.append(video)
            
            return trending_videos
        
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return [] 