import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_KEY", "sk-4825511f7c2e48e19bba8ad6a150d9bf")

def create_translations(text):
    """
    Create translations for Kannada and Kanglish
    
    Args:
        text (str): English text to translate
        
    Returns:
        dict: Contains 'kannada' and 'kanglish' translations
    """
    try:
        if not text or len(text.strip()) == 0:
            return {
                'kannada': 'ಅನುವಾದಿಸಲು ಯಾವುದೇ ವಿಷಯ ಲಭ್ಯವಿಲ್ಲ.',
                'kanglish': 'No content available for translation.'
            }
        
        # Try AI-powered translations
        try:
            kannada_translation = get_kannada_translation(text)
            kanglish_translation = get_kanglish_translation(text)
            
            return {
                'kannada': kannada_translation,
                'kanglish': kanglish_translation
            }
            
        except Exception as e:
            print(f"AI translation failed, using fallback: {e}")
            return get_fallback_translations(text)
        
    except Exception as e:
        print(f"Translation error: {e}")
        return {
            'kannada': 'ಅನುವಾದ ದೋಷ ಸಂಭವಿಸಿದೆ.',
            'kanglish': 'Translation error occurred.'
        }

def get_kannada_translation(text):
    """
    Get Kannada translation using AI
    
    Args:
        text (str): English text to translate
        
    Returns:
        str: Kannada translation
    """
    try:
        prompt = f"""Translate the following English text to Kannada. Provide only the translation without any explanations:

        English: {text[:1000]}
        
        Kannada:"""
        
        response = get_deepseek_response(prompt)
        
        # Clean up the response
        translation = response.strip()
        if translation.lower().startswith('kannada:'):
            translation = translation[8:].strip()
        
        return translation
        
    except Exception as e:
        print(f"Kannada translation error: {e}")
        raise

def get_kanglish_translation(text):
    """
    Get Kanglish (mixed Kannada-English) translation
    
    Args:
        text (str): English text to translate
        
    Returns:
        str: Kanglish translation
    """
    try:
        prompt = f"""Convert the following English text to Kanglish (mixed Kannada-English as commonly spoken in Karnataka). 
        Use English words written in Kannada script where appropriate and mix both languages naturally:

        English: {text[:1000]}
        
        Kanglish:"""
        
        response = get_deepseek_response(prompt)
        
        # Clean up the response
        translation = response.strip()
        if translation.lower().startswith('kanglish:'):
            translation = translation[9:].strip()
        
        return translation
        
    except Exception as e:
        print(f"Kanglish translation error: {e}")
        raise

def get_deepseek_response(prompt):
    """
    Get response from Deepseek API
    
    Args:
        prompt (str): Prompt for translation
        
    Returns:
        str: API response
    """
    try:
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
        }
        
        data = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
            "temperature": 0.3
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=45)
        response.raise_for_status()
        
        result = response.json()
        return result['choices'][0]['message']['content']
        
    except requests.Timeout:
        print("Translation API timeout")
        raise Exception("Translation service timeout")
    except requests.RequestException as e:
        print(f"Translation API error: {e}")
        raise Exception("Translation service error")
    except Exception as e:
        print(f"Unexpected translation error: {e}")
        raise

def get_fallback_translations(text):
    """
    Provide fallback translations when AI service fails
    
    Args:
        text (str): English text
        
    Returns:
        dict: Fallback translations
    """
    try:
        # Simple fallback messages
        kannada_fallback = f"ಸಾರಾಂಶ (ಪರೀಕ್ಷಾ ಆವೃತ್ತಿ): ಈ ವಿಷಯದ ಮುಖ್ಯ ಅಂಶಗಳನ್ನು ಶೀಘ್ರದಲ್ಲೇ ಸ್ವಯಂ ಅನುವಾದಿಸಲಾಗುತ್ತದೆ. ಮೂಲ ಪಠ್ಯ: {text[:100]}..."
        
        kanglish_fallback = f"Summary (test version): Main points inda auto-translation soon ready aagutaade. Original text: {text[:100]}..."
        
        return {
            'kannada': kannada_fallback,
            'kanglish': kanglish_fallback
        }
        
    except Exception:
        return {
            'kannada': 'ಅನುವಾದ ಸೇವೆ ಲಭ್ಯವಿಲ್ಲ.',
            'kanglish': 'Translation service not available.'
        }

def validate_translation(translation, source_text):
    """
    Basic validation of translation quality
    
    Args:
        translation (str): Translated text
        source_text (str): Source text
        
    Returns:
        dict: Validation results
    """
    try:
        if not translation or not source_text:
            return {'valid': False, 'reason': 'Empty content'}
        
        # Check if translation is reasonable length
        source_length = len(source_text)
        translation_length = len(translation)
        length_ratio = translation_length / source_length if source_length > 0 else 0
        
        # Translation should be within reasonable bounds (0.5x to 3x original length)
        if length_ratio < 0.5 or length_ratio > 3:
            return {'valid': False, 'reason': 'Unusual length ratio'}
        
        # Check if translation contains actual content
        if len(translation.strip()) < 5:
            return {'valid': False, 'reason': 'Translation too short'}
        
        return {
            'valid': True,
            'length_ratio': length_ratio,
            'translation_length': translation_length,
            'source_length': source_length
        }
        
    except Exception:
        return {'valid': False, 'reason': 'Validation error'}

def get_supported_languages():
    """
    Get list of supported languages for translation
    
    Returns:
        list: List of supported language codes and names
    """
    return [
        {'code': 'kn', 'name': 'Kannada', 'native_name': 'ಕನ್ನಡ'},
        {'code': 'en-kn', 'name': 'Kanglish', 'native_name': 'Kanglish (ಕಂಗ್ಲಿಷ್)'},
        {'code': 'en', 'name': 'English', 'native_name': 'English'}
    ]
