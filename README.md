# YouTube Video Shortifier

![GitHub repo size](https://img.shields.io/github/repo-size/KhamisiKibet/YouTube-Video-Shortifier)
![GitHub stars](https://img.shields.io/github/stars/KhamisiKibet/YouTube-Video-Shortifier?style=social)
![GitHub forks](https://img.shields.io/github/forks/KhamisiKib/YouTube-Video-Shortifier?style=social)
[![Twitter Follow](https://img.shields.io/twitter/follow/KhamisiKibet?style=social)](https://twitter.com/intent/follow?screen_name=KhamisiKibet)
[![YouTube Video Views](https://img.shields.io/youtube/views/JK-B-CT34EU?style=social)](https://youtu.be/JK-B-CT34EU)

## Overview

![Demo](/Screenshot%202024-09-02%20153150.png "Desktop Demo")

**YouTube Video Shortifier** is a Python-based tool designed to automate the process of downloading, trimming, resizing, and editing YouTube videos into short-form content best for `TikTok or YouTube shorts`. It includes features for adding text overlays, watermarks, and outros, making it ideal for content creators looking to repurpose long-form videos into engaging shorts.

## Features

- **Download Videos**: Fetch and download videos from YouTube using the YouTube Data API.
- **Trim and Resize**: Automatically trim videos to a specified duration and resize them to fit a vertical format.
- **Blurry Background**: Add a blurred background to fit the video within the target dimensions.
- **Text Overlays**: Add customizable text overlays with options for padding and rounded corners.
- **Watermarks**: Include a logo or watermark in the final video.
- **Outro Clips**: Concatenate an outro clip to the processed video.

## Requirements

- **Python 3.x**: The script is compatible with Python 3.
- **FFmpeg**: Required for video processing. Ensure FFmpeg is installed and available in your system's PATH.
- **Google API Key**: Needed to access the YouTube Data API.
- **Dependencies**: Install the required Python libraries using `pip`.

## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/KhamisiKibet/YouTube-Video-Shortifier.git
   cd YouTube-Video-Shortifier
   ```

2. **Install Dependencies**

   Create a virtual environment (optional but recommended):

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

   Install the required libraries:

   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up Environment Variables**

   Create a `.env` file in the root directory of the project with the following content:

   ```env
   YOUTUBE_API_KEY=your_youtube_api_key
   CHANNEL_ID_YOUTUBE=your_channel_id
   ```

   Replace `your_youtube_api_key` and `your_channel_id` with your actual API key and YouTube channel ID.

4. **Install FFmpeg**

   Ensure FFmpeg is installed on your system. You can download it from [FFmpeg's official website](https://ffmpeg.org/download.html) and follow the installation instructions.

## Usage

1. **Run the Script**

   Execute the main script to start processing videos:

   ```bash
   python ShortifyYtVideo_Moviepy.py
   ```

   - Using the Pure FFmpeg Script:

        `Moviepy` might be too slow, if you prefer using `FFmpeg` directly without MoviePy, use the ShortifyYtVideo_Ffmpeg.py script. It offers similar functionality but relies solely on FFmpeg for video processing.

        To run the FFmpeg script:
        ```bash
        python ShortifyYtVideo_Ffmpeg.py
        ```

   The script will:
   - Fetch a random video from the specified YouTube channel.
   - Download the video and its audio.
   - Trim and resize the video.
   - Add a blurry background, text overlays, and an optional watermark.
   - Concatenate an outro clip.
   - Save the final video in the `ShortifiedYtVideos` directory.

2. **Customize the Script**

   - **Text Overlay**: Modify the `break_text` function to adjust text wrapping settings.
   - **Background Blur**: Change the `blur` function parameters to adjust the blur effect.
   - **Watermark**: Update the `logo_path` variable in `main_flow()` to point to your logo file.

## Contributing

Contributions are welcome! Please fork the repository, make your changes, and submit a pull request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

For questions or feedback, you can reach out to [me](mailto:info@spinncode.com) or open an issue in the GitHub repository.

---

## ☕️ Support My Work

If you enjoy my projects and find them helpful, consider buying me a coffee. Your support helps me keep going and create more awesome content! 😊

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.patreon.com/spinntv)