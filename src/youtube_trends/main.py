"""
Main script for fetching and displaying YouTube trending videos.
"""

from .api import YouTubeAPI
from .display import display_trending_videos

def main():
    """Main function to fetch and display trending videos."""
    print("Fetching trending videos in Italy...")
    
    try:
        api = YouTubeAPI()
        trending_videos = api.get_trending_videos()
        display_trending_videos(trending_videos)
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main() 