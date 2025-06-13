"""
Web scraper for YouTube search results.
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from .database import YouTubeDatabase
import requests
from io import BytesIO
from PIL import Image
import yt_dlp
import os
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logger
logger = logging.getLogger(__name__)

class YouTubeScraper:
    """Scraper for YouTube search results."""
    
    def __init__(self):
        """Initialize the scraper with Chrome WebDriver."""
        logger.info("Initializing YouTube Scraper...")
        chrome_options = Options()
        
        # Basic options
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Additional options for Docker environment
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")
        chrome_options.add_argument("--disable-site-isolation-trials")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Set user agent
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Additional preferences
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        try:
            logger.info("Setting up Chrome WebDriver...")
            
            # Use system ChromeDriver
            chromedriver_path = '/usr/local/bin/chromedriver'
            if not os.path.exists(chromedriver_path):
                raise Exception(f"ChromeDriver not found at {chromedriver_path}")
                
            logger.info(f"Using ChromeDriver at: {chromedriver_path}")
            service = Service(executable_path=chromedriver_path)
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Set page load timeout
            self.driver.set_page_load_timeout(30)
            
            logger.info("Chrome WebDriver initialized successfully")
            
            # Initialize database
            try:
                self.db = YouTubeDatabase()
                logger.info("Database initialized")
            except Exception as e:
                logger.error(f"Failed to initialize database: {e}")
                logger.warning("Continuing without database support")
                self.db = None
            
        except Exception as e:
            logger.error(f"Failed to initialize Chrome WebDriver: {e}")
            raise
    
    def _is_today_upload(self, metadata: str) -> bool:
        """
        Check if the video was uploaded today based on metadata.
        
        Args:
            metadata: Video metadata string
            
        Returns:
            bool: True if video was uploaded today
        """
        today = datetime.now().date()
        
        # Check for "today" or "hours ago" in metadata
        if "today" in metadata.lower() or "hours ago" in metadata.lower():
            return True
            
        # Check for "minutes ago" in metadata
        if "minutes ago" in metadata.lower():
            return True
            
        # Check for "just now" in metadata
        if "just now" in metadata.lower():
            return True
            
        return False
    
    def _convert_time_to_seconds(self, time_str: str) -> int:
        """
        Convert time string (e.g., "2:30" or "1:30:45") to seconds.
        
        Args:
            time_str: Time string in format "MM:SS" or "HH:MM:SS"
            
        Returns:
            int: Time in seconds
        """
        try:
            # Split the time string into parts
            parts = time_str.split(':')
            
            if len(parts) == 2:  # MM:SS format
                minutes, seconds = map(int, parts)
                return minutes * 60 + seconds
            elif len(parts) == 3:  # HH:MM:SS format
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds
            else:
                logger.warning(f"Unexpected time format: {time_str}")
                return 0
        except Exception as e:
            logger.warning(f"Error converting time {time_str} to seconds: {e}")
            return 0
    
    def _extract_video_id(self, url: str) -> str:
        """
        Extract video ID from YouTube URL.
        
        Args:
            url: Full YouTube URL
            
        Returns:
            str: Video ID or original URL if not found
        """
        try:
            # Handle shorts URLs
            if '/shorts/' in url:
                return url
                
            # Extract video ID from watch URL
            if 'watch?v=' in url:
                video_id = url.split('watch?v=')[1].split('&')[0]
                return f"https://www.youtube.com/watch?v={video_id}"
                
            return url
        except Exception as e:
            logger.warning(f"Error extracting video ID from {url}: {e}")
            return url
    
    def search(self, url: str) -> List[Dict[str, Any]]:
        """
        Search YouTube using the provided URL.
        
        Args:
            url: The YouTube search URL
            
        Returns:
            List[Dict[str, Any]]: List of video information dictionaries
        """
        logger.info(f"Using provided URL: {url}")
        
        try:
            logger.info("Loading search page...")
            self.driver.get(url)
            logger.info("Page loaded, waiting for video elements...")
            
            # Wait for initial video elements to load
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ytd-video-renderer"))
            )
            
            # Get current URL after any redirects
            current_url = self.driver.current_url
            logger.info(f"Current page URL: {current_url}")
            
            # Scroll to load more content
            logger.info("Scrolling to load more content...")
            last_height = self.driver.execute_script("return document.documentElement.scrollHeight")
            while True:
                # Scroll down
                self.driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
                
                # Wait for new content to load
                time.sleep(2)
                
                # Calculate new scroll height
                new_height = self.driver.execute_script("return document.documentElement.scrollHeight")
                
                # Break if no more content loaded
                if new_height == last_height:
                    break
                    
                last_height = new_height
                logger.info("Scrolled and loaded more content...")
            
            # Get all video elements after scrolling
            video_elements = self.driver.find_elements(By.CSS_SELECTOR, "ytd-video-renderer")
            logger.info(f"Found {len(video_elements)} video elements after scrolling")
            
            results = []
            page = 1
            max_pages = 5  # Process up to 5 pages
            
            while page <= max_pages:
                logger.info(f"\nProcessing page {page}/{max_pages}")
                
                for idx, element in enumerate(video_elements, 1):
                    try:
                        logger.info(f"Processing video {idx}/{len(video_elements)} on page {page}")
                        
                        # Scroll element into view
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                        time.sleep(0.5)  # Wait for content to load
                        
                        # Get video information
                        title_element = element.find_element(By.CSS_SELECTOR, "#video-title")
                        title = title_element.text
                        full_url = title_element.get_attribute("href")
                        
                        if not full_url:  # Skip if no URL found
                            logger.warning(f"No URL found for video {idx}, skipping...")
                            continue
                            
                        # Extract clean URL
                        url = self._extract_video_id(full_url)
                        
                        # Get thumbnail URL - try multiple selectors
                        thumbnail_url = "Unknown"
                        try:
                            # Try the main thumbnail image
                            thumbnail_element = element.find_element(By.CSS_SELECTOR, "img.yt-core-image")
                            thumbnail_url = thumbnail_element.get_attribute("src")
                        except:
                            try:
                                # Try the thumbnail container
                                thumbnail_element = element.find_element(By.CSS_SELECTOR, "#thumbnail img")
                                thumbnail_url = thumbnail_element.get_attribute("src")
                            except:
                                try:
                                    # Try the thumbnail link
                                    thumbnail_element = element.find_element(By.CSS_SELECTOR, "#thumbnail")
                                    thumbnail_url = thumbnail_element.get_attribute("href")
                                except:
                                    logger.warning(f"Could not find thumbnail URL for video {idx}")
                        
                        # Get channel information - try different selectors
                        try:
                            channel_element = element.find_element(By.CSS_SELECTOR, "#channel-name a")
                            channel = channel_element.text
                        except:
                            try:
                                channel_element = element.find_element(By.CSS_SELECTOR, "ytd-channel-name a")
                                channel = channel_element.text
                            except:
                                channel = "Unknown Channel"
                                logger.warning(f"Could not find channel name for video {idx}")
                        
                        # Get metadata and length
                        try:
                            metadata_element = element.find_element(By.CSS_SELECTOR, "#metadata-line")
                            metadata = metadata_element.text
                            
                            # Skip if video is scheduled for premiere
                            if "Premieres" in metadata:
                                logger.info(f"Skipping video {idx} - Scheduled for premiere: {metadata}")
                                continue
                                
                            # Skip if video is currently being watched
                            if "watching" in metadata.lower():
                                logger.info(f"Skipping video {idx} - Currently being watched: {metadata}")
                                continue
                            
                            # Try to get video length - try multiple selectors
                            length = "Unknown"
                            try:
                                length_element = element.find_element(By.CSS_SELECTOR, "span.ytd-thumbnail-overlay-time-status-renderer")
                                length = length_element.text.strip()
                            except:
                                try:
                                    length_element = element.find_element(By.CSS_SELECTOR, "#text.ytd-thumbnail-overlay-time-status-renderer")
                                    length = length_element.text.strip()
                                except:
                                    logger.warning(f"Could not find length for video {idx}")
                            
                            # Extract views from metadata
                            views = "0"
                            if "views" in metadata.lower():
                                views = metadata.split("views")[0].strip()
                            
                        except:
                            metadata = "No metadata"
                            length = "Unknown"
                            views = "0"
                            logger.warning(f"Could not find metadata for video {idx}")
                            continue  # Skip this video if metadata is not found
                        
                        # Skip if length is still unknown
                        if length == "Unknown":
                            logger.info(f"Skipping video {idx} - Length is unknown")
                            continue
                        
                        logger.info(f"\nVideo {idx} details:")
                        logger.info(f"Title: {title}")
                        logger.info(f"URL: {url}")
                        logger.info(f"Thumbnail: {thumbnail_url}")
                        logger.info(f"Channel: {channel}")
                        logger.info(f"Length: {length} seconds")
                        logger.info(f"Views: {views}")
                        logger.info(f"Metadata: {metadata}")
                        
                        video_info = {
                            'title': title,
                            'url': url,
                            'thumbnail_url': thumbnail_url,
                            'channel': channel,
                            'length': length,
                            'views': views,
                            'metadata': metadata
                        }
                        
                        # Add to database if available
                        if self.db is not None:
                            if self.db.add_video(video_info):
                                logger.info(f"Added to database: {title}")
                            else:
                                logger.info(f"Video already in database: {title}")
                        
                        results.append(video_info)
                        
                    except Exception as e:
                        logger.error(f"Error processing video element {idx}: {e}")
                        continue
                
                # Try to go to next page
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, "ytd-continuation-item-renderer")
                    if next_button:
                        logger.info("Found next page button, clicking...")
                        next_button.click()
                        time.sleep(2)  # Wait for new content to load
                        page += 1
                    else:
                        logger.info("No more pages available")
                        break
                except Exception as e:
                    logger.info("No more pages available")
                    break
            
            logger.info(f"\nSuccessfully processed {len(results)} videos from {page-1} pages")
            return results
            
        except Exception as e:
            logger.error(f"Error during search: {e}")
            return []
    
    def close(self):
        """Close the WebDriver and database connection."""
        logger.info("\nClosing YouTube Scraper...")
        try:
            self.driver.quit()
            logger.info("WebDriver closed")
            
            # List all videos in database before closing if available
            if self.db is not None:
                self.db.list_all_videos()
            logger.info("Scraper closed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def _resize_thumbnail(self, thumbnail_url: str, video_id: str) -> str:
        """
        Resize thumbnail to 480x270 and save locally.
        
        Args:
            thumbnail_url: URL of the thumbnail
            video_id: Video ID from SQLite row
            
        Returns:
            str: Full absolute path to the saved thumbnail file
        """
        try:
            # Convert AVIF URL to JPEG
            if 'avif' in thumbnail_url:
                thumbnail_url = thumbnail_url.replace('avif', 'jpg')
            elif '?sqp=' in thumbnail_url:
                # Remove query parameters to get base JPEG
                thumbnail_url = thumbnail_url.split('?')[0]
            
            logger.info(f"Attempting to download thumbnail from: {thumbnail_url}")
            # Download the image
            response = requests.get(thumbnail_url)
            if response.status_code != 200:
                logger.warning(f"Failed to download thumbnail: {thumbnail_url} - Status code: {response.status_code}")
                return thumbnail_url
                
            # Log the content type
            content_type = response.headers.get('content-type', 'unknown')
            logger.info(f"Thumbnail content type: {content_type}")
            
            if not content_type.startswith('image/'):
                logger.warning(f"Invalid content type for thumbnail: {content_type}")
                return thumbnail_url
                
            # Open and resize the image
            try:
                img = Image.open(BytesIO(response.content))
                logger.info(f"Original image size: {img.size}")
                img = img.resize((480, 270), Image.Resampling.LANCZOS)
                logger.info("Image resized successfully")
            except Exception as e:
                logger.error(f"Error processing image: {e}")
                return thumbnail_url
            
            # Save to file using video ID
            thumbnail_path = f"{video_id}.jpg"
            img.save(thumbnail_path, "JPEG")
            full_path = os.path.abspath(thumbnail_path)
            return full_path
            
        except Exception as e:
            logger.error(f"Error resizing thumbnail: {e}")
            logger.error(f"Thumbnail URL: {thumbnail_url}")
            return thumbnail_url

    def _download_video(self, url: str, max_retries: int = 3) -> str:
        """
        Download video using yt-dlp with retry mechanism.
        
        Args:
            url: YouTube video URL
            max_retries: Maximum number of retry attempts
            
        Returns:
            str: Path to downloaded video file
        """
        # Extract video ID
        video_id = url.split('v=')[-1]
        logger.info(f"Extracted video ID: {video_id}")
        
        def sanitize_filename(title: str) -> str:
            """Sanitize filename for Linux filesystem."""
            # Replace invalid characters with underscore
            invalid_chars = '<>:"/\\|?*'
            for char in invalid_chars:
                title = title.replace(char, '_')
            # Remove leading/trailing spaces and dots
            title = title.strip('. ')
            # Limit length to 255 characters (Linux filename limit)
            return title[:255]
        
        ydl_opts = {
            'format': 'best[ext=mp4]',
            'outtmpl': f'{video_id}.%(ext)s',  # Use video ID for initial download
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'nocheckcertificate': True,
            'no_playlist': True,
            'geo_bypass': True,
            'retries': 10,
            'fragment_retries': 10,
            'socket_timeout': 30,
            'http_chunk_size': 10485760,
            'verbose': True
        }
        
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    logger.info(f"Attempting to download video (attempt {retry_count + 1}/{max_retries}): {url}")
                    try:
                        info = ydl.extract_info(url, download=True)
                    except Exception as e:
                        logger.error(f"First attempt failed: {e}")
                        # Try with video ID directly
                        logger.info("Trying with video ID directly...")
                        info = ydl.extract_info(video_id, download=True)
                    
                    if not info:
                        raise Exception("Video information not available")
                        
                    if 'title' not in info:
                        raise Exception("Video title not found")
                    
                    # Check if file was downloaded with video ID
                    temp_path = f"{video_id}.mp4"
                    if not os.path.exists(temp_path):
                        raise Exception("Video file not downloaded")
                    
                    # Get sanitized filename
                    title = sanitize_filename(info['title'])
                    final_path = f"{title}.mp4"
                    
                    # Rename the file
                    try:
                        os.rename(temp_path, final_path)
                        logger.info(f"Successfully downloaded and renamed video to: {final_path}")
                        return final_path
                    except Exception as rename_error:
                        logger.error(f"Error renaming file: {rename_error}")
                        # If rename fails, return the temp path
                        return temp_path
                    
            except Exception as e:
                last_error = e
                retry_count += 1
                logger.error(f"Download attempt {retry_count} failed: {e}")
                
                # Clean up any partial downloads
                try:
                    temp_path = f"{video_id}.mp4"
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except Exception as cleanup_error:
                    logger.error(f"Error during cleanup: {cleanup_error}")
                
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count  # Exponential backoff
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} download attempts failed")
                    raise last_error

    def _download_thumbnail(self, url: str, video_id: str) -> str:
        """
        Download and resize thumbnail.
        
        Args:
            url: Thumbnail URL
            video_id: Video ID for filename
            
        Returns:
            str: Path to thumbnail file
        """
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        img = img.resize((480, 270), Image.Resampling.LANCZOS)
        thumbnail_path = f"{video_id}.jpg"
        img.save(thumbnail_path, "JPEG")
        return thumbnail_path

    def submit_to_justjackpot(self, video_data: dict) -> bool:
        """
        Submit video data to JustJackpot API.
        
        Args:
            video_data: Dictionary containing video information
            
        Returns:
            bool: True if submission was successful, False otherwise
        """
        try:
            # Download video
            video_path = self._download_video(video_data['url'])
            logger.info(f"Downloaded video to: {video_path}")
            
            # Resize thumbnail
            if video_data['thumbnail_url'] != "Unknown":
                thumbnail_path = self._resize_thumbnail(video_data['thumbnail_url'], video_data['url'].split('v=')[-1])
                logger.info(f"Thumbnail saved to: {thumbnail_path}")
            else:
                logger.warning("No thumbnail URL available")
                return False
            
            # Convert length to seconds
            length_str = video_data.get('length', '0')
            # Prepare form data
            form_data = {
                'cliente': '3',  # jktv-free
                'categoria': '1',  # tunes
                'lingua': '1',  # en
                'url_originale': video_data['url'],
                'lunghezza': length_str
            }
            
            # Prepare files
            files = {
                'file': (os.path.basename(video_path), open(video_path, 'rb'), 'video/mp4'),
                'image': (os.path.basename(thumbnail_path), open(thumbnail_path, 'rb'), 'image/jpeg')
            }
            
            # Submit to API
            api_url = os.getenv('JUSTJACKPOT_API_URL')
            logger.info(f"API URL from environment: {api_url}")
            
            if not api_url:
                logger.error("JUSTJACKPOT_API_URL environment variable is not set")
                return False
                
            response = requests.post(
                api_url,
                data=form_data,
                files=files
            )
            
            # Update upload_date in database
            if response.status_code == 200:
                logger.info("Successfully submitted to JustJackpot")
                # Update upload_date in database
                self.db.update_video_upload_date(video_data['url'])
                return True
            else:
                logger.error(f"Failed to submit to JustJackpot: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error submitting to JustJackpot: {e}")
            return False
            
        finally:
            # Clean up files
            try:
                if 'video' in locals() and os.path.exists(video_path):
                    os.remove(video_path)
                if 'image' in locals() and os.path.exists(thumbnail_path):
                    os.remove(thumbnail_path)
            except Exception as e:
                logger.error(f"Error cleaning up files: {e}")

    def process_pending_videos(self):
        """Process videos that need upload dates and resize their thumbnails."""
        logger.info("\n" + "="*50)
        logger.info("Starting process_pending_videos")
        logger.info("="*50 + "\n")
        
        if not self.db:
            logger.error("Database not initialized")
            return
            
        try:
            # Get one video that needs processing
            video = self.db.get_pending_video()
            if not video:
                logger.info("No videos need processing")
                return
                
            logger.info(f"Processing video: {video['url']}")
            
            # Load the video page
            self.driver.get(video['url'])
            time.sleep(2)  # Wait for page to load
        
            # Prepare video data for API submission
            video_data = {
                'title': video['title'],
                'url': video['url'],
                'thumbnail_url': video['thumbnail_url'],
                'length': video['length']
            }
            
            # Submit to JustJackpot
            if self.submit_to_justjackpot(video_data):
                logger.info("Video submitted to JustJackpot")
            else:
                logger.error("Failed to submit video to JustJackpot")
                
        except Exception as e:
            logger.error(f"Error processing video: {e}")
        finally:
            self.close()

def main():
    """Main function to run the scraper."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    scraper = YouTubeScraper()
    try:
        # Fixed URL with sp parameter
        url = "https://www.youtube.com/results?search_query=kids+song&sp=CAISBggCEAEwAQ%253D%253D"
        #logger.info(f"Starting search with URL: {url}")
        #results = scraper.search(url)
        #logger.info("\nFinal Results:")
        #for video in results:
        #    logger.info(f"\nTitle: {video['title']}")
        #    logger.info(f"URL: {video['url']}")
        #    logger.info(f"Thumbnail: {video['thumbnail_url']}")
        #    logger.info(f"Channel: {video['channel']}")
        #    logger.info(f"Length: {video['length']} seconds")
        #    logger.info(f"Views: {video['views']}")
        #    logger.info(f"Metadata: {video['metadata']}")
        #    logger.info("-" * 50)
            
    finally:
        scraper.process_pending_videos()
        scraper.close()

if __name__ == "__main__":
    main() 