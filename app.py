import streamlit as st
import pandas as pd
import re
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load API key from Streamlit Secrets
API_KEY = st.secrets["YOUTUBE_API_KEY"]

# Function to extract video ID from URL
def extract_video_id(url):
    match = re.search(r"v=([a-zA-Z0-9_-]{11})", url)  # Standard YouTube URL
    if not match:
        match = re.search(r"youtu\.be/([a-zA-Z0-9_-]{11})", url)  # Shortened URL
    if not match:
        match = re.search(r"shorts/([a-zA-Z0-9_-]{11})", url)  # Shorts URL
    return match.group(1) if match else None

# Function to fetch comments and replies
def get_comments(video_id):
    youtube = build("youtube", "v3", developerKey=API_KEY)
    comments = []
    
    try:
        request = youtube.commentThreads().list(
            part="snippet,replies",
            videoId=video_id,
            maxResults=100
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

        # Show comments in the app for debugging
        st.write("Fetched Comments:", comments)

        return pd.DataFrame(comments)

    except HttpError as e:
        st.error(f"Google API Error: {e}")
        return pd.DataFrame()

    except Exception as e:
        st.error(f"An error occurred: {e}")
        return pd.DataFrame()

# Streamlit UI
st.title("YouTube Comment Extractor")
st.write("Paste a YouTube link to extract comments and replies.")

# Input field for YouTube URL
video_url = st.text_input("Enter YouTube Video URL")

if st.button("Fetch Comments"):
    video_id = extract_video_id(video_url)

    if video_id:
        df = get_comments(video_id)

        if not df.empty:
            # Save as CSV properly formatted
            csv_data = df.to_csv(index=False, encoding='utf-8')
            st.success("Comments extracted successfully!")

            # Provide download button
            st.download_button(label="Download Comments",
                               data=csv_data.encode('utf-8'),
                               file_name="youtube_comments.csv",
                               mime="text/csv")
        else:
            st.error("No comments found for this video.")
    else:
        st.error("Invalid YouTube URL. Please check and try again.")
