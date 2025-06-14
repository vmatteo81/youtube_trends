# YouTube Cookies Setup for yt-dlp

This document explains how to set up YouTube cookies to avoid authentication errors when downloading videos.

## Problem

YouTube may block yt-dlp requests with errors like:
```
ERROR: [youtube] Sign in to confirm you're not a bot. Use --cookies-from-browser or --cookies for the authentication.
```

## Solutions

### Option 1: Browser Cookies (Recommended for Local Development)

The scraper will automatically try to extract cookies from your Chrome browser when running locally. This works out of the box if you're logged into YouTube in Chrome.

### Option 2: Cookie File (Recommended for Docker/Production)

1. **Export cookies from your browser:**
   - Install a browser extension like "Get cookies.txt LOCALLY" for Chrome/Firefox
   - Navigate to YouTube and make sure you're logged in
   - Use the extension to export cookies for `youtube.com`
   - Save the file as `youtube_cookies.txt`

2. **For Docker deployment:**
   - Place the `youtube_cookies.txt` file in your project root
   - Update your Docker run command to mount the cookie file:
   ```bash
   docker run -v $(pwd)/youtube_cookies.txt:/app/youtube_cookies.txt youtube-scraper
   ```

3. **For GitHub Actions:**
   - Add your cookie file content as a GitHub secret named `YOUTUBE_COOKIES`
   - Update your workflow to create the cookie file:
   ```yaml
   - name: Create YouTube cookies file
     run: |
       printf '%s' "${{ secrets.YOUTUBE_COOKIES }}" > youtube_cookies.txt
   ```

### Option 3: Alternative yt-dlp Clients

If cookies don't work, you can try using different YouTube clients by modifying the extractor arguments:

```python
'extractor_args': {
    'youtube': {
        'player_client': ['mweb'],  # Try mobile web client
        'skip': ['hls', 'dash'],
    }
}
```

## Security Notes

- **Never commit cookie files to your repository**
- Cookies contain authentication tokens that could compromise your YouTube account
- Use environment variables or secrets for production deployments
- Consider using a dedicated YouTube account for scraping
- Rotate cookies regularly as they expire

## Troubleshooting

1. **"No cookies available" warning:**
   - This means the scraper couldn't find browser cookies or a cookie file
   - The scraper will still attempt downloads but may fail on some videos

2. **"Could not use browser cookies" warning:**
   - This is normal in Docker environments where Chrome browser isn't available
   - Use the cookie file method instead

3. **Still getting authentication errors:**
   - Try refreshing your cookies (re-export from browser)
   - Ensure you're logged into YouTube when exporting cookies
   - Try using a different browser or incognito mode when exporting

## Cookie File Format

The cookie file should be in Netscape format (standard for yt-dlp):
```
# Netscape HTTP Cookie File
.youtube.com	TRUE	/	FALSE	1234567890	cookie_name	cookie_value
```

Most browser extensions will export in the correct format automatically.