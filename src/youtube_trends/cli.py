"""
Command-line interface for YouTube Trends.
"""

import argparse
from .api import YouTubeAPI
from .display import display_results

def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description='YouTube Trends CLI')
    parser.add_argument('config', help='Configuration name to use (e.g., "kids")')
    parser.add_argument('--days-back', type=int, default=7,
                      help='Number of days to look back for videos (default: 7)')
    
    args = parser.parse_args()
    
    try:
        api = YouTubeAPI()
        results = api.search_videos(
            config_name=args.config,
            days_back=args.days_back
        )
        display_results(results)
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main()) 