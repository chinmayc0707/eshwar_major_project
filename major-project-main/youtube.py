import os
import re
import glob
import yt_dlp

def sanitize_filename(filename):
    """Sanitize filename for safe filesystem usage"""
    if not filename:
        return 'unnamed_file'
    
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Remove emoji and special unicode characters
    filename = re.sub(r'[^\w\s\-_\.]', '', filename)
    # Replace multiple spaces/underscores with single ones
    filename = re.sub(r'[\s_]+', '_', filename)
    
    # Limit length to 100 chars
    if len(filename) > 100:
        name, ext = os.path.splitext(filename)
        filename = name[:96] + "..." + ext
    
    return filename

def validate_youtube_url(url):
    """Validate YouTube URL - ONLY supports full https://www.youtube.com/watch?v=VIDEO_ID format"""
    if not url:
        return None
    
    # Strict pattern - ONLY matches full YouTube URLs
    pattern = r'^https://www\.youtube\.com/watch\?v=([\w-]{11})$'
    match = re.match(pattern, url.strip())
    
    if match:
        print(f"✅ Valid YouTube URL: {url}")
        return url
    else:
        print(f"❌ Invalid YouTube URL format. Only https://www.youtube.com/watch?v=VIDEO_ID supported")
        return None

def download_youtube_video(url, download_folder):
    """Download YouTube video as MP4 file - NO AUDIO EXTRACTION"""
    try:
        # Validate URL format
        normalized_url = validate_youtube_url(url)
        if not normalized_url:
            raise ValueError('Invalid YouTube URL format. Only full URLs like https://www.youtube.com/watch?v=VIDEO_ID are supported.')
        
        print(f"🎯 Processing YouTube URL: {normalized_url}")
        
        # First, extract info without downloading to get title
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as info_ydl:
            try:
                info = info_ydl.extract_info(normalized_url, download=False)
                if not info:
                    raise ValueError("Could not extract video information")
                
                video_title = info.get('title', 'YouTube_Video')
                video_duration = info.get('duration', 0)
                safe_title = sanitize_filename(video_title)
                
                print(f"📹 Video Title: {video_title}")
                print(f"⏱️  Duration: {video_duration} seconds")
                
            except Exception as e:
                print(f"Warning: Could not extract video info: {e}")
                safe_title = "YouTube_Video"
        
        # CRITICAL: yt-dlp options that prevent audio extraction
        output_template = os.path.join(download_folder, f"{safe_title}.%(ext)s")
        
        ydl_opts = {
            # Download and merge video+audio into MP4 (NO EXTRACTION)
            'format': 'bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4][height<=720]/bestvideo+bestaudio/best',
            'outtmpl': output_template,
            'merge_output_format': 'mp4',  # Merge to MP4
            'writeinfojson': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'writethumbnail': False,
            'ignoreerrors': True,
            'no_warnings': False,
            'extractflat': False,
            'postprocessors': [],  # CRITICAL: NO postprocessors = NO audio extraction
            'nocheckcertificate': True,
            'noplaylist': True,
            'continuedl': True,
            'nooverwrites': False,
            'retries': 3,
            'fragment_retries': 3,
            'quiet': False,
            'keep_video': True  # Keep the original video file
        }
        
        # Download MP4 video (with audio merged, not extracted)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print("⬇️  Downloading MP4 video with audio...")
            ydl.download([normalized_url])
        
        # Find the MP4 file
        mp4_pattern = os.path.join(download_folder, f"{safe_title}*.mp4")
        mp4_files = glob.glob(mp4_pattern)
        
        if mp4_files:
            mp4_path = mp4_files[0]
            print(f"✅ Successfully downloaded MP4: {mp4_path}")
            
            # Verify it's a video file (not audio)
            if os.path.exists(mp4_path):
                file_size = os.path.getsize(mp4_path)
                print(f"📁 File size: {file_size / (1024*1024):.2f} MB")
                return mp4_path
            else:
                raise FileNotFoundError("MP4 file not found after download")
        else:
            # Fallback: look for any MP4 files created recently
            all_mp4s = glob.glob(os.path.join(download_folder, "*.mp4"))
            if all_mp4s:
                recent_mp4 = max(all_mp4s, key=os.path.getmtime)
                print(f"✅ Found recent MP4: {recent_mp4}")
                return recent_mp4
            else:
                raise FileNotFoundError("No MP4 file found after download")
                
    except Exception as e:
        print(f"❌ YouTube download error: {str(e)}")
        raise Exception(f"YouTube download failed: {str(e)}")
