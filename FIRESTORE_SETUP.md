# Google Firestore Setup Guide

This project now uses Google Cloud Firestore instead of SQLite for storing YouTube video data. Follow these steps to set up Firestore authentication:

## Prerequisites

1. **Google Cloud Project**: You need a Google Cloud Project with Firestore enabled.
2. **Service Account**: Create a service account with Firestore permissions.

## Setup Steps

### 1. Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Firestore API for your project

### 2. Create a Service Account

1. In the Google Cloud Console, go to **IAM & Admin** > **Service Accounts**
2. Click **Create Service Account**
3. Give it a name (e.g., "youtube-scraper")
4. Grant the following roles:
   - **Cloud Datastore User** (for read/write access to Firestore)
   - **Cloud Datastore Index Admin** (optional, for index management)

### 3. Download Service Account Key

1. Click on your newly created service account
2. Go to the **Keys** tab
3. Click **Add Key** > **Create New Key**
4. Choose **JSON** format
5. Download the JSON file

### 4. Place Service Account Key

Simply place your downloaded service account JSON file in the project root directory and rename it to `firestore-access.json`.

The application will automatically detect and use this file - no environment variables needed!

```
youtube_scraping/
├── firestore-access.json  ← Place your key file here
├── src/
├── requirements.txt
└── ...
```

**Optional**: If you prefer to use environment variables or have the key file in a different location, you can still set:

```bash
# Windows (PowerShell)
$env:GOOGLE_APPLICATION_CREDENTIALS="path\to\your\key.json"

# Linux/Mac
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/key.json"
```

### 5. Initialize Firestore Database

1. In the Google Cloud Console, go to **Firestore**
2. Click **Create Database**
3. Choose **Native Mode**
4. Select a location for your database

## Usage

The `YouTubeDatabase` class will automatically:
- Connect to Firestore using your credentials
- Create a collection named "youtube_videos" (default)
- Store video data as documents with auto-generated IDs

## Collection Structure

Each video document in Firestore will have the following structure:

```json
{
  "url": "https://www.youtube.com/watch?v=example",
  "title": "Video Title",
  "language": 1,
  "categories": 2,
  "length": "180",
  "upload_date": null,
  "thumbnail_url": "https://img.youtube.com/vi/example/maxresdefault.jpg",
  "is_shorts": false,
  "created_at": "2024-01-01T12:00:00Z"
}
```

**Field Descriptions:**
- `language`: Numeric identifier from config filename (e.g., 1 from "1.json")
- `categories`: Numeric category ID from config file (1=tunes, 2=tales, 3=education, 4=games)

## Troubleshooting

### Authentication Errors
- Ensure `GOOGLE_APPLICATION_CREDENTIALS` points to a valid JSON key file
- Verify the service account has the correct permissions
- Check that the Firestore API is enabled in your project

### Permission Errors
- Ensure your service account has "Cloud Datastore User" role
- Verify your project has Firestore enabled

### Connection Errors
- Check your internet connection
- Verify the project ID is correct
- Ensure Firestore is initialized in your project

### Command to be send to enable ttl 
- gcloud firestore fields ttls update created_at --collection-group=youtube_videos --enable-ttl