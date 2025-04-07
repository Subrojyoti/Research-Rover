# helper/keywords_scraper.py
import requests
import json
import time
import logging
import urllib.parse
from typing import List, Optional, Dict, Any # For type hinting
from .extract_secrets import get_secrets

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Constants and Configuration ---
EMAIL = get_secrets("email") # Fetch email using the helper

# --- Generic JSON Fetch Helper with Session Support ---
def _fetch_json(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: int = 15, session=None) -> Optional[Dict[str, Any]]:
    """Generic function to fetch JSON data with error handling, using session if provided."""
    requester = session if session else requests # Use passed session or default requests
    try:
        response = requester.get(url, params=params, headers=headers, timeout=timeout)
        response.raise_for_status() # Raise exception for bad status codes (4xx or 5xx)
        # Check content type before decoding
        if 'application/json' in response.headers.get('Content-Type', ''):
            return response.json()
        else:
            logging.warning(f"Non-JSON response received from {url}. Content-Type: {response.headers.get('Content-Type')}")
            return None # Or handle non-JSON appropriately
    except requests.exceptions.Timeout:
        logging.warning(f"Request timed out: {url}")
    except requests.exceptions.HTTPError as e:
        # Log non-404 errors as warnings, 404 usually just means "not found"
        if e.response.status_code != 404:
            logging.warning(f"HTTP Error: {e.response.status_code} accessing {url}")
        else:
            logging.info(f"Resource not found (404): {url}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Request Exception: {e}")
    except json.JSONDecodeError:
        logging.error(f"JSON Decode Error for response from {url}")
    except Exception as e:
        logging.error(f"An unexpected error occurred fetching {url}: {e}")
    return None

# --- Keyword Extraction Functions (Modified for Session) ---

def _get_keywords_openalex(doi: str, email: str, session=None) -> Optional[List[str]]:
    """Fetches keywords and concepts from OpenAlex using DOI and session."""
    logging.debug(f"Querying OpenAlex for keywords (DOI: {doi})")
    encoded_doi = urllib.parse.quote(doi)
    url = f"https://api.openalex.org/works/doi:{encoded_doi}"
    params = {'mailto': email}

    data = _fetch_json(url, params=params, session=session) # Pass session
    if not data:
        return None

    keywords_found = []
    # 1. Get author keywords
    if isinstance(data.get('keywords'), list):
         for kw_item in data['keywords']:
             if isinstance(kw_item, dict) and isinstance(kw_item.get('keyword'), str):
                 keywords_found.append(kw_item['keyword'])
             elif isinstance(kw_item, str): # Handle list of strings
                 keywords_found.append(kw_item)

    # 2. Get concepts
    if isinstance(data.get('concepts'), list):
        concepts = sorted(data['concepts'], key=lambda x: x.get('score', 0), reverse=True)
        for concept in concepts[:5]: # Limit to top 5 concepts
            if isinstance(concept.get('display_name'), str):
                keywords_found.append(concept['display_name'])

    # Clean, remove duplicates, sort, and return
    unique_keywords = sorted(list(set(kw.strip() for kw in keywords_found if kw and kw.strip())))
    if unique_keywords:
        logging.debug(f"OpenAlex found keywords/concepts: {unique_keywords}")
        return unique_keywords
    else:
        logging.debug("OpenAlex: No keywords or concepts found.")
        return None


def _get_keywords_semantic_scholar(doi: str, session=None) -> Optional[List[str]]:
    """Fetches topics (keywords) from Semantic Scholar using DOI and session."""
    logging.debug(f"Querying Semantic Scholar for topics (DOI: {doi})")
    encoded_doi = urllib.parse.quote(doi)
    url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{encoded_doi}"
    params = {'fields': 'topics'}

    # Pre-emptive sleep *might* still be useful for S2, even with session retries
    # Keep it short as retry handles actual 429s.
    time.sleep(0.3)

    # Use _fetch_json which now uses the session and its retry logic
    data = _fetch_json(url, params=params, session=session) # Pass session

    if data and isinstance(data.get('topics'), list):
        keywords_found = [topic['topic'] for topic in data['topics'] if isinstance(topic.get('topic'), str)]
        unique_keywords = sorted(list(set(kw.strip() for kw in keywords_found if kw and kw.strip())))
        if unique_keywords:
            logging.debug(f"Semantic Scholar found topics: {unique_keywords}")
            return unique_keywords

    logging.debug("Semantic Scholar: No topics found.")
    return None


def _get_keywords_crossref(doi: str, email: str, session=None) -> Optional[List[str]]:
    """Fetches 'subject' field from Crossref using DOI and session."""
    logging.debug(f"Querying Crossref for subjects (DOI: {doi})")
    encoded_doi = urllib.parse.quote(doi)
    url = f"https://api.crossref.org/works/{encoded_doi}"
    params = {'mailto': email}
    # Headers managed by the session now (assuming User-Agent is set there)

    data = _fetch_json(url, params=params, session=session) # Pass session
    if not data or data.get('status') != 'ok':
        return None

    message = data.get('message', {})
    # Crossref 'subject' field can contain keywords
    if isinstance(message.get('subject'), list):
        keywords_found = [str(subj) for subj in message['subject']] # Ensure strings
        unique_keywords = sorted(list(set(kw.strip() for kw in keywords_found if kw and kw.strip())))
        if unique_keywords:
            logging.debug(f"Crossref found subjects: {unique_keywords}")
            return unique_keywords

    logging.debug("Crossref: No 'subject' field found.")
    return None


# --- Main Keyword Fetching Function (Modified for Session) ---
def get_keywords_for_doi(doi: str, email: str = EMAIL, session=None) -> Optional[List[str]]:
    """
    Tries to find keywords for a paper using its DOI by querying APIs, using session.
    """
    if not doi:
        logging.warning("Input DOI is empty for keyword search.")
        return None

    logging.debug(f"--- Starting Keyword search for DOI: {doi} ---")

    # Try APIs sequentially, passing the session down
    # 1. Try OpenAlex
    keywords = _get_keywords_openalex(doi, email, session=session)
    if keywords:
        logging.info(f"Keywords found via OpenAlex for DOI: {doi}")
        return keywords

    # 2. Try Semantic Scholar
    keywords = _get_keywords_semantic_scholar(doi, session=session)
    if keywords:
        logging.info(f"Keywords found via Semantic Scholar for DOI: {doi}")
        return keywords

    # 3. Try Crossref
    keywords = _get_keywords_crossref(doi, email, session=session)
    if keywords:
        logging.info(f"Keywords found via Crossref for DOI: {doi}")
        return keywords

    logging.info(f"--- Keyword search complete for DOI: {doi}. Not found. ---")
    return None

# Example Usage (can be removed)
# if __name__ == "__main__":
#     test_doi_oa = "10.1038/s41586-020-2649-2" # Has OpenAlex concepts/keywords
#     test_doi_s2 = "10.1016/j.artint.2018.10.003" # Has S2 topics
#     test_doi_cr = "10.1109/cvpr.2017.431" # Might have Crossref subjects

#     print(f"\nKeywords for {test_doi_oa}:")
#     print(get_keywords_for_doi(test_doi_oa))

#     print(f"\nKeywords for {test_doi_s2}:")
#     print(get_keywords_for_doi(test_doi_s2))

#     print(f"\nKeywords for {test_doi_cr}:")
#     print(get_keywords_for_doi(test_doi_cr))

#     print(f"\nKeywords for invalid DOI:")
#     print(get_keywords_for_doi("10.invalid/doi"))