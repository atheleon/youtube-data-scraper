import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import json
from datetime import datetime, timedelta

def get_channel_videos(channel_url, max_videos=20):
    try:
        # Ensure the URL leads to the channel's videos page
        if "/@" in channel_url and not channel_url.endswith('/videos'):
            channel_url = channel_url.rstrip('/') + '/videos'

        # Send a GET request to the channel's videos page
        response = requests.get(channel_url)
        response.raise_for_status()
        
        # Parse the page content with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract JSON data from the script tags
        yt_initial_data = None
        try:
            script_tags = soup.find_all('script')
            for script in script_tags:
                if 'var ytInitialData' in script.string if script.string else '':
                    yt_initial_data = script.string
                    break
            if not yt_initial_data:
                raise ValueError("Could not find the script tag with video data.")
        except Exception as e:
            print(f"Error extracting script tag containing JSON data: {e}")
            return pd.DataFrame()

        # Parse JSON data
        try:
            json_str = re.search(r'var ytInitialData = ({.*});', yt_initial_data).group(1)
            data = json.loads(json_str)
        except Exception as e:
            print(f"Error parsing JSON data: {e}")
            return pd.DataFrame()

        # Locate the videos tab in the JSON data
        try:
            video_elements = data['contents']['twoColumnBrowseResultsRenderer']['tabs']
            videos_tab = next((tab for tab in video_elements if 'tabRenderer' in tab and 
                               tab['tabRenderer'].get('title', '').lower() == 'videos'), None)
            if not videos_tab:
                raise ValueError("Could not find the 'videos' tab in the channel data.")
        except Exception as e:
            print(f"Error locating the videos tab in JSON data: {e}")
            return pd.DataFrame()

        # Attempt to locate the video items in different structures
        video_items = []
        try:
            # First attempt: Look for 'sectionListRenderer'
            video_items = videos_tab['tabRenderer']['content']['sectionListRenderer']['contents'][0] \
                          ['itemSectionRenderer']['contents'][0]['gridRenderer']['items']
        except KeyError:
            try:
                # Alternative attempt: Look for 'richGridRenderer'
                video_items = videos_tab['tabRenderer']['content']['richGridRenderer']['contents']
                # Filter only video items
                video_items = [item['richItemRenderer']['content']['videoRenderer'] for item in video_items 
                               if 'richItemRenderer' in item and 'videoRenderer' in item['richItemRenderer']['content']]
            except Exception as e:
                print(f"Error locating video items in JSON data: {e}")
                return pd.DataFrame()

        # Extract video data
        videos = []
        for video in video_items[:max_videos]:
            try:
                title = video['title']['runs'][0]['text']
                video_url = f"https://www.youtube.com/watch?v={video['videoId']}"
                
                views_text = video.get('viewCountText', {}).get('simpleText', '0 views')
                views = int(re.sub(r'[^\d]', '', views_text))  # Extract digits from text
                
                upload_date = video.get('publishedTimeText', {}).get('simpleText', 'Unknown')
                upload_date = parse_relative_date(upload_date)  # Convert relative date to absolute date

                # Fetch additional data from the video page
                video_details = get_video_details(video_url)

                videos.append({
                    'title': title,
                    'url': video_url,
                    'views': views,
                    'upload_date': upload_date,
                    'duration': video_details.get('duration', 0),
                    'likes': video_details.get('likes', 0),
                    'tags': video_details.get('tags', ''),
                    'location': video_details.get('location', ''),
                    'subscriber_count': video_details.get('subscriber_count', 0),
                })
            except KeyError as ke:
                print(f"KeyError extracting video data: {ke}")
                continue
            except Exception as e:
                print(f"Error extracting video data: {e}")
                continue

        return pd.DataFrame(videos)
    except Exception as e:
        print(f"An unexpected error occurred while retrieving videos: {e}")
        return pd.DataFrame()

def get_video_details(video_url):
    """Fetch details from the individual video page, such as likes, tags, location, and subscriber count."""
    try:
        response = requests.get(video_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract likes
        likes_text = soup.find('meta', {'itemprop': 'interactionCount'})['content']
        likes = int(likes_text) if likes_text.isdigit() else 0
        
        # Extract subscriber count
        subscriber_element = soup.find('yt-formatted-string', {'id': 'owner-sub-count'})
        subscriber_count_text = subscriber_element.text if subscriber_element else '0 subscribers'
        subscriber_count = int(re.sub(r'[^\d]', '', subscriber_count_text))
        
        # Extract tags (in meta keywords)
        tags = soup.find('meta', {'name': 'keywords'})
        tags_content = tags['content'] if tags else ''
        
        # Extract location (if available)
        location_element = soup.find('meta', {'itemprop': 'contentLocation'})
        location = location_element['content'] if location_element else ''
        
        # Extract duration
        duration_element = soup.find('meta', {'itemprop': 'duration'})
        duration = parse_duration(duration_element['content']) if duration_element else 0
        
        return {
            'likes': likes,
            'tags': tags_content,
            'location': location,
            'subscriber_count': subscriber_count,
            'duration': duration
        }
    except Exception as e:
        print(f"Error fetching video details for {video_url}: {e}")
        return {}

def parse_relative_date(relative_date):
    """Convert relative date (e.g., '1 day ago') to an absolute date."""
    try:
        today = datetime.now()

        if 'day' in relative_date:
            days_ago = int(re.search(r'(\d+) day', relative_date).group(1))
            return today - timedelta(days=days_ago)
        elif 'week' in relative_date:
            weeks_ago = int(re.search(r'(\d+) week', relative_date).group(1))
            return today - timedelta(weeks=weeks_ago)
        elif 'month' in relative_date:
            months_ago = int(re.search(r'(\d+) month', relative_date).group(1))
            return today - timedelta(days=30 * months_ago)  # Approximate month as 30 days
        elif 'year' in relative_date:
            years_ago = int(re.search(r'(\d+) year', relative_date).group(1))
            return today - timedelta(days=365 * years_ago)  # Approximate year as 365 days

        return today
    except Exception as e:
        print(f"Error parsing relative date '{relative_date}': {e}")
        return datetime.now()

def parse_duration(duration):
    try:
        # Example duration format: 'PT15M33S'
        match = re.match(r'PT(\d+H)?(\d+M)?(\d+S)?', duration)
        hours = int(match.group(1)[:-1]) if match.group(1) else 0
        minutes = int(match.group(2)[:-1]) if match.group(2) else 0
        seconds = int(match.group(3)[:-1]) if match.group(3) else 0
        return hours * 3600 + minutes * 60 + seconds
    except Exception as e:
        print(f"Error parsing duration '{duration}': {e}")
        return 0

def analyze_videos(video_df):
    try:
        video_df['upload_date'] = pd.to_datetime(video_df['upload_date'], errors='coerce')
        avg_views = video_df['views'].mean()
        avg_likes = video_df['likes'].mean()
        avg_duration = video_df['duration'].mean()
        avg_subscriber_count = video_df['subscriber_count'].mean()
        
        print(f"Average Views: {avg_views}")
        print(f"Average Likes: {avg_likes}")
        print(f"Average Duration (seconds): {avg_duration}")
        print(f"Average Subscriber Count at Upload: {avg_subscriber_count}")
        
        stats = {
            'average_views': avg_views,
            'average_likes': avg_likes,
            'average_duration': avg_duration,
            'average_subscriber_count': avg_subscriber_count
        }
        
        return stats
    except Exception as e:
        print(f"Error analyzing video data: {e}")
        return {}

def save_to_csv(video_df, stats, filename='youtube_data_analysis.csv'):
    try:
        summary_df = pd.DataFrame([stats])
        combined_df = pd.concat([video_df, summary_df], ignore_index=True)
        combined_df.to_csv(filename, index=False)
        print(f"Data and analysis saved to {filename}")
    except Exception as e:
        print(f"Error saving data to CSV: {e}")

# Main script execution
channel_url = input("Enter the full URL of the YouTube channel: ").strip()
video_df = get_channel_videos(channel_url)

if not video_df.empty:
    stats = analyze_videos(video_df)
    save_to_csv(video_df, stats)
else:
    print("No video data to analyze.")
