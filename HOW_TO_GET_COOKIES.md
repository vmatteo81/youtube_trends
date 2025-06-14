# How to Get YouTube Cookies for Authentication

Since YouTube no longer supports username/password authentication with yt-dlp, you need to extract cookies from your browser. Here are several methods:

## Method 1: Browser Extension (Recommended)

### Get cookies.txt LOCALLY Extension
1. Install the "Get cookies.txt LOCALLY" extension:
   - **Chrome**: [Chrome Web Store](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
   - **Firefox**: [Firefox Add-ons](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)

2. Go to [YouTube.com](https://youtube.com) and make sure you're logged in

3. Click the extension icon and select "Export" or "Get cookies.txt"

4. Save the file as `youtube_cookies.txt`

## Method 2: Manual Browser Export

### Chrome/Edge
1. Go to YouTube.com and log in
2. Press `F12` to open Developer Tools
3. Go to **Application** tab → **Storage** → **Cookies** → `https://www.youtube.com`
4. Look for these important cookies and copy their values:
   - `__Secure-1PSID`
   - `__Secure-3PSID` 
   - `HSID`
   - `SSID`
   - `APISID`
   - `SAPISID`

5. Create a `youtube_cookies.txt` file in Netscape format:
```
# Netscape HTTP Cookie File
.youtube.com	TRUE	/	TRUE	[expiry]	__Secure-1PSID	[value]
.youtube.com	TRUE	/	TRUE	[expiry]	__Secure-3PSID	[value]
.youtube.com	TRUE	/	TRUE	[expiry]	HSID	[value]
.youtube.com	TRUE	/	TRUE	[expiry]	SSID	[value]
.youtube.com	TRUE	/	TRUE	[expiry]	APISID	[value]
.youtube.com	TRUE	/	TRUE	[expiry]	SAPISID	[value]
```

### Firefox
1. Go to YouTube.com and log in
2. Press `F12` → **Storage** tab → **Cookies** → `https://www.youtube.com`
3. Follow the same process as Chrome

## Method 3: Command Line Tools

### Using yt-dlp itself
```bash
# This will save cookies to a file
yt-dlp --cookies-from-browser chrome --write-info-json --skip-download "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### Using browser_cookie3 (Python)
```python
import browser_cookie3

# Get cookies from Chrome
cookies = browser_cookie3.chrome(domain_name='youtube.com')

# Save to file
with open('youtube_cookies.txt', 'w') as f:
    f.write('# Netscape HTTP Cookie File\n')
    for cookie in cookies:
        f.write(f'{cookie.domain}\t{str(cookie.domain_specified).upper()}\t{cookie.path}\t{str(cookie.secure).upper()}\t{cookie.expires or 0}\t{cookie.name}\t{cookie.value}\n')
```

## Adding Cookies to GitHub Actions

1. Copy the entire content of your `youtube_cookies.txt` file

2. Go to your GitHub repository → **Settings** → **Secrets and variables** → **Actions**

3. Click **New repository secret**

4. Name: `YOUTUBE_COOKIES`

5. Value: Paste the entire cookie file content

6. Click **Add secret**

## Alternative: Username/Password (Limited Support)

If you prefer username/password (though not recommended for YouTube), you can add these secrets:

1. `YOUTUBE_USERNAME`: Your YouTube/Google email
2. `YOUTUBE_PASSWORD`: Your account password or app-specific password

**Note**: This method has limited success with YouTube and may require app-specific passwords if you have 2FA enabled.

## Security Notes

⚠️ **Important Security Considerations**:

- Cookies contain sensitive authentication data
- Only share cookies through secure channels (GitHub Secrets)
- Cookies expire and may need periodic updates
- Never commit cookie files to your repository
- Consider using a dedicated YouTube account for automation

## Troubleshooting

### Cookies Not Working
- Ensure you're logged into YouTube when extracting cookies
- Check that cookies haven't expired
- Try extracting fresh cookies
- Verify the cookie format is correct (Netscape format)

### Still Getting Authentication Errors
- YouTube may have additional bot detection
- Try using different user agents
- Consider rate limiting your requests
- Some videos may still be restricted

### Cookie Expiration
- YouTube cookies typically last 1-2 years
- Monitor your scraper for authentication failures
- Set up alerts for when cookies need refreshing

## Testing Your Cookies

Test your cookies locally before adding to GitHub:

```bash
# Test with yt-dlp
yt-dlp --cookies youtube_cookies.txt "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

If this works, your cookies are valid and ready to use!