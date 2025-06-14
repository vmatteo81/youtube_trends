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
from dotenv import load_dotenv
import configparser

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
    
    def load_urls_from_config(self, config_file: str) -> List[Dict[str, Any]]:
        """
        Load URLs from a configuration file along with language and category information.
        
        Args:
            config_file: Path to the configuration file
            
        Returns:
            List of dictionaries containing URL, language, and category information
        """
        url_data = []
        config_path = os.path.join(os.path.dirname(__file__), 'config', config_file)
        
        try:
            if config_file.endswith('.cfg'):
                # Extract numeric value from config filename
                config_number = int(config_file.split('.')[0]) if config_file.split('.')[0].isdigit() else 0
                
                # Handle .cfg files
                config = configparser.ConfigParser()
                config.read(config_path)
                
                # Try to read from DEFAULT section first, then from any section
                if 'url' in config['DEFAULT']:
                    url_data.append({
                        'url': config['DEFAULT']['url'],
                        'language': config_number,
                        'categories': 0  # Default category for .cfg files
                    })
                else:
                    for section in config.sections():
                        if 'url' in config[section]:
                            url_data.append({
                                'url': config[section]['url'],
                                'language': config_number,
                                'categories': 0  # Default category for .cfg files
                            })
                            
                # Also try reading as simple key=value format
                if not url_data:
                    with open(config_path, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, value = line.split('=', 1)
                                if key.strip().lower() == 'url':
                                    url_data.append({
                                        'url': value.strip(),
                                        'language': config_number,
                                        'categories': 0  # Default category for .cfg files
                                    })
                                    
            elif config_file.endswith('.json'):
                # Handle .json files
                with open(config_path, 'r') as f:
                    data = json.load(f)
                    language = data.get('language', 'unknown')
                    
                    if 'categories' in data:
                        # Extract numeric value from config filename (e.g., "1.json" -> 1)
                        config_number = int(config_file.split('.')[0]) if config_file.split('.')[0].isdigit() else 0
                        
                        # Process categories and their URLs
                        for category_id, category_info in data['categories'].items():
                            # Use category_id as numeric value (1,2,3,4)
                            category_numeric = int(category_id)
                            
                            url_data.append({
                                'url': category_info['url'],
                                'language': config_number,  # Use config file number as language identifier
                                'categories': category_numeric  # Use category ID (1,2,3,4)
                            })
                    elif 'urls' in data:
                        # Extract numeric value from config filename
                        config_number = int(config_file.split('.')[0]) if config_file.split('.')[0].isdigit() else 0
                        
                        # Fallback for simple URL list
                        for url in data['urls']:
                            url_data.append({
                                'url': url,
                                'language': config_number,
                                'categories': 0  # Default category
                            })
                    elif 'url' in data:
                        # Extract numeric value from config filename
                        config_number = int(config_file.split('.')[0]) if config_file.split('.')[0].isdigit() else 0
                        
                        url_data.append({
                            'url': data['url'],
                            'language': config_number,
                            'categories': 0  # Default category
                        })
                        
            logger.info(f"Loaded {len(url_data)} URLs from {config_file}")
            return url_data
            
        except Exception as e:
            logger.error(f"Error loading config file {config_file}: {e}")
            return []
    
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
            # Clean the time string - remove any extra whitespace and non-numeric characters except colons
            cleaned_time = time_str.strip()
            logger.debug(f"Converting time string: '{time_str}' -> cleaned: '{cleaned_time}'")
            
            # Split the time string into parts
            parts = cleaned_time.split(':')
            
            if len(parts) == 2:  # MM:SS format
                minutes, seconds = map(int, parts)
                result = minutes * 60 + seconds
                logger.debug(f"Converted {cleaned_time} to {result} seconds (MM:SS format)")
                return result
            elif len(parts) == 3:  # HH:MM:SS format
                hours, minutes, seconds = map(int, parts)
                result = hours * 3600 + minutes * 60 + seconds
                logger.debug(f"Converted {cleaned_time} to {result} seconds (HH:MM:SS format)")
                return result
            else:
                logger.warning(f"Unexpected time format: '{time_str}' (parts: {parts})")
                return 0
        except Exception as e:
            logger.warning(f"Error converting time '{time_str}' to seconds: {e}")
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
    
    def search(self, url: str, language: str = 'unknown', categories: str = 'unknown') -> List[Dict[str, Any]]:
        """
        Search YouTube using the provided URL.
        
        Args:
            url: The YouTube search URL
            language: Language from config file
            categories: Category from config file
            
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
                        
                        # Channel information is no longer needed - using language and categories instead
                        
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
                            
                            # Try to get video length - try multiple selectors based on actual YouTube HTML structure
                            length = "Unknown"
                            selectors = [
                                ".badge-shape-wiz__text",  # New YouTube badge structure
                                "#text.ytd-thumbnail-overlay-time-status-renderer",  # Span with id='text'
                                "span#text.style-scope.ytd-thumbnail-overlay-time-status-renderer",  # Full span selector
                                "ytd-thumbnail-overlay-time-status-renderer span#text",  # Within time status renderer
                                "badge-shape .badge-shape-wiz__text",  # Badge shape text
                                "div.badge-shape-wiz__text",  # Direct badge text div
                                "span.ytd-thumbnail-overlay-time-status-renderer",  # Original selector
                                "[aria-label*='minuti'] span",  # Italian minutes
                                "[aria-label*='minutes'] span",  # English minutes
                                "[aria-label*='secondi'] span",  # Italian seconds
                                "[aria-label*='seconds'] span"  # English seconds
                            ]
                            
                            for selector in selectors:
                                try:
                                    length_element = element.find_element(By.CSS_SELECTOR, selector)
                                    length_text = length_element.text.strip()
                                    if length_text and length_text != "" and ":" in length_text:
                                        length = length_text
                                        logger.debug(f"Found length '{length}' using selector: {selector}")
                                        break
                                except:
                                    continue
                            
                            if length == "Unknown" or length == "":
                                logger.warning(f"Could not find length for video {idx} - tried all selectors")
                            
                        except:
                            metadata = "No metadata"
                            length = "Unknown"
                            logger.warning(f"Could not find metadata for video {idx}")
                            continue  # Skip this video if metadata is not found
                        
                        # Skip if length is still unknown
                        if length == "Unknown":
                            logger.info(f"Skipping video {idx} - Length is unknown")
                            continue
                        
                        # Convert length to seconds
                        length_seconds = self._convert_time_to_seconds(length)
                        
                        logger.info(f"\nVideo {idx} details:")
                        logger.info(f"Title: {title}")
                        logger.info(f"URL: {url}")
                        logger.info(f"Thumbnail: {thumbnail_url}")
                        logger.info(f"Language: {language}")
                        logger.info(f"Categories: {categories}")
                        logger.info(f"Length: {length} ({length_seconds} seconds)")
                        logger.info(f"Metadata: {metadata}")
                        
                        video_info = {
                            'title': title,
                            'url': url,
                            'thumbnail_url': thumbnail_url,
                            'language': language,
                            'categories': categories,
                            'length': length_seconds,
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

    def _setup_authentication(self, ydl_opts: dict) -> str:
        """
        Setup authentication for yt-dlp with multiple fallback methods.
        
        Args:
            ydl_opts: yt-dlp options dictionary to modify
            
        Returns:
            str: Description of authentication method used
        """
        # Priority order: cookie file -> .netrc -> browser cookies -> no auth
        
        # 1. Try cookie file (highest priority)
        cookie_file = '/app/youtube_cookies.txt'
        if os.path.exists(cookie_file):
            ydl_opts['cookiefile'] = cookie_file
            logger.info(f"Using cookie file: {cookie_file}")
            return "cookie_file"
        
        # 2. Try .netrc file
        netrc_file = '/app/.netrc'
        if os.path.exists(netrc_file):
            ydl_opts['netrc'] = True
            logger.info(f"Using .netrc file: {netrc_file}")
            return "netrc"
        
        # 3. Try browser cookies (if Chrome is available)
        chrome_config_path = '/root/.config/google-chrome'
        if os.path.exists(chrome_config_path):
            try:
                ydl_opts['cookiesfrombrowser'] = ('chrome',)
                logger.info("Using cookies from Chrome browser")
                return "browser_cookies"
            except Exception as e:
                logger.warning(f"Could not use browser cookies: {e}")
        
        # 4. No authentication - add fallback options
        logger.warning("No authentication available - using fallback options")
        self._add_no_auth_fallback(ydl_opts)
        return "no_auth_fallback"
    
    def _add_no_auth_fallback(self, ydl_opts: dict):
        """
        Add fallback options for unauthenticated downloads.
        
        Args:
            ydl_opts: yt-dlp options dictionary to modify
        """
        # Use alternative clients that may work without authentication
        ydl_opts['extractor_args']['youtube'].update({
            'player_client': ['mweb', 'web', 'android'],
            'skip': ['hls', 'dash'],  # Skip formats that might require auth
            'player_skip': ['webpage', 'configs'],
        })
        
        # Add more conservative settings
        ydl_opts.update({
            'sleep_interval': 2,  # Longer delays
            'max_sleep_interval': 10,
            'retries': 20,  # More retries
            'fragment_retries': 20,
        })
        
        # Update headers to be less detectable
        ydl_opts['http_headers'].update({
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'X-Forwarded-For': '8.8.8.8',  # Use Google DNS
        })
        
        logger.info("Applied no-auth fallback configuration")

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
        
        # Base yt-dlp options with enhanced authentication
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': f'{video_id}.%(ext)s',  # Use video ID for initial download
            'quiet': False,  # Enable output for debugging
            'no_warnings': False,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'nocheckcertificate': True,
            'no_playlist': True,
            'geo_bypass': True,
            'retries': 15,
            'fragment_retries': 15,
            'socket_timeout': 60,
            'http_chunk_size': 1048576,  # Reduced chunk size to avoid throttling
            'verbose': True,
            'sleep_interval': 1,  # Add delay between requests
            'max_sleep_interval': 5,
            # Enhanced extractor arguments for YouTube
            'extractor_args': {
                'youtube': {
                    'skip': ['hls'],  # Only skip HLS, keep DASH for better quality
                    'player_skip': ['configs'],
                    'player_client': ['mweb', 'web'],  # Try mobile web client first
                }
            },
            # Add headers to appear more like a real browser
            'http_headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip,deflate',
                'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                'Keep-Alive': '300',
                'Connection': 'keep-alive',
            }
        }
        
        # Enhanced authentication setup with multiple fallbacks
        auth_method = self._setup_authentication(ydl_opts)
        logger.info(f"Authentication method: {auth_method}")
        
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    logger.info(f"Attempting to download video (attempt {retry_count + 1}/{max_retries}): {url}")
                    try:
                        info = ydl.extract_info(url, download=True)
                    except Exception as e:
                        error_msg = str(e).lower()
                        logger.error(f"First attempt failed: {e}")
                        
                        # Handle specific authentication errors
                        if "sign in to confirm" in error_msg or "bot" in error_msg:
                            logger.warning("Authentication/bot detection error - trying alternative approach")
                            # Try with different client and more conservative settings
                            alt_opts = ydl_opts.copy()
                            alt_opts['extractor_args']['youtube'].update({
                                'player_client': ['android', 'mweb'],
                                'skip': ['webpage'],
                                'player_skip': ['webpage', 'configs'],
                            })
                            alt_opts['sleep_interval'] = 3
                            
                            with yt_dlp.YoutubeDL(alt_opts) as alt_ydl:
                                logger.info("Trying with alternative client configuration...")
                                info = alt_ydl.extract_info(url, download=True)
                        else:
                            # Try with video ID directly for other errors
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
                    # Handle specific error types with different strategies
                    error_msg = str(last_error).lower()
                    
                    if "sign in to confirm" in error_msg or "bot" in error_msg:
                        # For authentication errors, try removing cookies on next attempt
                        if retry_count == 1 and 'cookiefile' in ydl_opts:
                            logger.warning("Cookies may be expired - trying without cookies on next attempt")
                            ydl_opts_backup = ydl_opts.copy()
                            ydl_opts.pop('cookiefile', None)
                            self._add_no_auth_fallback(ydl_opts)
                    
                    wait_time = min(2 ** retry_count, 30)  # Exponential backoff with max 30s
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} download attempts failed")
                    logger.error(f"Final error: {last_error}")
                    
                    # Provide helpful error message based on error type
                    error_msg = str(last_error).lower()
                    if "sign in to confirm" in error_msg or "bot" in error_msg:
                        logger.error("Authentication required. Please check:")
                        logger.error("1. YouTube cookies are valid and not expired")
                        logger.error("2. Cookies were exported correctly from a private/incognito session")
                        logger.error("3. Consider using a different IP address or VPN")
                    
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

    def submit_to_justjackpot(self, video_data: dict, language: int = 1, category: int = 1) -> bool:
        """
        Submit video data to JustJackpot API.
        
        Args:
            video_data: Dictionary containing video information
            language: Language ID for the video
            category: Category ID for the video
            
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
                'categoria': str(category),  # Use dynamic category
                'lingua': str(language),  # Use dynamic language
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

    def _get_language_category_combinations(self):
        """Get all language-category combinations from config files."""
        combinations = set()
        config_dir = os.path.join(os.path.dirname(__file__), 'config')
        
        if not os.path.exists(config_dir):
            logger.warning(f"Config directory not found: {config_dir}")
            return list(combinations)
        
        for filename in os.listdir(config_dir):
            if filename.endswith('.json'):
                try:
                    url_data_list = self.load_urls_from_config(filename)
                    if url_data_list:
                        # load_urls_from_config returns a list of dictionaries
                        for url_data in url_data_list:
                            language = url_data.get('language')
                            category = url_data.get('categories')
                            
                            if language and category:
                                combinations.add((language, category))
                except Exception as e:
                    logger.error(f"Error loading config file {filename}: {e}")
        
        return list(combinations)

    def process_pending_videos(self):
        """Process videos that need upload dates and resize their thumbnails.
        Uploads one video per category per language combination per run.
        """
        logger.info("\n" + "="*50)
        logger.info("Starting process_pending_videos")
        logger.info("="*50 + "\n")
        
        videos_processed = 0  # Initialize at the beginning
        
        if not self.db:
            logger.error("Database not initialized")
            return
            
        try:
            # Get all available language-category combinations from config files
            language_category_combinations = self._get_language_category_combinations()
            
            if not language_category_combinations:
                logger.info("No language-category combinations found in config files")
                return
            
            logger.info(f"Found {len(language_category_combinations)} language-category combinations: {language_category_combinations}")
            
            # Get one video per language-category combination
            videos = self.db.get_pending_videos_by_category_language(language_category_combinations)
            
            if not videos:
                logger.info("No videos need processing")
                return
                
            logger.info(f"Processing {len(videos)} videos")
            
            for video in videos:
                language = video.get('language', 'unknown')
                categories = video.get('categories', 'unknown')
                
                logger.info(f"Processing video: {video['url']} (language={language}, categories={categories})")
                
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
                
                # Submit to JustJackpot with correct language and category
                if self.submit_to_justjackpot(video_data, language=language, category=categories):
                    logger.info(f"Video submitted to JustJackpot for {language}/{categories}")
                    videos_processed += 1
                else:
                    logger.error(f"Failed to submit video to JustJackpot for {language}/{categories}")
            
            logger.info(f"Total videos processed: {videos_processed}")
                    
        except Exception as e:
            logger.error(f"Error processing videos: {e}")
        finally:
            logger.info(f"Finished processing. Total videos uploaded: {videos_processed}")
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
        # Automatically discover all .json config files
        config_dir = os.path.join(os.path.dirname(__file__), 'config')
        config_files = [f for f in os.listdir(config_dir) if f.endswith('.json')]
        
        if not config_files:
            logger.warning("No .json config files found in config directory")
            return
        
        logger.info(f"Found {len(config_files)} config files: {config_files}")
        
        for config_file in config_files:
            logger.info(f"Processing config file: {config_file}")
            url_data_list = scraper.load_urls_from_config(config_file)
            
            for url_data in url_data_list:
                url = url_data['url']
                language = url_data['language']
                categories = url_data['categories']
                logger.info(f"Starting search with URL: {url} (Language: {language}, Category: {categories})")
                results = scraper.search(url, language, categories)
                logger.info("\nFinal Results:")
                for video in results:
                    logger.info(f"\nTitle: {video['title']}")
                    logger.info(f"URL: {video['url']}")
                    logger.info(f"Thumbnail: {video['thumbnail_url']}")
                    logger.info(f"Language: {video['language']}")
                    logger.info(f"Categories: {video['categories']}")
                    logger.info(f"Length: {video['length']} seconds")
                    logger.info(f"Metadata: {video['metadata']}")
                    logger.info("-" * 50)
            
    finally:
        scraper.process_pending_videos()
        scraper.close()

if __name__ == "__main__":
    main()