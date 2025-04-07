# helper/doi_info_scraper.py
import requests
import re
import logging

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper Function (moved from search.py for potential reuse) ---
def _get_request(url, params=None, headers=None, timeout=15, session=None):
    """Helper to perform GET request using session or default requests."""
    requester = session if session else requests # Use passed session or default requests
    try:
        response = requester.get(url, params=params, headers=headers, timeout=timeout)
        # Allow callers to handle status codes specifically
        return response
    except requests.exceptions.Timeout:
        logging.warning(f"Request timed out: {url}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Request Exception for {url}: {e}")
    return None

# --- BibTeX Fetching ---
def fetch_bibtex(doi, session=None):
    """Fetch BibTeX entry for a given DOI using DOI.org API, using provided session."""
    if not doi:
        return "Error: DOI is empty."
    url = f"https://doi.org/{doi}"
    headers = {"Accept": "application/x-bibtex"}
    logging.debug(f"Fetching BibTeX for DOI: {doi} from {url}")

    response = _get_request(url, headers=headers, session=session)

    if response:
        if response.status_code == 200:
            logging.debug(f"Successfully fetched BibTeX for DOI: {doi}")
            # Decode response text, trying utf-8 first, then latin-1 as fallback
            try:
                return response.content.decode('utf-8')
            except UnicodeDecodeError:
                logging.warning(f"UTF-8 decode failed for BibTeX DOI {doi}, trying latin-1.")
                try:
                    return response.content.decode('latin-1')
                except Exception as decode_err:
                    logging.error(f"Could not decode BibTeX response for DOI {doi}: {decode_err}")
                    return f"Error fetching DOI {doi}: Could not decode response content"
        elif response.status_code == 404:
            logging.warning(f"BibTeX not found (404) for DOI: {doi}")
            return f"Error fetching DOI {doi}: Not Found (404)"
        else:
            logging.error(f"Error fetching BibTeX for DOI {doi}: Status {response.status_code}")
            return f"Error fetching DOI {doi}: Status {response.status_code}"
    else:
        # Error logged by _get_request
        return f"Error fetching DOI {doi}: Request failed (see logs)"

# --- BibTeX Parsing and Formatting ---
def clean_pages_field(bibtex_entry):
    """Fix common encoding issues in BibTeX fields, especially pages."""
    if not isinstance(bibtex_entry, str):
        return bibtex_entry
    # Replace common mis-encoded en-dash variants with a standard en-dash
    fixed_entry = bibtex_entry.replace('â€“', '–').replace('&#8211;', '–')
    # Correct other potential issues if needed
    # fixed_entry = fixed_entry.replace('Ã¤', 'ä') # Example for umlauts if needed
    return fixed_entry

def bibtex_to_formatted_text(bibtex_entry):
    """
    Convert a BibTeX entry string to a formatted text citation and extract keywords.
    Returns a tuple: (formatted_citation, keywords_list or None).
    """
    if not bibtex_entry or not isinstance(bibtex_entry, str) or bibtex_entry.startswith("Error"):
        return "Citation information not available.", None

    # Apply cleaning first
    bibtex_entry = clean_pages_field(bibtex_entry)

    # Define patterns for extraction (case-insensitive for field names)
    patterns = {
        'author':   re.compile(r'author\s*=\s*[\{"]([^"}]+)[\}"]', re.IGNORECASE),
        'title':    re.compile(r'title\s*=\s*[\{"]([^"}]+)[\}"]', re.IGNORECASE),
        'year':     re.compile(r'year\s*=\s*[\{"]([^"}]+)[\}"]', re.IGNORECASE),
        'doi':      re.compile(r'doi\s*=\s*[\{"]([^"}]+)[\}"]', re.IGNORECASE),
        'journal':  re.compile(r'(?:journal|booktitle)\s*=\s*[\{"]([^"}]+)[\}"]', re.IGNORECASE), # Handle booktitle too
        'volume':   re.compile(r'volume\s*=\s*[\{"]([^"}]+)[\}"]', re.IGNORECASE),
        'number':   re.compile(r'number\s*=\s*[\{"]([^"}]+)[\}"]', re.IGNORECASE),
        'pages':    re.compile(r'pages\s*=\s*[\{"]([^"}]+)[\}"]', re.IGNORECASE),
        'month':    re.compile(r'month\s*=\s*[\{"]([^"}]+)[\}"]', re.IGNORECASE),
        'keywords': re.compile(r'keywords\s*=\s*[\{"]([^"}]+)[\}"]', re.IGNORECASE),
    }

    # Extract values
    data = {}
    for key, pattern in patterns.items():
        match = pattern.search(bibtex_entry)
        # Clean braces and potential leading/trailing whitespace from matched value
        data[key] = match.group(1).replace('{','').replace('}','').strip() if match else None

    # --- Format Citation ---
    authors_text = ""
    if data['author']:
        # Simple author formatting (Last, F. M. and ...) - needs improvement for complex names
        author_list = re.split(r'\s+and\s+', data['author']) # Split by ' and '
        formatted_authors = []
        for auth in author_list:
            parts = auth.split(',') # Try splitting by comma (Last, First M.)
            if len(parts) == 2:
                last_name = parts[0].strip()
                first_names = parts[1].strip()
                # Attempt to create initials (F. M.) - simplistic
                initials = '. '.join(n[0] for n in first_names.split() if n) + '.' if first_names else ''
                formatted_authors.append(f"{last_name}, {initials}")
            else:
                 # If no comma, assume 'First M. Last' or just 'Name' - keep as is for now
                 formatted_authors.append(auth.strip())
        authors_text = ' and '.join(formatted_authors)

    # Format month
    month_dict = {
        'jan': 'Jan.', 'feb': 'Feb.', 'mar': 'Mar.', 'apr': 'Apr.',
        'may': 'May', 'jun': 'Jun.', 'jul': 'Jul.', 'aug': 'Aug.',
        'sep': 'Sep.', 'oct': 'Oct.', 'nov': 'Nov.', 'dec': 'Dec.'
    }
    month_formatted = month_dict.get(data['month'].lower(), data['month'].capitalize()) if data['month'] else ""

    # Construct citation parts, handling potential None values
    citation_parts = []
    if authors_text: citation_parts.append(authors_text)
    if data['year']: citation_parts.append(f"({data['year']})") # Year often in parentheses
    if data['title']: citation_parts.append(f"\"{data['title']}\".") # Title in quotes, ending with period
    if data['journal']: citation_parts.append(f"*{data['journal']}*") # Journal often italicized (using markdown *)
    if data['volume']: citation_parts.append(f"vol. {data['volume']}")
    if data['number']: citation_parts.append(f"no. {data['number']}")
    if data['pages']: citation_parts.append(f"pp. {data['pages']}")
    # Consider adding month if relevant (less common in standard citations)
    # if month_formatted: citation_parts.append(f"{month_formatted}")
    if data['doi']: citation_parts.append(f"doi:{data['doi']}")

    # Join parts with appropriate separators (e.g., comma, period) - basic joining here
    formatted_citation = ", ".join(part for part in citation_parts if part)
    # Simple fix for potential double punctuation ".," -> "."
    formatted_citation = formatted_citation.replace('.,', ',').replace('". ,', '".').replace('.) ,', ').')


    # --- Extract Keywords ---
    keywords_list = None
    if data['keywords']:
        # Split by comma or semicolon, remove whitespace, filter empty strings
        keywords_list = [kw.strip() for kw in re.split(r'[;,]', data['keywords']) if kw.strip()]

    logging.debug(f"Parsed Citation: {formatted_citation}")
    logging.debug(f"Parsed Keywords from BibTeX: {keywords_list}")

    return formatted_citation, keywords_list

# Example Usage (can be removed)
# if __name__ == "__main__":
#     test_doi = "10.1038/nature12373" # Example DOI
#     print(f"Fetching BibTeX for {test_doi}...")
#     bibtex = fetch_bibtex(test_doi)
#     if bibtex and not bibtex.startswith("Error"):
#         # print("\n--- Raw BibTeX ---")
#         # print(bibtex)
#         print("\n--- Formatted Citation & Keywords ---")
#         citation, keywords = bibtex_to_formatted_text(bibtex)
#         print("Citation:", citation)
#         print("Keywords:", keywords)
#     else:
#         print(bibtex)

#     test_doi_404 = "10.9999/invalid-doi-example"
#     print(f"\nFetching BibTeX for {test_doi_404}...")
#     bibtex_404 = fetch_bibtex(test_doi_404)
#     print(bibtex_404)