import requests
import json
import time
import xml.etree.ElementTree as ET
import re
from urllib.parse import quote # To correctly encode titles in URLs
from .extract_secrets import get_secrets

# --- Constants and Configuration ---
EMAIL = get_secrets("email")

# --- API Helper Functions ---

def _get_doi_crossref(title, email):
    """Fetches DOI from Crossref API."""
    base_url = "https://api.crossref.org/works"
    params = {
        'query.bibliographic': title,
        'rows': 1, # Get the most relevant match
        'mailto': email # Identify for polite pool
    }
    headers = {
        'User-Agent': f'DOIFetcher/1.0 (mailto:{email})'
    }
    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=15) # Increased timeout
        response.raise_for_status() # Raises HTTPError for bad responses (4XX, 5XX)
        data = response.json()

        if data.get('status') == 'ok' and data['message'].get('items'):
            item = data['message']['items'][0]
            if 'DOI' in item and item['DOI']:
                doi = item['DOI']
                return doi

    except requests.exceptions.Timeout:
        print("Crossref request timed out.")
    except requests.exceptions.HTTPError as e:
        print(f"Crossref HTTP Error: {e.response.status_code} for title '{title}'")
    except requests.exceptions.RequestException as e:
        print(f"Crossref Request Exception: {e}")
    except json.JSONDecodeError:
        print(f"Crossref JSON Decode Error for title: {title}")
    except Exception as e:
        print(f"An unexpected error occurred during Crossref query: {e}")

    return None

def _get_doi_openalex(title, email):
    """Fetches DOI from OpenAlex API."""
    # Encode title safely for URL parameter
    encoded_title = quote(title)
    base_url = f"https://api.openalex.org/works?filter=title.search:{encoded_title}"
    params = {
        'per_page': 1,
        'mailto': email # Identify for polite pool
    }
    try:
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get('results') and len(data['results']) > 0:
            item = data['results'][0]
            doi_url = item.get('doi')
            if doi_url and 'doi.org/' in doi_url:
                doi = doi_url.split('doi.org/', 1)[1]
                return doi

    except requests.exceptions.Timeout:
        print("OpenAlex request timed out.")
    except requests.exceptions.HTTPError as e:
        print(f"OpenAlex HTTP Error: {e.response.status_code} for title '{title}'")
    except requests.exceptions.RequestException as e:
        print(f"OpenAlex Request Exception: {e}")
    except json.JSONDecodeError:
        print(f"OpenAlex JSON Decode Error for title: {title}")
    except Exception as e:
        print(f"An unexpected error occurred during OpenAlex query: {e}")

    return None

def _get_doi_semantic_scholar(title):
    """Fetches DOI from Semantic Scholar API."""
    logging.info(f"Querying Semantic Scholar for: '{title}'")
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        'query': title,
        'fields': 'doi',
        'limit': 1
    }
    # Note: Semantic Scholar has stricter rate limits (100 per 5 mins unauthenticated)
    # Implement more robust rate limiting if hitting limits frequently
    # Basic delay before request:
    time.sleep(0.3) # ~3 requests per second max, well below 100/5min

    try:
        response = requests.get(base_url, params=params, timeout=15)

        if response.status_code == 429:
             time.sleep(60)
             response = requests.get(base_url, params=params, timeout=15) # Retry once

        response.raise_for_status()
        data = response.json()

        if data.get('data') and len(data['data']) > 0:
             paper_data = data['data'][0]
             doi = paper_data.get('doi')
             if doi:
                 return doi
             
    except requests.exceptions.Timeout:
        print("Semantic Scholar request timed out.")
    except requests.exceptions.HTTPError as e:
        # Don't log 404 as warning necessarily, it just means not found often
        if e.response.status_code != 404:
             print(f"Semantic Scholar HTTP Error: {e.response.status_code} for title '{title}'")
    except requests.exceptions.RequestException as e:
        print(f"Semantic Scholar Request Exception: {e}")
    except json.JSONDecodeError:
        print(f"Semantic Scholar JSON Decode Error for title: {title}")
    except Exception as e:
        print(f"An unexpected error occurred during Semantic Scholar query: {e}")
        
    return None

def _get_doi_arxiv(title):
    """Fetches DOI (arXiv format) from arXiv API."""
    base_url = "http://export.arxiv.org/api/query"
    # arXiv title searches need field prefix 'ti:' and quotes for exact phrases
    search_query = f'ti:"{title}"'
    params = {
        'search_query': search_query,
        'max_results': 1
    }

    # arXiv requires delays between requests. Be polite!
    time.sleep(3.1) # Adhere to >= 3 seconds delay

    try:
        response = requests.get(base_url, params=params, timeout=20) # Longer timeout for arXiv
        response.raise_for_status()

        # Parse XML response
        root = ET.fromstring(response.content)
        # Namespace is often present in arXiv's XML
        namespaces = {'atom': 'http://www.w3.org/2005/Atom'}
        entry = root.find('atom:entry', namespaces)

        if entry is not None:
            arxiv_id_url = entry.find('atom:id', namespaces).text
            # Extract the ID part (e.g., '1706.03762' or 'math/0611510v1')
            # Match common formats like 'abs/1706.03762' or 'abs/math/0611510v1'
            match = re.search(r'arxiv\.org/abs/([^v]+)(v\d+)?$', arxiv_id_url)
            if match:
                arxiv_id = match.group(1)
                # Construct the recommended DOI format for arXiv papers
                doi = f"10.48550/arXiv.{arxiv_id}"
                return doi
            
        else:
            # Check for opensearch totalResults to see if 0 results were explicitly returned
             total_results = root.find('{http://a9.com/-/spec/opensearch/1.1/}totalResults')

    except requests.exceptions.Timeout:
        print("arXiv request timed out.")
    except requests.exceptions.HTTPError as e:
        print(f"arXiv HTTP Error: {e.response.status_code} for title '{title}'")
    except requests.exceptions.RequestException as e:
        print(f"arXiv Request Exception: {e}")
    except ET.ParseError:
        print(f"arXiv XML Parse Error for title: {title}")
    except Exception as e:
        print(f"An unexpected error occurred during arXiv query: {e}")

    return None


# --- Main Combined Function ---

def get_doi(title, email=EMAIL):
    """
    Tries to find the DOI for a paper title by querying APIs in order:
    1. arXiv
    2. Crossref
    3. OpenAlex
    4. Semantic Scholar

    Args:
        title (str): The title of the paper.
        email (str): Your email address for API identification (polite pools).

    Returns:
        str: The found DOI, or None if not found in any service.
    """
    if not title:
        return None

    # 1. Try arXiv
    doi = _get_doi_arxiv(title)
    if doi:
        return doi
    # 2. Try Crossref
    doi = _get_doi_crossref(title, email)
    if doi:
        return doi

    # 3. Try OpenAlex
    doi = _get_doi_openalex(title, email)
    if doi:
        return doi

    # 4. Try Semantic Scholar
    doi = _get_doi_semantic_scholar(title)
    if doi:
        return doi

    
    return None