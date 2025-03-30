import requests
import os
import csv

def get_api_key():
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        api_key_path = os.path.join(current_dir, "..", "apikey.txt")
        
        if not os.path.exists(api_key_path):
            raise FileNotFoundError(f"API key file not found at: {api_key_path}")
            
        with open(api_key_path, "r") as apikey_file:
            api_key = apikey_file.readlines()[0].strip()
            if not api_key:
                raise ValueError("API key is empty")
            return api_key
    except FileNotFoundError as e:
        print(f"Error: {str(e)}")
        print("Please create an apikey.txt file in the backend directory with your CORE API key")
        raise
    except Exception as e:
        raise Exception(f"Error reading API key: {e}")

API_KEY = get_api_key()
API_ENDPOINT = "https://api.core.ac.uk/v3/"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

def search_works(query, limit=100, max_results=100):
    results = []
    url = f"{API_ENDPOINT}search/works?q={query}&limit={limit}&scroll=true"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code == 200:
        print(f"Search successful for query: {query}")
        data = response.json()
        results.extend(data["results"])
        scroll_id = data.get("scrollId")

        while scroll_id and len(results) < max_results:
            url = f"{API_ENDPOINT}search/works?scrollId={scroll_id}&limit={limit}"
            response = requests.get(url, headers=HEADERS)
            if response.status_code == 200:
                data = response.json()
                results.extend(data["results"])
                scroll_id = data.get("scrollId")
            else:
                break
    return results[:max_results]

def extract_and_save_to_csv(data, csv_file_name):
    headers = ["Source", "Source_URL", "Title", "Download_URL", "Abstract", "Full_Text", "Year_Published"]
    extracted_data = []
    
    try:
        with open(csv_file_name, "w", encoding="utf-8", newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            
            for work_item in data[:10]:
                provider_name = "Unknown"
                provider_url = "Unknown"
                
                # Safely check for dataProviders
                data_providers = work_item.get('dataProviders', [])
                if data_providers and len(data_providers) > 0 and 'url' in data_providers[0]:
                    provider = data_providers[0]['url']
                    try:
                        provider_info = requests.get(provider, headers=HEADERS)
                        if provider_info.status_code == 200:
                            provider_info = provider_info.json()
                            provider_name = provider_info.get('name', "Unknown")
                            provider_url = provider_info.get('homepageUrl', "Unknown")
                    except:
                        pass
                
                entry = {
                    "Source": provider_name,
                    "Source_URL": provider_url,
                    "Title": work_item.get("title", ""),
                    "Download_URL": work_item.get("downloadUrl", ""),
                    "Abstract": work_item.get("abstract", ""),
                    "Full_Text": work_item.get("fullText", ""),
                    "Year_Published": work_item.get("yearPublished", ""),
                }
                
                writer.writerow(entry)
                extracted_data.append(entry)
                
        print(f"CSV saved successfully at: {csv_file_name}")
        return extracted_data
    except Exception as e:
        print(f"Error saving CSV: {e}")
        return None
