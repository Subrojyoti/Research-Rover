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
    retries=5,  # Increased from 3 to 5
    backoff_factor=1.0,  # Increased from 0.5 to 1.0 for longer delays
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
def search_works(query, limit=500, max_results=10, start_year=0, end_year=0):
    """Search for works using the CORE API with scrolling, session, and error handling.
    Ensures enough English-language papers are returned by continuing to scroll if needed.
    """
    english_results = []
    processed_ids = set()
    encoded_query = urllib.parse.quote_plus(query)
    if start_year > 0 or end_year > 0:
        encoded_query = encoded_query + f" AND yearPublished>={start_year} AND yearPublished<={end_year}"
    elif start_year > 0:
        encoded_query = encoded_query + f" AND yearPublished>={start_year}"
    elif end_year > 0:
        encoded_query = encoded_query + f" AND yearPublished<={end_year}"
    initial_url = f"{CORE_API_ENDPOINT}search/works?q={encoded_query}&limit={limit}&scroll=true"
    logging.info(f">>> Searching CORE for: '{query}' (Max results: {max_results}, Year range: {start_year}-{end_year})")

    try:
        url = initial_url
        scroll_id = None
        while len(english_results) < max_results:
            response = core_session.get(url)
            response.raise_for_status()
            data = response.json()
            batch_results = data.get("results", [])
            # Filter for English language and not already processed
            new_english = [
                r for r in batch_results
                if r.get('id') not in processed_ids and
                   isinstance(r.get('language'), dict) and
                   r['language'].get('code') == 'en'
            ]
            english_results.extend(new_english)
            processed_ids.update(r.get('id') for r in batch_results if r.get('id'))
            logging.info(f"Fetched {len(new_english)} new English results (total: {len(english_results)})")

            scroll_id = data.get("scrollId")
            if not scroll_id or not batch_results:
                break  # No more results

            # Prepare next scroll URL, fetch more than needed to account for filtering
            remaining_needed = max_results - len(english_results)
            current_limit = min(limit, max(remaining_needed * 2, 10))
            url = f"{CORE_API_ENDPOINT}search/works?scrollId={scroll_id}&limit={current_limit}"

    except requests.exceptions.HTTPError as e:
        logging.error(f"CORE API HTTP Error: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.RequestException as e:
        logging.error(f"CORE API request failed: {e}")
    except json.JSONDecodeError:
        logging.error(f"Failed to decode JSON response from CORE API.")
    except Exception as e:
        logging.error(f"An unexpected error occurred during CORE search: {e}", exc_info=True)

    logging.info(f"Total unique English results fetched from CORE: {len(english_results)}")
    return english_results[:max_results]


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
    # Get the item ID safely - ensure we log its type for debugging
    item_id = work_item.get('id', 'N/A')
    logging.info(f"[Item {item_index+1}/{total_items}] Processing item ID: {item_id} (Type: {type(item_id).__name__})")

    thread_name = threading.current_thread().name # Get thread name for logging
    
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

    # --- Detect source (PubMed or CORE) ---
    # Safely determine if this is a PubMed result based on ID format
    # Handle any type of ID (string, int, None, etc.) without raising exceptions
    is_pubmed = False
    if item_id is not None:
        try:
            # Convert to string safely and then check
            id_str = str(item_id)
            is_pubmed = id_str.startswith('pubmed_')
            logging.debug(f"[Item {item_index+1}] ID '{id_str}' identified as {'PubMed' if is_pubmed else 'CORE'} source")
        except Exception as e:
            # If any error occurs during type conversion, log it and assume not PubMed
            logging.error(f"[Item {item_index+1}] Error determining source from ID: {e}")
            is_pubmed = False

    # --- Extract Provider Info ---
    if is_pubmed:
        # For PubMed results, provider info is already in the dataProviders field
        data_providers = work_item.get('dataProviders', [])
        if data_providers and isinstance(data_providers, list) and len(data_providers) > 0:
            provider_name = data_providers[0].get('name', 'PubMed')
            entry["Source"] = clean_text(provider_name)
        else:
            entry["Source"] = "PubMed"
    else:
        # For CORE results, follow the existing provider extraction logic
        provider_name = "Unknown"
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
        entry["Source"] = clean_text(provider_name)

    # --- Handle DOI, Reference, and Keywords ---
    doi = clean_text(work_item.get("doi", "")) # Clean DOI first
    reference = ""
    keywords = []
    
    # For PubMed, use pre-extracted reference if available
    if is_pubmed:
        # Use pre-extracted MeSH terms as keywords
        mesh_terms = work_item.get('meshTerms', [])
        if mesh_terms:
            keywords = [clean_text(term) for term in mesh_terms if term]
            logging.debug(f"[Item {item_index+1}] Using MeSH terms as keywords: {keywords}")
    
    # 1. Try finding DOI if not present/valid
    doi_pattern = r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$"
    if not doi or not re.match(doi_pattern, doi, re.IGNORECASE):
        if doi: 
            logging.debug(f"[Item {item_index+1}] Invalid DOI format ('{doi}'). Searching external APIs...")
        else: 
            logging.debug(f"[Item {item_index+1}] DOI missing for '{title[:50]}...'. Searching external APIs...")

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

    # 2. If a valid DOI exists, fetch BibTeX and Keywords (if not from PubMed or no keywords yet)
    if doi:
        entry["Doi"] = doi # Store the validated/found DOI
        
        # Only fetch BibTeX if no keywords (for PubMed) or for CORE
        if not keywords or not is_pubmed:
            bibtex_data = fetch_bibtex(doi, session=thread_session) # Pass session
            if bibtex_data and not bibtex_data.startswith("Error"):
                # Use helper to parse BibTeX for reference and potentially keywords
                parsed_reference, bibtex_keywords = bibtex_to_formatted_text(bibtex_data)
                # Use the parsed reference if we don't have one yet
                if not entry["Reference"]:
                    entry["Reference"] = clean_text(parsed_reference)
                
                # For CORE or if we still don't have keywords, use BibTeX keywords
                if (not is_pubmed or not keywords) and bibtex_keywords and isinstance(bibtex_keywords, list):
                    # Clean and store keywords from BibTeX
                    keywords = [clean_text(kw) for kw in bibtex_keywords if isinstance(kw, str) and clean_text(kw)]
                    logging.debug(f"[Item {item_index+1}] Found keywords in BibTeX: {keywords}")

        # 3. If we still don't have keywords and it's not PubMed or we have no keywords, try keyword scraper APIs
        if not keywords:
            logging.debug(f"[Item {item_index+1}] No keywords found yet for DOI {doi}. Querying keyword APIs...")
            # Pass session to keyword scraper
            external_keywords = get_keywords_for_doi(doi, email=EMAIL, session=thread_session)
            if external_keywords and isinstance(external_keywords, list):
                # Clean and store keywords from external APIs
                keywords = [clean_text(kw) for kw in external_keywords if isinstance(kw, str) and clean_text(kw)]
                logging.info(f"[Item {item_index+1}] Found keywords externally via APIs: {keywords}")

    # Store Keywords field with the final list (could be empty)
    entry["Keywords"] = keywords if keywords else []
    
    # For PubMed, use the pre-extracted reference if we don't have one yet
    if is_pubmed and not entry["Reference"] and 'authors' in work_item:
        # Create a basic reference format if not already set
        reference = clean_text(work_item.get('authors', ''))
        year = work_item.get('yearPublished', '')
        if year:
            reference += f" ({year})"
        if title:
            reference += f". {title}"
        journal = work_item.get('journal', '')
        if journal:
            reference += f". {journal}"
        if doi:
            reference += f". doi: {doi}"
        
        entry["Reference"] = clean_text(reference)

    # --- Handle Full Text ---
    full_text = clean_text(work_item.get("fullText", ""))
    if full_text:
        entry["Full_Text"] = full_text
    
    logging.info(f"[Item {item_index+1}/{total_items}] Finished processing item ID: {item_id}")
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
        # Create an empty CSV with just headers to avoid 404 errors
        try:
            with open(csv_file_name, "w", encoding="utf-8", newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
            logging.info(f"Created empty CSV file with headers at: {os.path.abspath(csv_file_name)}")
        except Exception as e:
            logging.error(f"Failed to create empty CSV file: {e}")
        return []

    # OPTIMIZATION: Write to CSV after all data is processed
    try:
        logging.info(f"Saving {len(processed_results)} extracted items to {csv_file_name}...")
        
        # Make sure the directory exists
        os.makedirs(os.path.dirname(os.path.abspath(csv_file_name)), exist_ok=True)
        
        with open(csv_file_name, "w", encoding="utf-8", newline='') as csvfile:
            # Use DictWriter for easy writing from list of dictionaries
            writer = csv.DictWriter(csvfile, fieldnames=headers, extrasaction='ignore') # Ignore extra fields if any
            writer.writeheader()
            
            # Write all processed rows at once
            writer.writerows(processed_results)
            
            # Flush to ensure data is written to disk
            csvfile.flush()
            os.fsync(csvfile.fileno())
            
        # Double-check file exists and has content
        if not os.path.exists(csv_file_name):
            logging.error(f"CSV file does not exist after writing: {csv_file_name}")
            return processed_results
        
        file_size = os.path.getsize(csv_file_name)
        logging.info(f"CSV saved successfully at: {os.path.abspath(csv_file_name)} (Size: {file_size} bytes)")
        return processed_results # Return the data that was saved
    except IOError as e:
        logging.error(f"I/O Error saving CSV file '{csv_file_name}': {e}")
        import traceback
        logging.error(traceback.format_exc())
    except csv.Error as e:
         logging.error(f"CSV writing error for file '{csv_file_name}': {e}")
         import traceback
         logging.error(traceback.format_exc())
    except Exception as e:
        logging.error(f"An unexpected error occurred during CSV writing: {e}", exc_info=True)
        import traceback
        logging.error(traceback.format_exc())

    return processed_results # Return the processed results even if saving failed





