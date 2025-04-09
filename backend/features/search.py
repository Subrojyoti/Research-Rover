# search.py
import requests
import os
import csv
import re
import logging
import time
import json # Added import
import urllib
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry # Corrected import path

# Assuming helpers are in a 'helper' subdirectory relative to search.py
# Adjust imports if your structure is different
try:
    from .helper.doi_finder import get_doi
    from .helper.extract_secrets import get_secrets
    from .helper.doi_info_scraper import fetch_bibtex, bibtex_to_formatted_text
    from .helper.keywords_scraper import get_keywords_for_doi
except ImportError as e:
    print(f"Error importing helper modules: {e}")
    # Optionally exit or raise error if helpers are critical
    exit(1)


# --- Setup Logging ---
# Configure logging level and format
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')

# --- Constants and Configuration ---
try:
    CORE_API_KEY = get_secrets("core_api")
    EMAIL = get_secrets("email") # Needed globally and for helper functions
except Exception as e:
    logging.error(f"Failed to load secrets: {e}. Exiting.")
    exit(1)



CORE_API_ENDPOINT = "https://api.core.ac.uk/v3/"
CORE_HEADERS = {"Authorization": f"Bearer {CORE_API_KEY}"}
# OPTIMIZATION: Define max workers for parallel processing
# Adjust based on your machine, network, and API rate limits (start lower, e.g., 5-10)
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", 10)) # Allow overriding via env var



# --- Session with Retries ---
# OPTIMIZATION: Use a Session object for connection pooling and add retries
def create_session_with_retries(
    retries=3,
    backoff_factor=0.5, # Time delay factor: {backoff factor} * (2 ** ({number of total retries} - 1))
    status_forcelist=(500, 502, 503, 504, 429), # Retry on these server errors and rate limits
    session=None,
):
    """Creates a requests Session with robust retry logic."""
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        # Respect Retry-After header if present (important for rate limits like 429)
        respect_retry_after_header=True,
        allowed_methods=frozenset(['HEAD', 'GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'TRACE']) # Methods to retry on
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    # Add common headers like User-Agent globally to the session
    session.headers.update({'User-Agent': f'ResearchFetcher/1.1 (mailto:{EMAIL})'})
    return session

# Create a global session specifically for CORE API calls (uses CORE_HEADERS)
core_session = create_session_with_retries()
core_session.headers.update(CORE_HEADERS)


# --- CORE API Search (Modified to use Session) ---
def search_works(query, limit=100, max_results=10):
    """Search for works using the CORE API with scrolling, session, and error handling."""
   
    results = []
    processed_ids = set() # Keep track of processed CORE IDs to avoid duplicates from scroll
    # URL encode the query parameter
    encoded_query = urllib.parse.quote_plus(query)
    initial_url = f"{CORE_API_ENDPOINT}search/works?q={encoded_query}&limit={limit}&scroll=true"
    logging.info(f">>> Searching CORE for: '{query}' (Max results: {max_results})")

    try:
        response = core_session.get(initial_url) # Use the session
        response.raise_for_status() # Check for HTTP errors (session retry handles transient ones)
        data = response.json()
        logging.info(f"Initial CORE search successful for query: {query}")

        # Process initial batch
        batch_results = data.get("results", [])
        new_results = [r for r in batch_results if r.get('id') not in processed_ids]
        results.extend(new_results)
        processed_ids.update(r.get('id') for r in new_results if r.get('id'))
        logging.info(f"Fetched initial {len(new_results)} results from CORE.")

        scroll_id = data.get("scrollId")

        # Scroll if needed and haven't reached max_results
        while scroll_id and len(results) < max_results:
            logging.info(f"Scrolling CORE results... (Currently have {len(results)}, need {max_results})")
            # Ensure limit doesn't cause overshoot if close to max_results
            remaining_needed = max_results - len(results)
            current_limit = min(limit, remaining_needed)
            if current_limit <= 0 or not continue_search: break # Should not happen with main check, but safeguard

            scroll_url = f"{CORE_API_ENDPOINT}search/works?scrollId={scroll_id}&limit={current_limit}"
            # Consider a small delay if scrolling very rapidly, although session retry helps
            # time.sleep(0.2) # Optional small delay

            response = core_session.get(scroll_url) # Use the session
            if response.status_code == 200:
                data = response.json()
                batch_results = data.get("results", [])
                new_results = [r for r in batch_results if r.get('id') not in processed_ids]
                results.extend(new_results)
                processed_ids.update(r.get('id') for r in new_results if r.get('id'))
                scroll_id = data.get("scrollId") # Get next scrollId
                logging.info(f"Fetched {len(new_results)} more results via scroll.")
            else:
                # Log specific error but attempt to continue if possible (though unlikely)
                logging.warning(f"CORE scroll request failed with status {response.status_code}. Response: {response.text}. Stopping scroll.")
                break # Stop scrolling on error
            
            

    except requests.exceptions.HTTPError as e:
         logging.error(f"CORE API HTTP Error: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.RequestException as e:
        logging.error(f"CORE API request failed: {e}")
    except json.JSONDecodeError:
        logging.error(f"Failed to decode JSON response from CORE API.")
    except Exception as e:
        logging.error(f"An unexpected error occurred during CORE search: {e}", exc_info=True)


    logging.info(f"Total unique results fetched from CORE: {len(results)}")
    # Ensure we don't return more than requested, even if scrolling fetched slightly more
    return results[:max_results]


# --- Text Cleaning Helper ---
def clean_text(text):
    """Removes newlines, excessive whitespace, and potentially problematic characters."""
    if not text or not isinstance(text, str):
        return ""
    # Remove common control characters except tab (\t)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    # Replace various newline representations and tabs with a single space
    text = text.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    # Consolidate multiple spaces into one
    text = ' '.join(text.split())
    return text.strip()


# --- Function to Process a Single Work Item (for Parallel Execution) ---
def process_work_item(work_item, item_index, total_items):
    """Processes a single work item to extract all required information. Runs in a thread."""
    core_id = work_item.get('id', 'N/A')
    thread_name = threading.current_thread().name # Get thread name for logging
    logging.info(f"[Item {item_index+1}/{total_items}] Processing CORE ID: {core_id}")

    # Create a *new* session for this thread/task to avoid sharing issues (thread-local state)
    # This session will be used for all non-CORE API calls within this function.
    try:
        thread_session = create_session_with_retries()
        # Ensure User-Agent is set for this session as well
        thread_session.headers.update({'User-Agent': f'ResearchFetcher/1.1 (mailto:{EMAIL})'})
    except Exception as e:
        logging.error(f"[Item {item_index+1}/{total_items}] Failed to create session: {e}")
        return None # Cannot proceed without a session

    # --- Basic Filtering ---
    title = clean_text(work_item.get('title', ''))
    if not title or title.lower().startswith("annual report"):
        logging.debug(f"[Item {item_index+1}] Skipping '{title[:50]}...' (Filtered Title)")
        return None

    language = work_item.get('language')
    # Ensure language exists, is a dict, has 'code', and is 'en'
    if not isinstance(language, dict) or language.get('code') != 'en':
        logging.debug(f"[Item {item_index+1}] Skipping '{title[:50]}...' (Not English or no language info: {language})")
        return None

    # --- Initialize Data ---
    # Use descriptive N/A or empty lists/strings for missing data
    entry = {
        "Source": "N/A", "Reference": "", "Doi": "", "Title": title,
        "Download_URL": clean_text(work_item.get("downloadUrl", "")),
        "Abstract": clean_text(work_item.get("abstract", "")),
        "Keywords": [], "Full_Text": "", # Full_Text from CORE often requires separate handling
        "Year_Published": work_item.get("yearPublished", "") or "N/A" # Handle potential None year
    }

    # --- Extract Provider Info (Prioritize 'name' field if available) ---
    provider_name = "Unknown"
    # Extract provider info
    data_providers = work_item.get('dataProviders', [])
    if data_providers and len(data_providers) > 0 and 'url' in data_providers[0]:
        provider = data_providers[0].get('url')
        print(f"Provider URL: {provider}")
        try:
            provider_info = requests.get(provider, headers=CORE_HEADERS)
            if provider_info.status_code == 200:
                provider_info = provider_info.json()
                provider_name = provider_info.get('name', "Unknown")
        except:
            pass
        # Add fallback logic here if 'name' is often missing and 'url' fetch is needed
        # else: logging.debug(f"[Item {item_index+1}] Provider name missing in first provider object.")

    entry["Source"] = clean_text(provider_name)

    # --- Handle DOI, Reference, and Keywords (using the thread's session) ---
    doi = clean_text(work_item.get("doi", "")) # Clean DOI from CORE first
    reference = ""
    keywords = []
    bibtex_keywords = None

    # 1. Try finding DOI if not present/valid in CORE data
    # Basic DOI validation regex (simple version)
    doi_pattern = r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$"
    if not doi or not re.match(doi_pattern, doi, re.IGNORECASE):
        if doi: logging.debug(f"[Item {item_index+1}] Invalid DOI format from CORE ('{doi}'). Searching external APIs...")
        else: logging.debug(f"[Item {item_index+1}] DOI missing for '{title[:50]}...'. Searching external APIs...")

        # Pass the thread's session to the helper
        found_doi = get_doi(title, email=EMAIL, session=thread_session)
        if found_doi:
            doi = clean_text(found_doi) # Clean the found DOI too
            # Re-validate the found DOI
            if re.match(doi_pattern, doi, re.IGNORECASE):
                 logging.info(f"[Item {item_index+1}] Found valid DOI externally: {doi}")
            else:
                 logging.warning(f"[Item {item_index+1}] Found DOI externally ('{doi}') but it seems invalid. Discarding.")
                 doi = "" # Discard invalid DOI
        else:
            logging.info(f"[Item {item_index+1}] Could not find DOI externally for '{title[:50]}...'")
            doi = "" # Ensure DOI is empty if not found/invalid

    # 2. If a valid DOI exists, fetch BibTeX and Keywords
    if doi:
        entry["Doi"] = doi # Store the validated/found DOI
        bibtex_data = fetch_bibtex(doi, session=thread_session) # Pass session
        if bibtex_data and not bibtex_data.startswith("Error"):
            # Use helper to parse BibTeX for reference and potentially keywords
            parsed_reference, bibtex_keywords = bibtex_to_formatted_text(bibtex_data)
            entry["Reference"] = clean_text(parsed_reference) # Clean parsed reference
            if bibtex_keywords and isinstance(bibtex_keywords, list):
                 # Clean and store keywords from BibTeX
                keywords = [clean_text(kw) for kw in bibtex_keywords if isinstance(kw, str) and clean_text(kw)]
                logging.debug(f"[Item {item_index+1}] Found keywords in BibTeX: {keywords}")

        # 3. If BibTeX didn't provide keywords, try keyword scraper APIs
        # Check keywords list is still empty
        if not keywords:
            logging.debug(f"[Item {item_index+1}] BibTeX keywords empty for DOI {doi}. Querying keyword APIs...")
            # Pass session to keyword scraper
            external_keywords = get_keywords_for_doi(doi, email=EMAIL, session=thread_session)
            if external_keywords and isinstance(external_keywords, list):
                # Clean and store keywords from external APIs
                keywords = [clean_text(kw) for kw in external_keywords if isinstance(kw, str) and clean_text(kw)]
                logging.info(f"[Item {item_index+1}] Found keywords externally via APIs: {keywords}")

        # Ensure Keywords field contains the final list (could be empty)
        entry["Keywords"] = keywords if keywords else []

    # --- Handle Full Text (Placeholder - requires significant extra work) ---
    # CORE's fullText field is often metadata or requires specific access.
    # Actual parsing needs PDF download (using Download_URL) and parsing libs.
    entry["Full_Text"] = clean_text(work_item.get("fullText", "")) # Basic inclusion

    logging.info(f"[Item {item_index+1}/{total_items}] Finished processing CORE ID: {core_id}")
    return entry # Return the dictionary for this item


# --- Main Extraction and Saving Function (Parallelized) ---
def extract_and_save_to_csv(data, csv_file_name):
    """Extracts data from CORE results in parallel and saves to CSV."""
    if not data:
        logging.warning("No data provided to extract_and_save_to_csv.")
        return []

    # Define headers based on the keys in the 'entry' dictionary created in process_work_item
    headers = ["Source", "Reference", "Doi", "Title", "Download_URL", "Abstract", "Keywords", "Full_Text", "Year_Published"]
    processed_results = []
    total_items = len(data)
    logging.info(f"Starting parallel processing of {total_items} work items using up to {MAX_WORKERS} workers...")
    start_time = time.time()

    # Use ThreadPoolExecutor for parallel I/O-bound tasks (API calls)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix='Worker') as executor:
        # Submit tasks: process_work_item for each item in the data
        # Pass item index and total count for better logging context
        future_to_index = {executor.submit(process_work_item, work_item, i, total_items): i for i, work_item in enumerate(data)}

        # Process completed tasks as they finish to collect results
        for future in as_completed(future_to_index):
            item_index = future_to_index[future]
            try:
                result = future.result() # Get result from the completed future
                if result and isinstance(result, dict): # Check if result is valid
                    processed_results.append(result)
                elif result is None:
                     logging.debug(f"Item at index {item_index} was filtered out during processing.")
                else:
                     logging.warning(f"Unexpected result type from processing item at index {item_index}: {type(result)}")
            except Exception as e:
                # Log exception raised during task execution
                logging.error(f"Error processing work item at index {item_index}: {e}", exc_info=True) # exc_info=True logs traceback

    processing_time = time.time() - start_time
    logging.info(f"Parallel processing finished in {processing_time:.2f} seconds.")
    logging.info(f"Successfully processed and retrieved data for {len(processed_results)} items out of {total_items}.")

    # Check if any data was successfully processed before writing CSV
    if not processed_results:
        logging.warning(f"No data extracted successfully. CSV file '{csv_file_name}' will not be created/updated.")
        return []

    # OPTIMIZATION: Write to CSV after all data is processed
    try:
        logging.info(f"Saving {len(processed_results)} extracted items to {csv_file_name}...")
        with open(csv_file_name, "w", encoding="utf-8", newline='') as csvfile:
            # Use DictWriter for easy writing from list of dictionaries
            writer = csv.DictWriter(csvfile, fieldnames=headers, extrasaction='ignore') # Ignore extra fields if any
            writer.writeheader()
            # Write all processed rows at once
            writer.writerows(processed_results)
        logging.info(f"CSV saved successfully at: {os.path.abspath(csv_file_name)}")
        return processed_results # Return the data that was saved
    except IOError as e:
        logging.error(f"I/O Error saving CSV file '{csv_file_name}': {e}")
    except csv.Error as e:
         logging.error(f"CSV writing error for file '{csv_file_name}': {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred during CSV writing: {e}", exc_info=True)

    return [] # Return empty list if saving failed


