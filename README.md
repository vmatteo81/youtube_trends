# YouTube Trending Videos - Italy

This Python application fetches trending videos from YouTube for Italy using the YouTube Data API v3.

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Get a YouTube Data API key:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the YouTube Data API v3
   - Create credentials (API key)
   - Copy your API key

3. Create a `.env` file in the project root and add your API key:
```
YOUTUBE_API_KEY=your_api_key_here
```

## Usage

Run the script:
```bash
python youtube_trending.py
```

The script will display the top 10 trending videos in Italy, including:
- Video title
- Channel name
- View count
- Like count
- Video URL

## Note

The YouTube Data API has quotas and limits. Make sure to check the [YouTube Data API Quotas](https://developers.google.com/youtube/v3/getting-started#quota) for more information.
