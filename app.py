import streamlit as st
import pandas as pd
import re
import openai
import matplotlib.pyplot as plt
from collections import Counter
from wordcloud import WordCloud
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
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

# Function to fetch YouTube comments and replies
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
            comments.append(top_comment)

            # Get replies if available
            if "replies" in item:
                for reply in item["replies"]["comments"]:
                    reply_text = reply["snippet"]["textDisplay"]
                    comments.append(reply_text)

        return comments if comments else ["No comments found."]

    except HttpError as e:
        st.error(f"Google API Error: {e}")
        return ["Error fetching comments."]

    except Exception as e:
        st.error(f"An error occurred: {e}")
        return ["Error fetching comments."]

# Function to fetch YouTube transcript
def get_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([t['text'] for t in transcript_list])
        return transcript_text
    except TranscriptsDisabled:
        st.warning("Transcript is disabled or unavailable for this video.")
        return "Transcript unavailable."
    except Exception:
        st.warning("An error occurred while fetching the transcript.")
        return "Transcript unavailable."

# Function to extract keyword trends
def extract_keywords(text, top_n=10):
    words = text.lower().split()
    common_words = Counter(words).most_common(top_n)
    return [word for word, count in common_words]

# Function to analyze content gaps using OpenAI
def analyze_content(transcript, comments, keywords):
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

    ### Trending Keywords:
    {', '.join(keywords)}

    ### Video Transcript:
    {transcript}

    ### Comments & Replies:
    {', '.join(comments)}

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

# Function to generate word cloud
def generate_wordcloud(text):
    wordcloud = WordCloud(width=800, height=400, background_color="white").generate(text)
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")
    st.pyplot(plt)

# Streamlit UI
st.title("YouTube Content Gap Analyzer")
st.write("Paste a YouTube link to extract transcript, comments, keyword trends, and AI-generated content gap analysis.")

video_url = st.text_input("Enter YouTube Video URL")

if st.button("Analyze Video"):
    video_id = extract_video_id(video_url)

    if video_id:
        st.info("Fetching transcript and comments...")
        transcript = get_transcript(video_id)
        comments = get_comments(video_id)
        all_text = transcript + " " + " ".join(comments)

        if transcript != "Transcript unavailable." or comments != ["No comments found."]:
            keywords = extract_keywords(all_text, top_n=10)

            st.success("Data extracted successfully! Generating insights...")
            
            # Show trending keywords
            st.subheader("🔍 Trending Keywords")
            st.write(", ".join(keywords))

            # Generate word cloud
            st.subheader("📊 Audience Engagement Word Cloud")
            generate_wordcloud(all_text)

            # AI Content Analysis
            insights = analyze_content(transcript, comments, keywords)
            st.subheader("🤖 AI Content Gap Analysis")
            st.write(insights)
            
            # Save to file
            full_data = f"### Trending Keywords:\n{', '.join(keywords)}\n\n### Video Transcript:\n{transcript}\n\n### Comments & Replies:\n{', '.join(comments)}\n\n### AI Analysis:\n{insights}"
            st.download_button("Download Analysis", full_data.encode('utf-8'), file_name="content_analysis.txt", mime="text/plain")

        else:
            st.error("No transcript or comments available for this video.")
    else:
        st.error("Invalid YouTube URL. Please check and try again.")
