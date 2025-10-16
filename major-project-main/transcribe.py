import assemblyai as aai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up AssemblyAI API key
aai.settings.api_key = os.getenv("ASSEMBLYAI_KEY", "e8770891918442e79c5ee70a6440ce62")

def process_audio_transcription(audio_source):
    """
    Transcribe audio file and return transcription with metadata
    
    Args:
        audio_source (str): Path to audio file
        
    Returns:
        dict: Contains 'text' and 'duration' keys
    """
    try:
        print(f"🎯 Starting transcription for: {audio_source}")
        
        # Configure transcription settings
        config = aai.TranscriptionConfig(
            speech_model=aai.SpeechModel.best,
            language_code="en"  # Can be modified to support other languages
        )
        
        # Create transcriber and transcribe
        transcriber = aai.Transcriber(config=config)
        transcript = transcriber.transcribe(audio_source)
        
        if transcript.status == "error":
            raise Exception(f"Transcription failed: {transcript.error}")
        
        print("✅ Transcription completed successfully")
        print(f"📝 Text length: {len(transcript.text)} characters")
        
        return {
            'text': transcript.text,
            'duration': getattr(transcript, 'duration', '--:--'),
            'status': 'success'
        }
        
    except Exception as e:
        print(f"❌ Transcription error: {str(e)}")
        raise Exception(f"Transcription failed: {str(e)}")

def validate_audio_file(file_path):
    """
    Validate if the audio file exists and is accessible
    
    Args:
        file_path (str): Path to audio file
        
    Returns:
        bool: True if file is valid, False otherwise
    """
    try:
        if not os.path.exists(file_path):
            return False
            
        # Check file size (should not be empty)
        if os.path.getsize(file_path) == 0:
            return False
            
        # Check file extension
        valid_extensions = ['.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.wma']
        file_extension = os.path.splitext(file_path)[1].lower()
        
        return file_extension in valid_extensions
        
    except Exception:
        return False

def get_audio_info(file_path):
    """
    Get basic information about the audio file
    
    Args:
        file_path (str): Path to audio file
        
    Returns:
        dict: Contains file information
    """
    try:
        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)
        file_extension = os.path.splitext(file_path)[1]
        
        return {
            'filename': file_name,
            'size_bytes': file_size,
            'size_mb': round(file_size / (1024 * 1024), 2),
            'extension': file_extension,
            'path': file_path
        }
        
    except Exception as e:
        return {'error': f"Could not get file info: {str(e)}"}
