import os
import re
import logging
from googleapiclient.discovery import build
from pytubefix import YouTube
from moviepy.editor import VideoFileClip, ImageClip, TextClip, CompositeVideoClip, concatenate_videoclips
from dotenv import load_dotenv
import requests
import subprocess
import textwrap
from random import shuffle
from PIL import Image, ImageDraw
import numpy as np
from skimage.filters import gaussian

# Automatically detect the script directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Define the path for the log file
log_file_path = os.path.join(SCRIPT_DIR, 'stderr.log')

# Ensure the directory exists
os.makedirs(SCRIPT_DIR, exist_ok=True)

# Set up logging to log errors and debug information
logging.basicConfig(
    filename=log_file_path,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load environment variables from .env file
load_dotenv()

# Get API key and Channel ID from environment variables
API_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID_YOUTUBE")

# Set up directories for downloads and output
YT_DOWNLOADS_DIR = os.path.join(SCRIPT_DIR, 'YtDownloads')
SHORTIFIED_VIDEOS_DIR = os.path.join(SCRIPT_DIR, 'ShortifiedYtVideos')

# Ensure directories exist
os.makedirs(YT_DOWNLOADS_DIR, exist_ok=True)
os.makedirs(SHORTIFIED_VIDEOS_DIR, exist_ok=True)

# Initialize YouTube API client
youtube = build('youtube', 'v3', developerKey=API_KEY)

def sanitize_filename(filename):
    """Remove invalid characters from filenames."""
    return re.sub(r'[<>:"/\\|?*]', '', filename)
    
def fetch_random_video():
    url = f"https://www.googleapis.com/youtube/v3/search?key={API_KEY}&channelId={CHANNEL_ID}&part=snippet,id&order=date&maxResults=50"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        data = response.json()

        if 'items' not in data:
            logging.error("No videos found or an error occurred in the API response.")
            return None

        video_ids = [item['id']['videoId'] for item in data['items'] if item['id'].get('videoId')]
        
        if not video_ids:
            logging.warning("No video IDs found in the response.")
            return None

        # Shuffle the video IDs to randomize order
        shuffle(video_ids)

        return [f"https://www.youtube.com/watch?v={video_id}" for video_id in video_ids]

    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch videos: {e}")
        return None

# Download video using pytube
def download_video(video_id, title):
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        logging.debug(f"Attempting to download video from URL: {url}")
        
        yt = YouTube(url)
        
        # Download the highest resolution video stream
        video_stream = yt.streams.filter(adaptive=True, file_extension='mp4', only_video=True).order_by('resolution').desc().first()
        audio_stream = yt.streams.filter(adaptive=True, file_extension='mp4', only_audio=True).first()
        
        if not video_stream or not audio_stream:
            logging.error(f"Could not find suitable video or audio streams for video {video_id}.")
            return None
        
        video_path = os.path.join(YT_DOWNLOADS_DIR, f"{sanitize_filename(title)}_video.mp4")
        audio_path = os.path.join(YT_DOWNLOADS_DIR, f"{sanitize_filename(title)}_audio.mp4")
        
        video_stream.download(output_path=YT_DOWNLOADS_DIR, filename=f"{sanitize_filename(title)}_video.mp4")
        audio_stream.download(output_path=YT_DOWNLOADS_DIR, filename=f"{sanitize_filename(title)}_audio.mp4")
        
        logging.info(f"Downloaded video and audio for video {video_id}.")
        
        return video_path, audio_path
    except Exception as e:
        logging.error(f"Error downloading video {video_id}: {e}")
        return None
    
def merge_video_audio(video_path, audio_path, output_path):
    try:
        command = [
            'ffmpeg', 
            '-i', video_path, 
            '-i', audio_path, 
            '-c:v', 'copy', 
            '-c:a', 'aac', 
            '-strict', 'experimental', 
            output_path
        ]
        subprocess.run(command, check=True)
        logging.info(f"Merged video and audio into {output_path}.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error merging video and audio: {e}")

def download_and_merge(video_id, title):
    paths = download_video(video_id, title)
    if paths:
        video_path, audio_path = paths
        output_path = os.path.join(YT_DOWNLOADS_DIR, f"{sanitize_filename(title)}.mp4")
        merge_video_audio(video_path, audio_path, output_path)
        return output_path
    return None

def break_text(text, max_lines=3, line_width=40):
    """
    Break text into multiple lines with a maximum number of lines and add ellipsis if the text exceeds.
    """
    # Wrap the text
    wrapped_text = textwrap.wrap(text, width=line_width)
    
    # If the text exceeds the maximum lines, truncate and add an ellipsis
    if len(wrapped_text) > max_lines:
        wrapped_text = wrapped_text[:max_lines]  # Keep only the first `max_lines` lines
        wrapped_text[-1] += '...'  # Add ellipsis to the last line

    # Join the lines back into a single string
    return '\n'.join(wrapped_text)

def create_rounded_rectangle(size, radius, color):
    """Create an image with a rounded rectangle."""
    img = Image.new('RGBA', size, color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([radius, 0, size[0] - radius, size[1]], fill=color)
    draw.rectangle([0, radius, size[0], size[1] - radius], fill=color)
    draw.pieslice([0, 0, 2 * radius, 2 * radius], 180, 270, fill=color)
    draw.pieslice([size[0] - 2 * radius, 0, size[0], 2 * radius], 270, 360, fill=color)
    draw.pieslice([0, size[1] - 2 * radius, 2 * radius, size[1]], 90, 180, fill=color)
    draw.pieslice([size[0] - 2 * radius, size[1] - 2 * radius, size[0], size[1]], 0, 90, fill=color)
    return img

def add_padding_and_radius(title_clip, padding, radius):
    """Add padding and rounded corners to a text clip."""
    # Create an image with rounded rectangle
    text_size = title_clip.size
    padded_size = (text_size[0] + 2 * padding, text_size[1] + 2 * padding)
    background_img = create_rounded_rectangle(padded_size, radius, color=(0, 0, 0, 250))  # Semi-transparent black background
    
    # Convert to moviepy clip
    background_clip = ImageClip(np.array(background_img), ismask=False).set_duration(title_clip.duration)
    
    # Place text clip over the background
    title_clip = title_clip.set_position(("center", "center"))
    return CompositeVideoClip([background_clip, title_clip.set_position(("center", "center"))])

def blur(image, sigma=10):
    """ Returns a blurred version of the image with adjustable blur strength """
    return gaussian(image.astype(float), sigma=sigma)

def trim_and_resize_video(input_path, title, outro_path, duration=55, watermark_path=None):
    try:
        # Load the main video and outro video
        clip = VideoFileClip(input_path)
        clip2 = VideoFileClip(input_path)
        outro_clip = VideoFileClip(outro_path)

        print(f"Original video duration: {clip.duration} seconds")
        print(f"Original video size: {clip.size}")

        # Trim the main video to 55 seconds
        clip = clip.subclip(0, duration)
        clip2 = clip2.subclip(0, duration)

        # Define the target size and minimum resolution
        target_size = (1080, 1920)  # Target resolution for vertical videos
        min_resolution = (360, 640)  # Define a minimum resolution

        # Handle very small resolutions
        original_size = clip.size
        if original_size[0] < min_resolution[0] or original_size[1] < min_resolution[1]:
            logging.warning(f"Original video resolution {original_size} is too small. Skipping resizing.")
            output_path = os.path.join(SHORTIFIED_VIDEOS_DIR, f"{sanitize_filename(title)}_short.mp4")
            clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=30)
        else:
            # Calculate scale factor to fit the video within the target dimensions
            original_width, original_height = clip.size
            target_width, target_height = target_size

            # Resize to fit within target dimensions
            scale_factor = min(target_width / original_width, target_height / original_height)
            new_width = int(original_width * scale_factor)
            new_height = int(original_height * scale_factor)

            # Create a blurry background
            blurred_clip = clip2.fl_image( blur )
            # If the resized blurred clip is wider than the target width, crop it from the center
            if blurred_clip.size[0] > target_width:
                # Calculate the left margin to crop
                crop_x_center = (blurred_clip.size[0] - target_width) // 2
                blurred_clip = blurred_clip.crop(x1=crop_x_center, y1=0, x2=crop_x_center + target_width, y2=target_height)
            # else:
            #     # If it is narrower, center it
            #     blurred_clip = blurred_clip.set_position(("center", "center"))

            # Resize while keeping the aspect ratio
            clip_resized = clip.resize(newsize=(new_width, new_height))

            # If resolution is higher than 720p, resize it down to 720p
            if clip_resized.size[1] > 720:
                clip_resized = clip_resized.resize(height=720)

            # Break the title text to fit within three lines
            wrapped_title = break_text(title, max_lines=3, line_width=40)

            # Define the path to the custom font
            custom_font_path = os.path.join(SCRIPT_DIR, "Fonts/Luciole-Regular.ttf")

            # Create text clip for title
            title_clip = TextClip(
                wrapped_title,
                fontsize=70,  # Increase fontsize for better visibility
                color='white',  # Text color
                bg_color='rgba(0, 0, 0, 0.6)',  # Semi-transparent background color
                font=custom_font_path,  # Path to the custom font file
                stroke_color='black',  # Outline color
                stroke_width=2,  # Outline width
                size=(target_width, 200),  # Size of the text box
                method='caption',  # Use caption method to handle line breaks
                align='center'  # Center align text
            )

            # Add padding and border radius
            padding = 20
            border_radius = 15
            title_with_padding = add_padding_and_radius(title_clip, padding, border_radius)
            
            title_clip = title_with_padding.set_position(('center', 'top')).set_duration(55)  # Duration is 55 seconds

            blurred_clip_added = blurred_clip.set_position(("center", "center"))
            clip_padded = clip_resized.set_position(("center", "center"))


            # Overlay the title text on top of the padded video
            final_clip = CompositeVideoClip([blurred_clip_added, clip_padded, title_clip])

            # Add watermark if provided
            if watermark_path:
                watermark = ImageClip(watermark_path)
                watermark = (watermark
                             .resize(height=100)  # Adjust watermark size as needed
                             .set_duration(55)  # Duration is 55 seconds
                             .set_position(("right", "bottom"))  # Position the watermark
                             .set_opacity(0.5))  # Adjust opacity as needed

                final_clip = CompositeVideoClip([final_clip, watermark])

            # Resize the outro clip to fit within the target dimensions and center it
            outro_width, outro_height = outro_clip.size
            scale_factor_outro = min(target_width / outro_width, target_height / outro_height)
            new_outro_width = int(outro_width * scale_factor_outro)
            new_outro_height = int(outro_height * scale_factor_outro)

            # Resize and pad the outro clip to match the target size
            outro_clip_resized = outro_clip.resize(newsize=(new_outro_width, new_outro_height))
            x_pad_outro = (target_width - outro_clip_resized.size[0]) // 2
            y_pad_outro = (target_height - outro_clip_resized.size[1]) // 2
            outro_clip_centered = outro_clip_resized.set_position((x_pad_outro, y_pad_outro))

            # Overlay outro clip over a blurred background as well
            # blurred_outro_background = create_blurry_background(outro_clip, target_size)
            outro_clip_centered = CompositeVideoClip([outro_clip_centered.set_duration(5)])

            # Concatenate the final video with the centered outro
            combined_clip = concatenate_videoclips([final_clip, outro_clip_centered], method="compose")

            # Save the combined video
            output_path = os.path.join(SHORTIFIED_VIDEOS_DIR, f"{sanitize_filename(title)}_short_with_outro.mp4")
            combined_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=30, bitrate="500k")
        
        logging.info(f"Video processed and saved as {output_path}.")
    except Exception as e:
        logging.error(f"Error trimming, resizing, or adding text to video {input_path}: {e}")

def fetch_channel_logo():
    try:
        # Fetch channel details
        url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet&id={CHANNEL_ID}&key={API_KEY}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # Check if the data contains the expected fields
        if 'items' in data and len(data['items']) > 0:
            channel = data['items'][0]
            # Fetch the high-resolution logo URL from the thumbnails
            logo_url = channel['snippet']['thumbnails']['high']['url']
            return logo_url
        else:
            print("Channel details not found in the API response.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching channel details: {e}")
        return None


def download_logo(logo_url, save_path):
    try:
        response = requests.get(logo_url)
        response.raise_for_status()  # Check for HTTP errors
        with open(save_path, 'wb') as file:
            file.write(response.content)
        print(f"Downloaded logo and saved to {save_path}.")
    except requests.exceptions.RequestException as e:
        print(f"Failed to download logo: {e}")

# Main flow
def main_flow():
    trials = 0
    max_trials = 5

    # Fetch and download the channel logo
    logo_path = os.path.join(SCRIPT_DIR, 'channel_logo.png')
    if not os.path.exists(logo_path):
        logo_url = fetch_channel_logo()
        if logo_url:
            download_logo(logo_url, logo_path)
        else:
            print("Failed to fetch channel logo.")
            return

    while trials < max_trials:
        video_urls = fetch_random_video()
        if video_urls:
            video_url = video_urls[0]  # Pick the first video URL
            yt = YouTube(video_url)
            video_id = yt.video_id  # Extract video ID from URL
            video_title = yt.title  # Extract video title
            logging.info(f"Selected video for processing: {video_url} (ID: {video_id}, Title: {video_title})")
            
            # Download the video
            download_path = download_and_merge(video_id, video_url)
            
            # Check if download was successful before proceeding
            if download_path and os.path.exists(download_path):
                trim_and_resize_video(download_path, video_title+video_id, watermark_path=logo_path)
                break  # Exit loop if successful
            else:
                logging.error(f"Failed to download video {video_id}, trying next video.")
        else:
            logging.warning("No suitable videos found, retrying...")
        
        trials += 1
        if trials >= max_trials:
            logging.critical("Exceeded maximum number of trials. Exiting.")

# Run the main flow
if __name__ == "__main__":
    main_flow()

    # test local file
    # trim_and_resize_video(os.path.join(SCRIPT_DIR, r"YtDownloads/httpswww.youtube.comwatchv=JK-B-CT34EU.mp4"), "24 Modern Ui Python, PySide6, Pyqt6 Desktop GUI appJK-B-CT34EU", os.path.join(SCRIPT_DIR, r"Assets/outro.mp4"), watermark_path=logo_path)


