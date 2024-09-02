import os
import re
import logging
from googleapiclient.discovery import build
from pytubefix import YouTube
from dotenv import load_dotenv
import requests
import subprocess
import textwrap
from random import shuffle

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
    """Remove all non-alphanumeric characters from filenames."""
    return re.sub(r'\W+', '', filename)
    
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

        # Check the duration of the video
        duration = yt.length  # Duration in seconds
        if duration < 120:  # 120 seconds = 2 minutes
            logging.info(f"Video '{title}' is shorter than 2 minutes. Skipping download.")
            return
        
        # Download the highest resolution video stream
        video_stream = yt.streams.filter(adaptive=True, file_extension='mp4', only_video=True).order_by('resolution').desc().first()
        audio_stream = yt.streams.filter(adaptive=True, file_extension='mp4', only_audio=True).first()
        
        if not video_stream or not audio_stream:
            logging.error(f"Could not find suitable video or audio streams for video {video_id}.")
            return None
        
        video_path = os.path.join(YT_DOWNLOADS_DIR, f"{sanitize_filename(title)}_video.mp4")
        audio_path = os.path.join(YT_DOWNLOADS_DIR, f"{sanitize_filename(title)}_audio.mp4")
        
        if os.path.exists(video_path):
            return video_path, audio_path, True
        
        # return
        
        video_stream.download(output_path=YT_DOWNLOADS_DIR, filename=f"{sanitize_filename(title)}_video.mp4")
        audio_stream.download(output_path=YT_DOWNLOADS_DIR, filename=f"{sanitize_filename(title)}_audio.mp4")
        
        logging.info(f"Downloaded video and audio for video {video_id}.")
        
        return video_path, audio_path, False
    except Exception as e:
        logging.error(f"Error downloading video {video_id}: {e}")
        return None
    
def merge_video_audio(video_path, audio_path, output_path):
    try:
        command = [
            'ffmpeg', '-y', 
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
        video_path, audio_path, local = paths
        output_path = os.path.join(YT_DOWNLOADS_DIR, f"{sanitize_filename(title)}.mp4")
        if not local:
            merge_video_audio(video_path, audio_path, output_path)
        return output_path
    return None

def break_text(text, max_lines=3, line_width=40, top_padding=1, bottom_padding=1):
    """
    Break text into multiple lines with a maximum number of lines, add ellipsis if the text exceeds,
    and add space at the top and bottom.
    """
    # Wrap the text
    wrapped_text = textwrap.wrap(text, width=line_width)
    
    # If the text exceeds the maximum lines, truncate and add an ellipsis
    if len(wrapped_text) > max_lines:
        wrapped_text = wrapped_text[:max_lines]  # Keep only the first `max_lines` lines
        wrapped_text[-1] += '...'  # Add ellipsis to the last line

    # Add padding lines at the top and bottom
    padded_text = [''] * top_padding + wrapped_text + [''] * bottom_padding
    
    # Join the lines back into a single string
    return '\n'.join(padded_text)

def trim_and_resize_video(input_path, title, outro_path, duration=55, watermark_path=None, overwrite = False):
    try:
        logging.info(f"Starting video processing for: {title}")

        # Ensure directories exist
        output_dir = "output_videos"
        os.makedirs(output_dir, exist_ok=True)
        
        # Sanitize title for filenames
        sanitized_title = title.replace(' ', '_').replace('/', '_')

        # Step 1: Create a Blurry Background Video
        blurry_bg_path = os.path.join(output_dir, f"{sanitized_title}_blurry_bg_9_16.mp4")
        logging.debug(f"Creating blurry background video at: {blurry_bg_path}")

        # Create blurry background video
        cmd_trim_resize_blur = [
            'ffmpeg', '-y', '-i', input_path,
            '-vf', "scale=-1:1280,crop='min(720,iw)':'min(1280,ih)',boxblur=10:10,pad=720:1280:(ow-iw)/2:(oh-ih)/2",
            '-c:v', 'libx264', '-b:v', '1000k', '-preset', 'medium', '-an', '-t', str(duration), blurry_bg_path
        ]

        if not os.path.exists(blurry_bg_path):
            try:
                subprocess.run(cmd_trim_resize_blur, check=True)
                logging.info(f"Blurry background video saved to {blurry_bg_path}")
            except subprocess.CalledProcessError as e:
                logging.error(f"Failed to create blurry background video. Error: {e}")
                return  # Exit if this step fails

        # Helper function to get video dimensions
        def get_video_dimensions(video_path):
            cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'default=noprint_wrappers=1:nokey=1', video_path]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                width_height = result.stdout.strip().split('\n')
                if len(width_height) != 2:
                    raise ValueError("Unexpected output from ffprobe")
                width, height = map(int, width_height)
                return width, height
            except subprocess.CalledProcessError as e:
                logging.error(f"ffprobe failed with error: {e}")
                raise
            except ValueError as e:
                logging.error(f"Error parsing video dimensions: {e}")
                raise

        
        # Get dimensions of blurry background
        blurry_width, blurry_height = get_video_dimensions(blurry_bg_path)
        logging.debug(f"Blurry background dimensions: {blurry_width}x{blurry_height}")

        # Step 2: Trim and Resize Main Video
        trimmed_main_path = os.path.join(output_dir, f"{sanitized_title}_trimmed_main.mp4")
        logging.debug(f"Trimming and resizing main video at: {trimmed_main_path}")

        cmd_cut = [
            'ffmpeg', '-y', '-i', input_path,
            '-vf', f"scale='if(gt(a,{blurry_width}/{blurry_height}),floor({blurry_width}/2)*2,-2)':'if(gt(a,{blurry_width}/{blurry_height}),-2,floor({blurry_height}/2)*2)'",  # Ensure dimensions are divisible by 2
            '-c:v', 'libx264', '-b:v', '1000k', '-preset', 'ultrafast',
            '-t', str(duration),  # Specify duration with the -t option
            trimmed_main_path
        ]

        if not os.path.exists(trimmed_main_path):
            try:
                subprocess.run(cmd_cut, check=True)
                logging.info(f"Trimmed main video saved to {trimmed_main_path}")
            except subprocess.CalledProcessError as e:
                logging.error(f"Failed to trim main video. Error: {e}")
                return  # Exit if this step fails

        # Get dimensions of trimmed main video
        main_width, main_height = get_video_dimensions(trimmed_main_path)
        logging.debug(f"Trimmed main video dimensions: {main_width}x{main_height}")
        
        # Define the path to the custom font
        custom_font_path = os.path.join("Fonts", "Luciole-Regular.ttf")
        # Prepare text for overlay
        formatted_title = break_text(title, max_lines=3, line_width=20, top_padding=3, bottom_padding=3)

        # Step 3: Overlay Main Clip on Blurry Background and Add Text at the Top
        final_output_path = os.path.join(output_dir, f"{sanitized_title}_final.mp4")
        # cmd_combine = [
        #     'ffmpeg', '-y', '-i', blurry_bg_path,
        #     '-i', trimmed_main_path,
        #     '-filter_complex', f"[0:v][1:v]overlay=(W-w)/2:(H-h)/2,drawtext=text='{formatted_title}':fontfile={custom_font_path}:fontcolor=white:fontsize=50:box=1:boxcolor=black@0.6:boxborderw=10:x=(w-text_w)/2:y=10",
        #     '-c:v', 'libx264', '-b:v', '1000k', '-preset', 'medium', final_output_path
        # ]

        cmd_combine = [
            'ffmpeg', '-y', '-i', blurry_bg_path,
            '-i', trimmed_main_path,
            # '-i', watermark_path,  # Add watermark as an additional input
            '-filter_complex', (
                f"[0:v][1:v]overlay=(W-w)/2:(H-h)/2,"  # Overlay main video on background
                f"drawtext=text='{formatted_title}':fontfile={custom_font_path}:fontcolor=white:fontsize=50:box=1:boxcolor=black@0.6:boxborderw=10:x=(w-text_w)/2:y=10"  # Add text
                # f"[2:v]scale=50:50[wm];[0:v][wm]overlay=5:H-h-10"  # Add watermark
            ),
            '-c:v', 'libx264', '-b:v', '1000k', '-preset', 'medium', final_output_path
        ]

        if not os.path.exists(final_output_path):
            try:
                subprocess.run(cmd_combine, check=True)
                print(f"Final video with text created and saved to {final_output_path}")
            except subprocess.CalledProcessError as e:
                print(f"Final video combination failed. Error: {e}")
                return  # Exit function if this step fails

        # Step 4: Concatenate Final Video with Outro
        concat_file = os.path.join("concat_list.txt")
        with open(concat_file, 'w') as f:
            f.write(f"file '{final_output_path}'\n")
            f.write(f"file '{outro_path}'\n")

        concat_output_path = os.path.join("ShortifiedYtVideos", f"{sanitized_title}_with_outro.mp4")
        cmd_concat = [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_file,
            '-c', 'copy', concat_output_path
        ]

        if not os.path.exists(concat_output_path):
            try:
                subprocess.run(cmd_concat, check=True)
                print(f"Final video with outro created and saved to {concat_output_path}")
            except subprocess.CalledProcessError as e:
                print(f"Error while concatenating videos. Error: {e}")

        return True

    except Exception as e:
        logging.error(f"Error processing video {title}: {e}")
        return

def main():
    try:
        video_urls = fetch_random_video()
        if not video_urls:
            raise Exception("No videos to process.")

        for url in video_urls:
            video_id = url.split('=')[-1]
            title = YouTube(url).title
            output_path = download_and_merge(video_id, title)
            
            if not output_path:
                continue
            outro = os.path.join(SCRIPT_DIR, "Assets/outro.mp4")
            if (trim_and_resize_video(output_path, title, outro)):
                break

    except Exception as e:
        logging.error(f"Main execution error: {e}")

if __name__ == "__main__":
    main()
    # OFFLINE TEST
    # logo_path = os.path.join(SCRIPT_DIR, 'channel_logo.png')
    # trim_and_resize_video(r"C:\xampp\htdocs\Spinn-Code-PHP-Web\py\YtDownloads\httpswww.youtube.comwatchv=JK-B-CT34EU.mp4", "24 Modern Ui Python, PySide6, Pyqt6 Desktop GUI appJK-B-CT34EU", r"C:\xampp\htdocs\Spinn-Code-PHP-Web\py\Assets\Outro.mp4", watermark_path=logo_path)
