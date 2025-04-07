# helper/doi_finder.py
import requests
import json
import time
import xml.etree.ElementTree as ET
import re
import logging
from urllib.parse import quote
from .extract_secrets import get_secrets

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Constants and Configuration ---
EMAIL = get_secrets("email")

# --- Generic Request Helper ---
def _get_request(url, params=None, headers=None, timeout=15, session=None):
    """Helper to perform GET request using session or default requests."""
    requester = session if session else requests
    try:
        response = requester.get(url, params=params, headers=headers, timeout=timeout)
        return response # Return the full response object
    except requests.exceptions.Timeout:
        logging.warning(f"Request timed out: {url}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Request Exception for {url}: {e}")
    return None

# --- API Helper Functions (Modified for Session) ---

def _get_doi_crossref(title, email, session=None):
    """Fetches DOI from Crossref API using session."""
    logging.debug(f"Querying Crossref for title: {title[:60]}...")
    base_url = "https://api.crossref.org/works"
    params = {'query.bibliographic': title, 'rows': 1, 'mailto': email}
    # User-Agent should be handled by the session passed from the main script

    response = _get_request(base_url, params=params, session=session, timeout=15)

    if response:
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('status') == 'ok' and data['message'].get('items'):
                    item = data['message']['items'][0]
                    if 'DOI' in item and item['DOI']:
                        doi = item['DOI']
                        logging.debug(f"Crossref Found DOI: {doi}")
                        return doi
                    else:
                         logging.debug("Crossref: DOI field empty or missing in first item.")
                else:
                    logging.debug("Crossref: No items found in response message.")
            except json.JSONDecodeError:
                logging.error(f"Crossref JSON Decode Error for title: {title}")
            except Exception as e:
                logging.error(f"Unexpected error processing Crossref response: {e}")
        elif response.status_code == 404:
             logging.debug(f"Crossref: 404 Not Found for title '{title}'")
        else:
            logging.warning(f"Crossref HTTP Error: {response.status_code} for title '{title}'")
    else:
        logging.debug(f"Crossref: No response received for title '{title}'")

    return None


def _get_doi_openalex(title, email, session=None):
    """Fetches DOI from OpenAlex API using session."""
    logging.debug(f"Querying OpenAlex for title: {title[:60]}...")
    encoded_title = quote(title)
    base_url = f"https://api.openalex.org/works?filter=title.search:{encoded_title}"
    params = {'per_page': 1, 'mailto': email}

    response = _get_request(base_url, params=params, session=session, timeout=15)

    if response:
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('results') and len(data['results']) > 0:
                    item = data['results'][0]
                    doi_url = item.get('doi')
                    if doi_url and 'doi.org/' in doi_url:
                        doi = doi_url.split('doi.org/', 1)[1]
                        logging.debug(f"OpenAlex Found DOI: {doi}")
                        return doi
                    else:
                        logging.debug("OpenAlex: DOI field missing or not in expected format.")
                else:
                    logging.debug("OpenAlex: No results found.")
            except json.JSONDecodeError:
                logging.error(f"OpenAlex JSON Decode Error for title: {title}")
            except Exception as e:
                 logging.error(f"Unexpected error processing OpenAlex response: {e}")
        elif response.status_code == 404:
            logging.debug(f"OpenAlex: 404 Not Found for title '{title}'")
        else:
            logging.warning(f"OpenAlex HTTP Error: {response.status_code} for title '{title}'")
    else:
        logging.debug(f"OpenAlex: No response received for title '{title}'")

    return None


def _get_doi_semantic_scholar(title, session=None):
    """Fetches DOI from Semantic Scholar API using session."""
    logging.debug(f"Querying Semantic Scholar for title: {title[:60]}...")
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {'query': title, 'fields': 'doi', 'limit': 1}

    # Keep pre-emptive sleep for S2 politeness
    time.sleep(0.3)

    # Session's retry logic handles 429s, but initial request uses the helper
    response = _get_request(base_url, params=params, session=session, timeout=15)

    if response:
        if response.status_code == 200:
             try:
                 data = response.json()
                 if data.get('data') and len(data['data']) > 0:
                     paper_data = data['data'][0]
                     doi = paper_data.get('doi')
                     if doi:
                         logging.debug(f"Semantic Scholar Found DOI: {doi}")
                         return doi
                     else:
                         logging.debug("Semantic Scholar: DOI field missing in first result.")
                 else:
                     # If 'data' is empty or not present, it means no match found
                     logging.debug("Semantic Scholar: No matching paper data found.")
             except json.JSONDecodeError:
                 logging.error(f"Semantic Scholar JSON Decode Error for title: {title}")
             except Exception as e:
                 logging.error(f"Unexpected error processing Semantic Scholar response: {e}")
        elif response.status_code == 404:
             logging.debug(f"Semantic Scholar: 404 Not Found endpoint hit (shouldn't happen for search).")
        # 429 handled by session retry, other errors logged by session or _get_request
        elif response.status_code != 429: # Don't log 429 warning if session handles it
             logging.warning(f"Semantic Scholar HTTP Error: {response.status_code} for title '{title}'")

    else:
         logging.debug(f"Semantic Scholar: No response received for title '{title}'")

    return None


def _get_doi_arxiv(title, session=None):
    """Fetches DOI (arXiv format) from arXiv API using session."""
    logging.debug(f"Querying arXiv for title: {title[:60]}...")
    base_url = "http://export.arxiv.org/api/query"
    # Clean title slightly for query - remove excessive whitespace
    clean_title = ' '.join(title.split())
    search_query = f'ti:"{clean_title}"' # Exact phrase search
    params = {'search_query': search_query, 'max_results': 1}

    # Keep mandatory arXiv sleep BEFORE the request
    logging.debug("Waiting 3.1 seconds for arXiv API politeness...")
    time.sleep(3.1)

    response = _get_request(base_url, params=params, timeout=20, session=session) # Longer timeout for arXiv

    if response:
        if response.status_code == 200:
            try:
                # Parse XML response
                root = ET.fromstring(response.content)
                namespaces = {'atom': 'http://www.w3.org/2005/Atom',
                              'opensearch': 'http://a9.com/-/spec/opensearch/1.1/'} # Add opensearch namespace

                # Check if any results were returned
                total_results_elem = root.find('opensearch:totalResults', namespaces)
                if total_results_elem is not None and int(total_results_elem.text) == 0:
                    logging.debug("arXiv: API reported 0 results found.")
                    return None

                entry = root.find('atom:entry', namespaces)
                if entry is not None:
                    arxiv_id_url_elem = entry.find('atom:id', namespaces)
                    if arxiv_id_url_elem is not None:
                        arxiv_id_url = arxiv_id_url_elem.text
                        match = re.search(r'arxiv\.org/abs/([^v]+)(v\d+)?$', arxiv_id_url)
                        if match:
                            arxiv_id = match.group(1)
                            # Construct the recommended DOI format for arXiv papers
                            doi = f"10.48550/arXiv.{arxiv_id}"
                            logging.debug(f"arXiv Found DOI: {doi}")
                            return doi
                        else:
                            logging.warning(f"arXiv: Could not parse arXiv ID from URL: {arxiv_id_url}")
                    else:
                         logging.warning("arXiv: Found entry but missing 'id' element.")
                else:
                    # This case might occur if totalResults > 0 but entry is missing (unlikely)
                    logging.debug("arXiv: Response indicates results, but no 'entry' element found.")

            except ET.ParseError:
                logging.error(f"arXiv XML Parse Error for title: {title}")
            except Exception as e:
                 logging.error(f"Unexpected error processing arXiv response: {e}")

        else:
            logging.warning(f"arXiv HTTP Error: {response.status_code} for title '{title}'")
    else:
        logging.debug(f"arXiv: No response received for title '{title}'")

    return None


# --- Main Combined Function (Modified for Session) ---
def get_doi(title, email=EMAIL, session=None):
    """
    Tries to find the DOI for a paper title by querying APIs in order, using session.
    """
    if not title:
        logging.warning("get_doi called with empty title.")
        return None


    logging.debug(f"--- Starting DOI search for title: {title[:60]}... ---")

    # Try APIs sequentially, passing the session down
    # Order: arXiv first (specific format), then general ones
    doi = _get_doi_arxiv(title, session=session)
    if doi: return doi

    doi = _get_doi_crossref(title, email, session=session)
    if doi: return doi

    doi = _get_doi_openalex(title, email, session=session)
    if doi: return doi

    doi = _get_doi_semantic_scholar(title, session=session)
    if doi: return doi

    logging.info(f"--- DOI search failed for title: {title[:60]}... ---")
    return None

# Example Usage (can be removed)
# if __name__ == "__main__":
#     title_cr = "Attention is All you Need"
#     title_arxiv = "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding"
#     title_oa = "An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale"
#     title_s2 = "Deep Residual Learning for Image Recognition" # Also in others
#     title_none = "A Paper Title That Likely Does Not Exist Anywhere Online ZYX123"

#     print(f"Searching for: '{title_cr}'")
#     print(f"DOI Found: {get_doi(title_cr)}\n")

#     print(f"Searching for: '{title_arxiv}'")
#     print(f"DOI Found: {get_doi(title_arxiv)}\n")

#     print(f"Searching for: '{title_oa}'")
#     print(f"DOI Found: {get_doi(title_oa)}\n")

#     print(f"Searching for: '{title_s2}'")
#     print(f"DOI Found: {get_doi(title_s2)}\n")

#     print(f"Searching for: '{title_none}'")
#     print(f"DOI Found: {get_doi(title_none)}\n")