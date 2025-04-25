import streamlit as st
import re
import time
import requests
from youtube_transcript_api import YouTubeTranscriptApi

# Groq API details
GROQ_API_KEY = "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"  # Replace with your actual key
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
TOKEN_LIMIT = 250  # Smaller chunks to prevent exceeding TPM limit
RATE_LIMIT_DELAY = 15  # Wait time when hitting rate limits

# Function to extract video ID from URL
def extract_video_id(url):
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
    return match.group(1) if match else None

# Function to fetch YouTube transcript
def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([t["text"] for t in transcript])
    except Exception as e:
        return f"Error fetching transcript: {e}"

# Function to split text into smaller chunks
def split_text(text, chunk_size):
    words = text.split()
    return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]

# Function to summarize text with dynamic rate limit handling
def summarize_text(text):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-8b-8192",  # Lower-cost model to reduce token usage
        "messages": [
            {"role": "system", "content": "Summarize the given text **in 2-3 bullet points**."},
            {"role": "user", "content": text}
        ]
    }

    while True:
        response = requests.post(GROQ_API_URL, json=payload, headers=headers)

        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]

        elif response.status_code == 429:  # Rate limit exceeded
            retry_after = response.headers.get("Retry-After", RATE_LIMIT_DELAY)
            st.warning(f"⚠️ Rate limit exceeded. Waiting {retry_after} seconds before retrying...")
            time.sleep(int(retry_after))  # Dynamically wait based on API response

        else:
            return f"Error summarizing text: {response.text}"

# Streamlit UI
st.title("🎥 YouTube Video Summarizer with Groq")
video_url = st.text_input("Enter YouTube Video URL")

if st.button("Summarize"):
    if video_url:
        video_id = extract_video_id(video_url)
        if video_id:
            transcript = get_transcript(video_id)
            if "Error" not in transcript:
                chunks = split_text(transcript, TOKEN_LIMIT)  # Smaller chunks to avoid limits
                summaries = []
                
                for chunk in chunks:
                    summary = summarize_text(chunk)
                    summaries.append(summary)
                    time.sleep(3)  # Small delay to further prevent rate limit hits
                
                final_summary = "\n".join(summaries)  # No extra API call for final summary
                
                st.subheader("📃 Video Summary:")
                st.write(final_summary)
            else:
                st.error(transcript)
        else:
            st.error("Invalid YouTube URL. Please check and try again.")
    else:
        st.error("Please enter a YouTube video URL.")
