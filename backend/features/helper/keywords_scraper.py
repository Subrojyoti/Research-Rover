import requests
import json
import time
import logging
import urllib.parse
from typing import List, Optional, Dict, Any # For type hinting
from .extract_secrets import get_secrets

# --- Constants and Configuration ---
EMAIL = get_secrets("email")

# --- Helper Functions for Keyword Extraction ---

def _fetch_json(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: int = 15) -> Optional[Dict[str, Any]]:
    """Generic function to fetch JSON data with error handling."""
    try:
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        # Automatically raise exception for bad status codes (4xx or 5xx)
        response.raise_for_status()
        return response.json()
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


def _get_keywords_openalex(doi: str, email: str) -> Optional[List[str]]:
    """Fetches keywords and concepts from OpenAlex using DOI."""
    logging.info(f"Querying OpenAlex for keywords (DOI: {doi})")
    # URL-encode the DOI just in case it contains special characters like '/'
    encoded_doi = urllib.parse.quote(doi)
    # Construct the URL using the DOI resolver format
    url = f"https://api.openalex.org/works/doi:{encoded_doi}"
    params = {'mailto': email}

    data = _fetch_json(url, params=params)
    if not data:
        return None

    keywords_found = []

    # 1. Get author keywords if available
    if isinstance(data.get('keywords'), list):
        for kw_item in data['keywords']:
             # Check if keyword item is a dictionary with 'keyword' field (newer format?) or just a string
             if isinstance(kw_item, dict) and isinstance(kw_item.get('keyword'), str):
                 keywords_found.append(kw_item['keyword'])
             elif isinstance(kw_item, str): # Handle if it's just a list of strings
                 keywords_found.append(kw_item)


    # 2. Get concepts (often more comprehensive)
    if isinstance(data.get('concepts'), list):
        # Sort concepts by score (descending) and take top N (e.g., 5)
        concepts = sorted(data['concepts'], key=lambda x: x.get('score', 0), reverse=True)
        for concept in concepts[:5]: # Limit to top 5 concepts
            if isinstance(concept.get('display_name'), str):
                 keywords_found.append(concept['display_name'])

    # Remove duplicates and return
    unique_keywords = sorted(list(set(kw.strip() for kw in keywords_found if kw.strip())))
    if unique_keywords:
        logging.info(f"OpenAlex found keywords/concepts: {unique_keywords}")
        return unique_keywords
    else:
        logging.info("OpenAlex: No keywords or concepts found.")
        return None


def _get_keywords_semantic_scholar(doi: str) -> Optional[List[str]]:
    """Fetches topics (keywords) from Semantic Scholar using DOI."""
    logging.info(f"Querying Semantic Scholar for topics (DOI: {doi})")
    encoded_doi = urllib.parse.quote(doi)
    url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{encoded_doi}"
    params = {'fields': 'topics'}

    # Basic rate limiting pause before request
    time.sleep(0.3)

    # We need a slightly custom fetch logic here to handle potential 429 retry
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 429:
            logging.warning("Semantic Scholar rate limit hit. Waiting 60 seconds...")
            time.sleep(60)
            response = requests.get(url, params=params, timeout=15) # Retry

        response.raise_for_status() # Check for errors after potential retry
        data = response.json()

        if data and isinstance(data.get('topics'), list):
            keywords_found = [topic['topic'] for topic in data['topics'] if isinstance(topic.get('topic'), str)]
            unique_keywords = sorted(list(set(kw.strip() for kw in keywords_found if kw.strip())))
            if unique_keywords:
                logging.info(f"Semantic Scholar found topics: {unique_keywords}")
                return unique_keywords

    except requests.exceptions.Timeout:
        logging.warning(f"Semantic Scholar request timed out: {url}")
    except requests.exceptions.HTTPError as e:
         if e.response.status_code != 404:
             logging.warning(f"Semantic Scholar HTTP Error: {e.response.status_code} accessing {url}")
         else:
             logging.info(f"Semantic Scholar resource not found (404): {url}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Semantic Scholar Request Exception: {e}")
    except json.JSONDecodeError:
        logging.error(f"Semantic Scholar JSON Decode Error for response from {url}")
    except Exception as e:
         logging.error(f"An unexpected error occurred during S2 keyword fetch: {e}")


    logging.info("Semantic Scholar: No topics found.")
    return None


def _get_keywords_crossref(doi: str, email: str) -> Optional[List[str]]:
    """Fetches 'subject' field from Crossref using DOI."""
    logging.info(f"Querying Crossref for subjects (DOI: {doi})")
    encoded_doi = urllib.parse.quote(doi)
    url = f"https://api.crossref.org/works/{encoded_doi}"
    params = {'mailto': email}
    headers = {'User-Agent': f'KeywordFetcher/1.0 (mailto:{email})'}

    data = _fetch_json(url, params=params, headers=headers)
    if not data or data.get('status') != 'ok':
        return None

    message = data.get('message', {})
    if isinstance(message.get('subject'), list):
        keywords_found = [str(subj) for subj in message['subject']] # Ensure strings
        unique_keywords = sorted(list(set(kw.strip() for kw in keywords_found if kw.strip())))
        if unique_keywords:
            logging.info(f"Crossref found subjects: {unique_keywords}")
            return unique_keywords

    logging.info("Crossref: No 'subject' field found.")
    return None


# --- Main Keyword Fetching Function ---

def get_keywords_for_doi(doi: str, email: str = EMAIL) -> Optional[List[str]]:
    """
    Tries to find keywords for a paper using its DOI by querying APIs:
    1. OpenAlex (checks 'keywords' and 'concepts')
    2. Semantic Scholar (checks 'topics')
    3. Crossref (checks 'subject')

    Args:
        doi (str): The DOI of the paper.
        email (str): Your email address for API identification.

    Returns:
        Optional[List[str]]: A list of unique keywords found, or None if none found.
    """
    if not doi:
        logging.warning("Input DOI is empty.")
        return None
    if email == "your_email@example.com":
         logging.warning("Using placeholder email. Update YOUR_EMAIL for proper API identification.")

    logging.info(f"\n--- Starting Keyword search for DOI: {doi} ---")

    # 1. Try OpenAlex
    keywords = _get_keywords_openalex(doi, email)
    if keywords:
        logging.info(f"--- Keywords found via OpenAlex for DOI: {doi} ---")
        return keywords

    # 2. Try Semantic Scholar
    keywords = _get_keywords_semantic_scholar(doi)
    if keywords:
        logging.info(f"--- Keywords found via Semantic Scholar for DOI: {doi} ---")
        return keywords

    # 3. Try Crossref
    keywords = _get_keywords_crossref(doi, email)
    if keywords:
        logging.info(f"--- Keywords found via Crossref for DOI: {doi} ---")
        return keywords

    logging.info(f"--- Keyword search complete for DOI: {doi}. Not found. ---")
    return None