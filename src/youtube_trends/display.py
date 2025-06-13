"""
Display module for formatting and showing trending videos information.
"""

def format_video_info(video, index):
    """
    Format a single video's information for display.
    
    Args:
        video (dict): Video information dictionary
        index (int): Video's position in the list
    
    Returns:
        str: Formatted video information
    """
    return f"""
{index}. {video['title']}
   Channel: {video['channel_title']}
   Views: {video['view_count']}
   Likes: {video['like_count']}
   URL: {video['url']}
{'-' * 80}"""

def display_trending_videos(videos):
    """
    Display a list of trending videos.
    
    Args:
        videos (list): List of video information dictionaries
    """
    if not videos:
        print("No trending videos found or an error occurred.")
        return
    
    print("\nTop Trending Videos in Italy:")
    print("-" * 80)
    
    for i, video in enumerate(videos, 1):
        print(format_video_info(video, i)) 