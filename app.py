import streamlit as st
import pandas as pd
from googleapiclient.discovery import build

# YouTube API Key (Replace with your actual API key)
API_KEY = "YOUR_YOUTUBE_API_KEY"

# Function to extract video ID from URL
import re

def extract_video_id(url):
    # Extract from standard YouTube URL
    match = re.search(r"v=([a-zA-Z0-9_-]{11})", url)
    if match:
        return match.group(1)
    
    # Extract from shortened YouTube URL
    match = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", url)
    if match:
        return match.group(1)

    # Extract from YouTube Shorts URL
    match = re.search(r"shorts/([a-zA-Z0-9_-]{11})", url)
    if match:
        return match.group(1)
    
    return None  # If no valid video ID found


# Function to fetch comments and replies
def get_comments(video_id):
    youtube = build("youtube", "v3", developerKey=API_KEY)
    comments = []
    
    request = youtube.commentThreads().list(
        part="snippet,replies",
        videoId=video_id,
        maxResults=100  # Adjust for more comments
    )
    
    response = request.execute()

    for item in response.get("items", []):
        top_comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
        comments.append({"Comment": top_comment, "Reply": None})

        # Get replies if available
        if "replies" in item:
            for reply in item["replies"]["comments"]:
                reply_text = reply["snippet"]["textDisplay"]
                comments.append({"Comment": None, "Reply": reply_text})

    return pd.DataFrame(comments)

# Streamlit UI
st.title("YouTube Comment Extractor")
st.write("Paste a YouTube link to extract comments and replies.")

video_url = st.text_input("Enter YouTube Video URL")
if st.button("Fetch Comments"):
    video_id = extract_video_id(video_url)
    
    if video_id:
        df = get_comments(video_id)
        
        # Save as CSV
        file_name = "youtube_comments.csv"
        df.to_csv(file_name, index=False)
        
        # Provide download link
        st.success("Comments extracted successfully!")
        st.download_button("Download Comments", file_name, file_name)
    else:
        st.error("Invalid YouTube URL. Please check and try again.")
