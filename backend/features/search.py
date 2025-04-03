import requests
import os
import csv
import re
from .helper.doi_finder import get_doi
from .helper.extract_secrets import get_secrets
from .helper.doi_info_scraper import fetch_bibtex, bibtex_to_formatted_text
# --- Constants and Configuration ---
CORE_API_KEY = get_secrets("core_api")
CORE_API_ENDPOINT = "https://api.core.ac.uk/v3/"
HEADERS = {"Authorization": f"Bearer {CORE_API_KEY}"}

# Search for works using the CORE API
def search_works(query, limit=100, max_results=30):
    results = []
    url = f"{CORE_API_ENDPOINT}search/works?q={query}&limit={limit}&scroll=true"
    print(f">>>Searching for {query}")
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
    else:
        print("Search Unsuccesfull")
    print(f"Total results found: {len(results)}")
    return results[:max_results]


def extract_and_save_to_csv(data, csv_file_name):
    headers = ["Source", "Reference", "Doi", "Title", "Download_URL", "Abstract", "Keywords", "Full_Text", "Year_Published"]
    extracted_data = []
    
    def clean_text(text):
        if not text:
            return ""
        # Remove newlines and excessive whitespace
        return ' '.join(str(text).replace('\n', ' ').split())
    
    try:
        with open(csv_file_name, "w", encoding="utf-8", newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            
            for work_item in data:
                title = clean_text(work_item.get('title', ''))
                if title.lower().startswith("annual report"):
                    continue
                language = work_item.get('language')
                if not language:
                    continue  # Skip if no language is found
                if not language.get('code') or language.get('code') != 'en':
                    continue
                # Initialize with default values
                provider_name = "Unknown"
                # Extract provider info
                data_providers = work_item.get('dataProviders', [])
                if data_providers and len(data_providers) > 0 and 'url' in data_providers[0]:
                    provider = data_providers[0].get('url')
                    try:
                        provider_info = requests.get(provider, headers=HEADERS)
                        if provider_info.status_code == 200:
                            provider_info = provider_info.json()
                            provider_name = provider_info.get('name', "Unknown")
                    except:
                        pass
                
                
                # Handle DOI extraction
                doi = work_item.get("doi", "")
                reference = ""
                keywords = []
                if not doi:
                    doi = get_doi(title)
                if doi:
                    reference, keywords = bibtex_to_formatted_text(fetch_bibtex(doi))
                entry = {
                    "Source": clean_text(provider_name),
                    "Reference": reference,
                    "Doi": clean_text(doi),
                    "Title": clean_text(work_item.get("title", "")),
                    "Download_URL": clean_text(work_item.get("downloadUrl", "")),
                    "Abstract": clean_text(work_item.get("abstract", "")),
                    "Keywords": keywords,
                    "Full_Text": clean_text(work_item.get("fullText", "")),
                    "Year_Published": work_item.get("yearPublished", ""),
                }
                
                writer.writerow(entry)
                extracted_data.append(entry)
                
        print(f"CSV saved successfully at: {csv_file_name}")
        return extracted_data
    except Exception as e:
        print(f"Error saving CSV: {e}")
        return None
