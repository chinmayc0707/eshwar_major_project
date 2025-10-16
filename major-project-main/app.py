from flask import Flask, render_template, request, jsonify, send_from_directory, url_for
from dotenv import load_dotenv
import os
import threading
import re
from queue import Queue
from transcribe import process_audio_transcription
from summary import  summarize_openrouter
from translate import create_translations
from youtube import download_youtube_video, validate_youtube_url  # Import YouTube functions

# Load environment variables from .env file
load_dotenv()

# ========== SUPPORTED FILE FORMATS ==========
# Comprehensive list of supported audio and video formats for uploads
SUPPORTED_EXTENSIONS = {
    # Video formats
    'mp4', 'webm', 'mov', 'avi', 'mkv', 'flv', 'wmv', 'm4v', '3gp', 'ogv',
    'asf', 'ts', 'rm', 'rmvb', 'mpg',
    # Audio formats  
    'mp3', 'wav', 'ogg', 'aac', 'flac', 'm4a', 'wma', 'opus', 'mka'
}

# ========== MIME TYPE MAPPING ==========
# Proper Content-Type headers for each file format to ensure correct browser handling
MIME_TYPES = {
    # Video MIME types
    '.mp4': 'video/mp4',
    '.webm': 'video/webm',
    '.mov': 'video/quicktime', 
    '.avi': 'video/x-msvideo',
    '.mkv': 'video/x-matroska',
    '.flv': 'video/x-flv',
    '.wmv': 'video/x-ms-wmv',
    '.m4v': 'video/x-m4v',
    '.3gp': 'video/3gpp',
    '.ogv': 'video/ogg',
    '.asf': 'video/x-ms-asf',
    '.ts': 'video/mp2t',
    '.rm': 'application/vnd.rn-realmedia',
    '.rmvb': 'application/vnd.rn-realmedia-vbr',
    '.mpg': 'video/mpeg',
    # Audio MIME types
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.ogg': 'audio/ogg',
    '.aac': 'audio/aac',
    '.flac': 'audio/flac',
    '.m4a': 'audio/mp4',
    '.wma': 'audio/x-ms-wma',
    '.opus': 'audio/opus',
    '.mka': 'audio/x-matroska'
}

def create_app():
    """
    Create and configure the Flask application
    """
    app = Flask(__name__, static_folder='static', template_folder='templates')
    
    # ========== FLASK CONFIGURATION ==========
    app.config["UPLOAD_FOLDER"] = "uploads"  # Directory for storing uploaded/downloaded files
    app.config["TEMPLATES_AUTO_RELOAD"] = True  # Auto-reload templates during development
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for CSS changes
    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2GB max file size for large videos
    
    # Ensure upload directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    
    # ========== GLOBAL PROCESSING STATUS TRACKER ==========
    # Tracks the progress of transcription, summarization, and translation
    processing_status = {
        'transcription': {'complete': False, 'result': None, 'progress': None, 'error': False},
        'summary': {'complete': False, 'result': None, 'progress': None, 'error': False},
        'translation': {'complete': False, 'result': None, 'progress': None, 'error': False},
        'final': {'success': False, 'error': None, 'filename': '', 'duration': '--:--', 'input_type': ''}
    }

    def reset_status():
        """
        Reset processing status for new request
        Called at the beginning of each new processing request
        """
        for key in processing_status:
            if key != 'final':
                processing_status[key] = {'complete': False, 'result': None, 'progress': None, 'error': False}
        processing_status['final'] = {'success': False, 'error': None, 'filename': '', 'duration': '--:--', 'input_type': ''}

    def validate_file_format(filename):
        """
        Validate if uploaded file format is supported
        
        Args:
            filename (str): Name of the uploaded file
            
        Returns:
            tuple: (is_valid: bool, message: str)
        """
        if not filename:
            return False, "No filename provided"
        
        if '.' not in filename:
            return False, "File has no extension"
        
        file_ext = filename.rsplit('.', 1)[1].lower()
        if file_ext not in SUPPORTED_EXTENSIONS:
            return False, f"Unsupported format: .{file_ext}"
        
        return True, "Valid format"

    def get_media_type_from_extension(filename):
        """
        Determine if file is video or audio based on extension
        
        Args:
            filename (str): Name of the file
            
        Returns:
            str: 'video', 'audio', or 'unknown'
        """
        if not filename:
            return 'video'  # Default for YouTube downloads
        
        file_ext = os.path.splitext(filename)[1].lower()
        
        # Define video extensions
        video_exts = {'.mp4', '.webm', '.mov', '.avi', '.mkv', '.flv', '.wmv', 
                     '.m4v', '.3gp', '.ogv', '.asf', '.ts', '.rm', '.rmvb', '.mpg'}
        
        if file_ext in video_exts:
            return 'video'
        else:
            return 'audio'

    # ========== ROUTE: HOME PAGE ==========
    @app.route('/')
    def home():
        """
        Serve the main home page with input options
        """
        return render_template('home-page.html')

    # ========== ROUTE: FILE SERVING ==========
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        """
        Serve uploaded/downloaded files with proper MIME types and streaming support
        
        This route handles:
        - Correct Content-Type headers for media playback
        - Range request support for video streaming
        - Caching headers for performance
        
        Args:
            filename (str): Name of the file to serve
        """
        try:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Check if file exists
            if not os.path.exists(file_path):
                print(f"❌ File not found: {file_path}")
                return jsonify({'error': 'File not found'}), 404
            
            # Get file extension and determine MIME type
            file_ext = os.path.splitext(filename)[1].lower()
            mime_type = MIME_TYPES.get(file_ext, 'application/octet-stream')
            
            print(f"📁 Serving file: {filename} (Type: {mime_type})")
            
            # Create response with proper headers for media streaming
            response = send_from_directory(app.config['UPLOAD_FOLDER'], filename)
            response.headers['Content-Type'] = mime_type
            response.headers['Accept-Ranges'] = 'bytes'  # Enable range requests for video streaming
            response.headers['Cache-Control'] = 'public, max-age=3600'  # Cache for 1 hour
            
            return response
            
        except Exception as e:
            print(f"❌ Error serving file {filename}: {e}")
            return jsonify({'error': 'Error serving file'}), 500

    # ========== ROUTE: PROCESS MEDIA ==========
    @app.route('/process', methods=['POST'])
    def process():
        """
        Main processing route that handles:
        1. File uploads
        2. YouTube URL downloads  
        3. Text input processing
        
        Returns JSON response indicating success or error
        """
        reset_status()  # Clear previous processing status
        input_type = request.form.get('inputType')
        
        try:
            # ========== HANDLE FILE UPLOADS ==========
            if input_type == 'file':
                uploaded_file = request.files.get('file')
                if not uploaded_file or uploaded_file.filename == '':
                    return jsonify({'error': 'No file provided'}), 400
                
                # Validate file format
                is_valid, message = validate_file_format(uploaded_file.filename)
                if not is_valid:
                    return jsonify({'error': message}), 400
                
                # Sanitize filename for safe filesystem usage
                from youtube import sanitize_filename
                safe_filename = sanitize_filename(uploaded_file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
                
                # Save the uploaded file
                uploaded_file.save(file_path)
                print(f"✅ File saved: {file_path}")
                
                media_source = file_path
                
            # ========== HANDLE YOUTUBE URLS ==========
            elif input_type == 'youtube':
                youtube_url = request.form.get('youtubeUrl', '').strip()
                if not youtube_url:
                    return jsonify({'error': 'No YouTube URL provided'}), 400
                
                # Validate YouTube URL format (strict validation - only full URLs)
                if not validate_youtube_url(youtube_url):
                    return jsonify({'error': 'Invalid YouTube URL format. Only https://www.youtube.com/watch?v=VIDEO_ID is supported.'}), 400
                
                print(f"🎥 Processing YouTube URL: {youtube_url}")
                
                # Download MP4 video using separate youtube.py module
                # This treats YouTube downloads like regular file uploads
                try:
                    media_source = download_youtube_video(youtube_url, app.config['UPLOAD_FOLDER'])
                    print(f"✅ Downloaded MP4 video: {media_source}")
                    
                    # IMPORTANT: Change input_type to 'file' to treat YouTube download as regular uploaded file
                    # This ensures the video is displayed in the result page with full controls
                    input_type = 'file'
                    
                except Exception as e:
                    return jsonify({'error': f"YouTube download failed: {str(e)}"}), 400
                
            # ========== HANDLE TEXT INPUT ==========
            elif input_type == 'text':
                text_input = request.form.get('textInput', '').strip()
                if not text_input:
                    return jsonify({'error': 'No text provided'}), 400
                
                if len(text_input) < 10:
                    return jsonify({'error': 'Text too short. Please provide at least 10 characters.'}), 400
                
                def process_text_input():
                    """
                    Process text input in background thread
                    - Skip transcription (use input text directly)
                    - Create summary
                    - Create translations
                    """
                    import time
                    try:
                        print("📝 Processing text input...")
                        
                        # Set transcription as the input text (skip actual transcription)
                        processing_status['transcription'] = {
                            'complete': True, 
                            'result': text_input, 
                            'progress': None, 
                            'error': False
                        }
                        
                        # Create summary
                        processing_status['summary'] = {
                            'complete': False, 
                            'result': None, 
                            'progress': 'Creating summary...', 
                            'error': False
                        }
                        time.sleep(2)  # Simulate processing time
                        
                        english_sum = summarize_openrouter(text_input)
                        processing_status['summary'] = {
                            'complete': True, 
                            'result': english_sum, 
                            'progress': 'Done', 
                            'error': False
                        }
                        
                        # Create translations
                        processing_status['translation'] = {
                            'complete': False, 
                            'result': None, 
                            'progress': 'Creating translations...', 
                            'error': False
                        }
                        time.sleep(3)  # Simulate processing time
                        
                        translations = create_translations(english_sum)
                        processing_status['translation'] = {
                            'complete': True, 
                            'result': translations, 
                            'progress': 'Done', 
                            'error': False
                        }
                        
                        # Mark processing as complete
                        processing_status['final'] = {
                            'success': True, 
                            'error': None, 
                            'filename': '', 
                            'duration': '--:--',
                            'input_type': 'text'
                        }
                        
                        print("✅ Text processing completed successfully")
                        
                    except Exception as e:
                        print(f"❌ Text processing error: {e}")
                        # Mark all steps as failed
                        processing_status['transcription'] = {
                            'complete': True, 
                            'result': f"ERROR: {str(e)}", 
                            'progress': None, 
                            'error': True
                        }
                        processing_status['summary'] = {
                            'complete': True, 
                            'result': None, 
                            'progress': None, 
                            'error': True
                        }
                        processing_status['translation'] = {
                            'complete': True, 
                            'result': None, 
                            'progress': None, 
                            'error': True
                        }
                        processing_status['final'] = {
                            'success': False, 
                            'error': str(e), 
                            'filename': '', 
                            'duration': '--:--',
                            'input_type': 'text'
                        }
                
                # Start text processing in background thread
                thread = threading.Thread(target=process_text_input, daemon=True)
                thread.start()
                return jsonify({'status': 'success'})
                
            else:
                return jsonify({'error': 'Invalid input type. Must be file, youtube, or text.'}), 400

            # ========== PROCESS AUDIO/VIDEO FILES ==========
            # This handles both uploaded files and YouTube downloads (now treated as files)
            def process_media_input():
                """
                Process audio/video files in background thread:
                1. Transcribe audio (works with both audio and video files)
                2. Create summary from transcription
                3. Create translations from summary
                """
                try:
                    print(f"🎵 Processing media file: {media_source}")
                    
                    # Step 1: Transcription
                    processing_status['transcription'] = {
                        'complete': False, 
                        'result': None, 
                        'progress': 'Transcribing media...', 
                        'error': False
                    }
                    
                    # AssemblyAI can extract audio from video files automatically
                    transcription_result = process_audio_transcription(media_source)
                    processing_status['transcription'] = {
                        'complete': True, 
                        'result': transcription_result['text'], 
                        'progress': 'Done', 
                        'error': False
                    }
                    
                    # Step 2: Summary
                    
                    processing_status['summary'] = {
                        'complete': False, 
                        'result': None, 
                        'progress': 'Creating summary...', 
                        'error': False
                    }

                    summary_result = summarize_openrouter(transcription_result['text'])
                    processing_status['summary'] = {
                        'complete': True, 
                        'result': summary_result, 
                        'progress': 'Done', 
                        'error': False
                    }
                    
                    # Step 3: Translation
                    processing_status['translation'] = {
                        'complete': False, 
                        'result': None, 
                        'progress': 'Creating translations...', 
                        'error': False
                    }
                    
                    translation_result = create_translations(summary_result)
                    processing_status['translation'] = {
                        'complete': True, 
                        'result': translation_result, 
                        'progress': 'Done', 
                        'error': False
                    }
                    
                    # Mark processing as complete
                    processing_status['final'] = {
                        'success': True, 
                        'error': None, 
                        'filename': os.path.basename(media_source), 
                        'duration': transcription_result.get('duration', '--:--'),
                        'input_type': 'file'  # YouTube downloads are now treated as files
                    }
                    
                    print("✅ Media processing completed successfully")
                    
                except Exception as e:
                    print(f"❌ Media processing error: {e}")
                    # Mark all steps as failed
                    processing_status['transcription'] = {
                        'complete': True, 
                        'result': f"ERROR: {str(e)}", 
                        'progress': None, 
                        'error': True
                    }
                    processing_status['summary'] = {
                        'complete': True, 
                        'result': None, 
                        'progress': None, 
                        'error': True
                    }
                    processing_status['translation'] = {
                        'complete': True, 
                        'result': None, 
                        'progress': None, 
                        'error': True
                    }
                    processing_status['final'] = {
                        'success': False, 
                        'error': str(e), 
                        'filename': os.path.basename(media_source) if 'media_source' in locals() else '', 
                        'duration': '--:--',
                        'input_type': input_type
                    }

            # Start media processing in background thread
            thread = threading.Thread(target=process_media_input, daemon=True)
            thread.start()
            return jsonify({'status': 'success'})

        except Exception as e:
            print(f"❌ Error in /process: {e}")
            return jsonify({'error': str(e)}), 500

    # ========== ROUTE: STATUS CHECKER ==========
    @app.route('/status/<step>')
    def get_status(step):
        """
        Get processing status for a specific step
        Used by frontend to check progress of transcription, summary, translation
        
        Args:
            step (str): One of 'transcription', 'summary', 'translation', 'final'
        """
        if step not in processing_status:
            return jsonify({'error': 'Invalid step'}), 400
            
        s = processing_status[step]
        return jsonify({
            'complete': s.get('complete', False),
            'result': s.get('result'),
            'progress': s.get('progress'),
            'error': s.get('error', False)
        })

    # ========== ROUTE: LOADING PAGES ==========
    @app.route('/loading/<page>')
    def loading(page):
        """
        Serve loading page HTML files from static folder
        Used during processing to show progress
        """
        return send_from_directory('static', f'{page}.html')

    # ========== ROUTE: RESULT PAGE ==========
    @app.route('/result')
    def result():
        """
        Display results page with:
        - Media player (for uploaded files and YouTube videos)  
        - Transcription text
        - Summary in English
        - Translations in Kannada and Kanglish
        
        YouTube downloads are now treated exactly like uploaded files
        """
        try:
            # Get processing results
            filename = request.args.get('filename') or processing_status.get('final', {}).get('filename', '')
            duration = request.args.get('duration') or processing_status.get('final', {}).get('duration', '--:--')
            input_type = request.args.get('type') or processing_status.get('final', {}).get('input_type', 'file')
            transcription = processing_status['transcription'].get('result', '')

            print(f"🎯 Result page - Filename: {filename}, Type: {input_type}")

            # Determine media display based on input type
            if input_type == 'text':
                # Text input - no media to display
                media_type = 'text'
                media_src = None
                media_name = 'Text input'
            else:
                # File uploads and YouTube downloads - show media player
                if filename:
                    media_type = get_media_type_from_extension(filename)
                    media_src = url_for('uploaded_file', filename=filename)
                    media_name = filename
                    print(f"📁 Media file: {media_name} -> {media_src}")
                    
                    # Debug: Verify file exists
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    if os.path.exists(file_path):
                        print(f"✅ File exists: {file_path}")
                        print(f"🔍 File size: {os.path.getsize(file_path)} bytes")
                    else:
                        print(f"❌ File missing: {file_path}")
                else:
                    media_type = 'video'  # Default for unknown files
                    media_src = None
                    media_name = 'Unknown file'

            # Get processing results
            summary_result = processing_status['summary'].get('result', 'No summary available.')
            translation_result = processing_status['translation'].get('result', {})
            
            # Prepare data for template
            data = {
                "mediaType": media_type,  # 'video', 'audio', 'text', or None
                "mediaName": media_name,  # Display name
                "mediaSrc": media_src,    # URL for media player
                "transcription": transcription,  # Full transcription text
                "duration": duration,     # Media duration
                "summaries": {
                    "english": summary_result,
                    "kannada": translation_result.get('kannada', 'ಕನ್ನಡ ಅನುವಾದ ಲಭ್ಯವಿಲ್ಲ.'),
                    "kanglish": translation_result.get('kanglish', 'Kanglish translation not available.')
                }
            }
            
            print(f"✅ Rendering result page with data: {data}")
            return render_template('result-page.html', data=data)
            
        except Exception as e:
            print(f"❌ Error in /result: {e}")
            # Return error page with basic structure
            return render_template('result-page.html', data={
                "mediaType": "error",
                "mediaName": "Error",
                "mediaSrc": None,
                "transcription": f"Error loading results: {str(e)}",
                "duration": "--:--",
                "summaries": {
                    "english": "Error loading summary",
                    "kannada": "ದೋಷ ಸಂಭವಿಸಿದೆ",
                    "kanglish": "Error aaithu"
                }
            })

    # ========== ERROR HANDLERS ==========
    @app.errorhandler(413)
    def too_large(e):
        """Handle file too large errors"""
        return jsonify({'error': 'File too large. Maximum size is 2GB.'}), 413

    @app.errorhandler(500)
    def internal_error(e):
        """Handle internal server errors"""
        return jsonify({'error': 'Internal server error occurred.'}), 500

    return app

# ========== APPLICATION STARTUP ==========
if __name__ == '__main__':
    app = create_app()
    print("🚀 Starting Kanglish Summarizer server...")
    print("📡 Server running on http://127.0.0.1:5000")
    print("📁 Upload folder:", os.path.abspath("uploads"))
    print("🎥 YouTube downloads: MP4 video format (treated as uploaded files)")
    print("🎵 Supported YouTube format: https://www.youtube.com/watch?v=VIDEO_ID ONLY")
    print("📋 Supported features:")
    print("   - File uploads (audio/video)")
    print("   - YouTube video downloads") 
    print("   - Direct text input")
    print("   - Real-time transcription")
    print("   - AI summarization")
    print("   - Kannada & Kanglish translations")
    app.run(debug=True, port=5000, use_reloader=False)
