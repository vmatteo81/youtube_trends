"""
Command-line interface for the YouTube Trends application.
"""

import argparse
from .api import YouTubeAPI
from .display import display_trending_videos

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Fetch YouTube trending videos.')
    parser.add_argument(
        '--region',
        default='IT',
        help='Region code (default: IT for Italy)'
    )
    parser.add_argument(
        '--max-results',
        type=int,
        default=10,
        help='Maximum number of results to return (default: 10)'
    )
    return parser.parse_args()

def main():
    """Main CLI function."""
    args = parse_args()
    
    print(f"Fetching trending videos in {args.region}...")
    
    try:
        api = YouTubeAPI()
        trending_videos = api.get_trending_videos(
            region_code=args.region,
            max_results=args.max_results
        )
        display_trending_videos(trending_videos)
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main() 