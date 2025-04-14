import os

def get_google_genai_api_key():
    """
    Get the Google GenAI API key from secrets.txt
    Returns:
        str: The API key or None if not found
    """
    try:
        # Get the path to secrets.txt (one level up from utils directory)
        secrets_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "secrets.txt")
        if not os.path.exists(secrets_path):
            print("Warning: secrets.txt not found")
            return None
            
        with open(secrets_path, 'r') as f:
            for line in f:
                if line.startswith('GOOGLE_GENAI_API_KEY='):
                    return line.strip().split('=')[1]
                    
        print("Warning: GOOGLE_GENAI_API_KEY not found in secrets.txt")
        return None
        
    except Exception as e:
        print(f"Error reading API key: {e}")
        return None 