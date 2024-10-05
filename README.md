### README

Welcome to the **YouTube Scraper 3000**! This gloriously fragile script is your ticket to scraping basic information from a YouTube channel—until YouTube inevitably changes its layout, leaving this program utterly useless. With `channel_url`, you can input the full channel URL (in the new, obnoxious “@username” format) so the script can scrape, dig, and pry its way to some video data. Variables like `max_videos` let you limit the number of videos scraped because let’s be honest—you probably don’t want to trust this thing too much. It extracts `views`, `likes`, `upload_date`, `duration`, `tags`, and even `subscriber_count`, assuming YouTube hasn’t hidden them behind some JavaScript fortress yet. The crown jewel of this script, `get_video_details()`, attempts to dive into each video page to fish out metadata, but be warned: it’s as delicate as a house of cards. It uses `parse_relative_date()` to convert vague upload dates like "2 months ago" into real dates, but hey, good luck if that ever changes. This masterpiece may become deprecated, broken, or entirely useless at the slightest whisper of a YouTube update, so enjoy it while it lasts!

#### Example Usage

```python
# Main script execution
channel_url = input("Enter the full URL of the YouTube channel: ").strip()
video_df = get_channel_videos(channel_url)

if not video_df.empty:
    stats = analyze_videos(video_df)
    save_to_csv(video_df, stats)
else:
    print("No video data to analyze.")
```

#### Functions Overview

- **`get_channel_videos(channel_url, max_videos=10)`**: Scrapes the video details from the given channel URL. 
- **`get_video_details(video_url)`**: Extracts likes, tags, location, subscriber count, and duration from each video’s page.
- **`parse_relative_date(relative_date)`**: Converts relative dates like "2 months ago" to an absolute date format.
- **`analyze_videos(video_df)`**: Computes averages for views, likes, and subscriber counts.
- **`save_to_csv(video_df, stats, filename='youtube_data_analysis.csv')`**: Saves all the scraped data and analysis to a CSV file.
