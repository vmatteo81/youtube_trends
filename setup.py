from setuptools import setup, find_packages

setup(
    name="youtube_trends",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "google-api-python-client>=2.108.0",
        "python-dotenv>=1.0.0",
        "beautifulsoup4>=4.12.0",
        "requests>=2.31.0",
        "selenium>=4.16.0",
        "webdriver-manager>=4.0.1",
    ],
    entry_points={
        "console_scripts": [
            "youtube-trends=youtube_trends.cli:main",
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="A tool to fetch YouTube trending videos",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/youtube_trends",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
) 