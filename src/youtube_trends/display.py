"""
Display module for YouTube Trends results.
"""

def display_results(results):
    """
    Display search results by country.
    
    Args:
        results (dict): Dictionary of results by country
    """
    if not results:
        print("No results found.")
        return
    
    total_videos = sum(len(videos) for videos in results.values())
    print(f"\nFound {total_videos} videos across {len(results)} countries")
    
    for country, videos in results.items():
        print(f"\n{'='*20} {country.upper()} ({len(videos)} videos) {'='*20}")
        
        for video in videos:
            print(f"\nTitle: {video['title']}")
            print(f"Channel: {video['channel_title']}")
            print(f"Search Term: {video['search_term']}")
            print(f"Published: {video['published_at']}")
            print(f"Duration: {video['duration']}")
            print(f"Views: {video['view_count']}")
            print(f"Likes: {video['like_count']}")
            print(f"Comments: {video['comment_count']}")
            print(f"License: {video['license']} (CC: {video['is_cc_licensed']})")
            print(f"Category: {video['category']}")
            print(f"Language: {video['language']}")
            print(f"URL: {video['url']}")
            
            if video['channel_info']:
                print("\nChannel Information:")
                print(f"Subscribers: {video['channel_info']['subscriber_count']}")
                print(f"Total Videos: {video['channel_info']['video_count']}")
                print(f"Total Views: {video['channel_info']['view_count']}")
            
            if video['tags']:
                print("\nTags:")
                print(", ".join(video['tags']))
            
            print("-" * 50) 