import os
def get_secrets(core_api_key = None, my_email = None):
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        api_key_path = os.path.join(current_dir, "..", "..", "secrets.txt")
        
        if not os.path.exists(api_key_path):
            raise FileNotFoundError(f"API key file not found at: {api_key_path}")
        
        secrets = {}
        with open(api_key_path, "r") as apikey_file:
            for line in apikey_file:
                if '=' in line:
                    key, value = line.split('=', 1)
                    secrets[key.strip()] = value.strip().strip("'")

        core_api = secrets.get('CORE_API')
        email = secrets.get('EMAIL')
        if not core_api and not email:
            raise ValueError("One required API key or email is missing")
        
        if my_email == "email":
            return email
        if core_api_key == "core_api":
            return core_api

    except FileNotFoundError as e:
        print(f"Error: {str(e)}")
        print("Please create an secrets.txt file in the backend directory with your API keys and email.")
        raise
    except Exception as e:
        raise Exception(f"Error reading secrets: {e}")