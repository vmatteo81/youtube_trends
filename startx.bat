docker build -t youtube-trends .

docker run -v ./data:/app/data youtube-trends python -m youtube_trends.web_scraper
