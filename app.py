import streamlit as st
import pandas as pd
import re
import openai
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load API keys from Streamlit Secrets
YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

openai.api_key = OPENAI_API_KEY

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
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
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
            comments.append(f"Comment: {top_comment}")

            # Get replies if available
            if "replies" in item:
                for reply in item["replies"]["comments"]:
                    reply_text = reply["snippet"]["textDisplay"]
                    comments.append(f"Reply: {reply_text}")

        return "\n".join(comments)  # Return as a single text block

    except HttpError as e:
        st.error(f"Google API Error: {e}")
        return ""

    except Exception as e:
        st.error(f"An error occurred: {e}")
        return ""

# Function to fetch transcript
def get_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([t['text'] for t in transcript_list])
        return transcript_text
    except:
        st.warning("Transcript unavailable for this video.")
        return ""

# Function to analyze content gaps with OpenAI
def analyze_content(transcript, comments):
    system_prompt = """
    You are an expert in ADHD relationship coaching, analyzing YouTube content to identify content gaps.
    The audience struggles with ADHD-related relationship challenges, including communication breakdowns, misunderstandings, emotional dysregulation, and burnout.
    Your goal is to review the video transcript and audience comments to determine:
    - What topics are covered well?
    - What questions or pain points remain unaddressed?
    - What content could better resonate with this audience?
    """

    user_prompt = f"""
    Here is a YouTube video transcript and audience comments. Identify content gaps that would resonate with an ADHD audience.

    ### Video Transcript:
    {transcript}

    ### Comments & Replies:
    {comments}

    What insights can you provide on missing or underdeveloped topics?
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        st.error(f"Error fetching AI analysis: {e}")
        return "Error analyzing content."

# Streamlit UI
st.title("YouTube Content Gap Analyzer")
st.write("Paste a YouTube link to extract transcript, comments, and get an AI-generated content gap analysis.")

video_url = st.text_input("Enter YouTube Video URL")

if st.button("Analyze Video"):
    video_id = extract_video_id(video_url)

    if video_id:
        st.info("Fetching transcript and comments...")
        transcript = get_transcript(video_id)
        comments = get_comments(video_id)

        if transcript or comments:
            st.success("Data extracted successfully! Sending to ChatGPT for analysis...")
            insights = analyze_content(transcript, comments)
            
            # Display AI Analysis
            st.subheader("AI Content Gap Analysis:")
            st.write(insights)
            
            # Save to file
            full_data = f"### Video Transcript:\n{transcript}\n\n### Comments & Replies:\n{comments}\n\n### AI Analysis:\n{insights}"
            st.download_button("Download Analysis", full_data.encode('utf-8'), file_name="content_analysis.txt", mime="text/plain")

        else:
            st.error("No transcript or comments available for this video.")
    else:
        st.error("Invalid YouTube URL. Please check and try again.")
