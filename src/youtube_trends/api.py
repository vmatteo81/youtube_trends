"""
YouTube API client module for fetching videos based on configurations.
"""

import os
import traceback
import json
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from .config import ConfigLoader

class YouTubeAPI:
    """YouTube API client for fetching videos based on configurations."""
    
    def __init__(self):
        """Initialize the YouTube API client."""
        load_dotenv()
        self.api_key = os.getenv('YOUTUBE_API_KEY')
        if not self.api_key:
            raise ValueError("YouTube API key not found. Please set YOUTUBE_API_KEY in .env file")
        
        self.service = build('youtube', 'v3', developerKey=self.api_key)
        self.config_loader = ConfigLoader()
    
    def _log_api_request(self, endpoint, params):
        """Log API request parameters."""
        print("\nAPI Request Details:")
        print(f"Endpoint: {endpoint}")
        print("Parameters:")
        for key, value in params.items():
            if key == 'developerKey':
                value = f"{value[:5]}...{value[-5:]}"
            print(f"  {key}: {value}")
        print("-" * 50)
    
    def _log_api_response(self, response, items_count=None):
        """Log API response summary."""
        print("\nAPI Response Summary:")
        if items_count is not None:
            print(f"Items found: {items_count}")
        if hasattr(response, 'get'):
            print(f"Response keys: {list(response.keys())}")
        print("-" * 50)
    
    def _get_license_info(self, video_id):
        """
        Get license information for a video.
        
        Args:
            video_id (str): The YouTube video ID
            
        Returns:
            dict: License information including type and status
        """
        try:
            response = self.service.videos().list(
                part='contentDetails',
                id=video_id
            ).execute()
            
            if not response.get('items'):
                return {'type': 'unknown', 'is_cc': False}
                
            video = response['items'][0]
            license_type = video['contentDetails'].get('license', 'unknown')
            
            print(f"\nLicense check for video {video_id}:")
            print(f"License type: {license_type}")
            
            return {
                'type': license_type,
                'is_cc': license_type == 'creativeCommon'
            }
            
        except Exception as e:
            print(f"Error checking license for video {video_id}: {str(e)}")
            return {'type': 'error', 'is_cc': False}
    
    def _is_horizontal_video(self, video_id):
        """
        Check if a video is in horizontal format.
        
        Args:
            video_id (str): The YouTube video ID
            
        Returns:
            bool: True if video is horizontal, False otherwise
        """
        try:
            response = self.service.videos().list(
                part='contentDetails',
                id=video_id
            ).execute()
            
            if not response.get('items'):
                return False
                
            video = response['items'][0]
            dimension = video['contentDetails'].get('dimension', '')
            
            print(f"\nChecking video dimensions for {video_id}:")
            print(f"Dimension: {dimension}")
            
            return dimension == '2d'  # 2d means horizontal video
            
        except Exception as e:
            print(f"Error checking video dimensions for {video_id}: {str(e)}")
            return False
    
    def search_videos(self, config_name, days_back=7):
        """
        Search for videos using a specific configuration.
        
        Args:
            config_name (str): Name of the configuration to use
            days_back (int): Number of days to look back for videos
            
        Returns:
            dict: Dictionary of results by country
        """
        try:
            print(f"\n{'='*20} Starting Search {'='*20}")
            print(f"Using configuration: {config_name}")
            
            # Get all countries for this configuration
            countries = self.config_loader.get_countries(config_name)
            print(f"Found countries: {', '.join(countries)}")
            
            results = {}
            for country in countries:
                print(f"\n{'='*20} Processing {country} {'='*20}")
                
                # Get country configuration
                country_config = self.config_loader.get_country_config(config_name, country)
                search_terms = country_config['search_terms']
                horizontal_only = country_config.get('horizontal_video_only', False)
                max_videos = country_config.get('max_videos', 10)  # Default to 10 if not specified
                
                print(f"Target number of videos: {max_videos}")
                if horizontal_only:
                    print("Filtering for horizontal videos only")
                
                # Calculate the date for filtering
                published_after = (datetime.utcnow() - timedelta(days=days_back)).isoformat() + 'Z'
                
                country_videos = []
                for term in search_terms:
                    if len(country_videos) >= max_videos:
                        print(f"\nReached target of {max_videos} videos for {country}")
                        break
                        
                    print(f"\nSearching for: {term}")
                    
                    # Search for videos
                    search_params = {
                        'part': 'id',
                        'q': term,
                        'type': 'video',
                        'maxResults': 50,  # Maximum allowed by API
                        'order': 'date',
                        'publishedAfter': published_after,
                        'regionCode': country_config['region_code'],
                        'relevanceLanguage': country_config['language'],
                        'videoCategoryId': country_config['video_category_id'],
                        'safeSearch': country_config['safe_search'],
                        'videoDuration': country_config['video_duration']
                    }
                    
                    self._log_api_request('search().list', search_params)
                    search_response = self.service.search().list(**search_params).execute()
                    
                    if not search_response.get('items'):
                        print(f"No videos found for term: {term}")
                        continue
                    
                    # Get video IDs
                    video_ids = [item['id']['videoId'] for item in search_response['items']]
                    self._log_api_response(search_response, len(video_ids))
                    
                    # Get detailed video information
                    videos_params = {
                        'part': 'snippet,statistics,contentDetails',
                        'id': ','.join(video_ids)
                    }
                    
                    self._log_api_request('videos().list', videos_params)
                    videos_response = self.service.videos().list(**videos_params).execute()
                    
                    if not videos_response.get('items'):
                        print(f"No video details found for term: {term}")
                        continue
                    
                    # Process each video
                    for item in videos_response['items']:
                        if len(country_videos) >= max_videos:
                            break
                            
                        video_id = item['id']
                        
                        # Check if video is horizontal if required
                        if horizontal_only and not self._is_horizontal_video(video_id):
                            print(f"\nSkipping video {video_id}: Not horizontal")
                            continue
                        
                        # Get license information
                        license_info = self._get_license_info(video_id)
                        
                        # Get channel information
                        channel_id = item['snippet'].get('channelId')
                        channel_info = {}
                        if channel_id:
                            try:
                                channel_response = self.service.channels().list(
                                    part='snippet,statistics',
                                    id=channel_id
                                ).execute()
                                if channel_response.get('items'):
                                    channel = channel_response['items'][0]
                                    channel_info = {
                                        'channel_id': channel_id,
                                        'channel_title': channel['snippet'].get('title', ''),
                                        'channel_description': channel['snippet'].get('description', ''),
                                        'subscriber_count': channel['statistics'].get('subscriberCount', 'N/A'),
                                        'video_count': channel['statistics'].get('videoCount', 'N/A'),
                                        'view_count': channel['statistics'].get('viewCount', 'N/A')
                                    }
                            except Exception as e:
                                print(f"Error fetching channel info for {channel_id}: {str(e)}")
                        
                        video = {
                            'title': item['snippet']['title'],
                            'description': item['snippet'].get('description', ''),
                            'channel_title': item['snippet']['channelTitle'],
                            'published_at': item['snippet']['publishedAt'],
                            'view_count': item['statistics'].get('viewCount', 'N/A'),
                            'like_count': item['statistics'].get('likeCount', 'N/A'),
                            'comment_count': item['statistics'].get('commentCount', 'N/A'),
                            'video_id': video_id,
                            'url': f"https://www.youtube.com/watch?v={video_id}",
                            'license': license_info['type'],
                            'is_cc_licensed': license_info['is_cc'],
                            'duration': item['contentDetails'].get('duration', 'N/A'),
                            'language': item['snippet'].get('defaultLanguage', 'unknown'),
                            'category': item['snippet'].get('categoryId', 'unknown'),
                            'tags': item['snippet'].get('tags', []),
                            'channel_info': channel_info,
                            'search_term': term,
                            'country': country,
                            'dimension': item['contentDetails'].get('dimension', 'unknown')
                        }
                        country_videos.append(video)
                        print(f"\nAdded video {video_id}:")
                        print(f"Title: {video['title']}")
                        print(f"Channel: {video['channel_title']}")
                        print(f"License: {video['license']} (CC: {video['is_cc_licensed']})")
                        print(f"Duration: {video['duration']}")
                        print(f"Category: {video['category']}")
                        print(f"Dimension: {video['dimension']}")
                        print(f"URL: {video['url']}")
                        print(f"Progress: {len(country_videos)}/{max_videos} videos")
                        print("-" * 50)
                
                results[country] = country_videos
                print(f"\nFound {len(country_videos)} videos for {country}")
            
            print(f"\n{'='*20} Search Completed {'='*20}")
            return results
        
        except HttpError as e:
            print(f"\n{'='*20} API Error {'='*20}")
            print(f"YouTube API Error: {e.resp.status} {e.content}")
            print(f"Error details: {e.error_details if hasattr(e, 'error_details') else 'No details available'}")
            print(f"{'='*50}\n")
            return {}
        except Exception as e:
            print(f"\n{'='*20} Unexpected Error {'='*20}")
            print(f"An unexpected error occurred: {str(e)}")
            print("Full error traceback:")
            traceback.print_exc()
            print(f"{'='*50}\n")
            return {} 