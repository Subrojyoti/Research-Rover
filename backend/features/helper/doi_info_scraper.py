import requests
import re

# Function to fetch BibTeX entry for a given DOI
def fetch_bibtex(doi):
    """Fetch BibTeX entry for a given DOI using DOI.org API."""
    url = f"https://doi.org/{doi}"
    headers = {"Accept": "application/x-bibtex"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.text
        else:
            return f"Error fetching DOI {doi}: {response.status_code}"
    except Exception as e:
        return f"Error: {e}"


def clean_pages_field(bibtex_entry):
    """Fix encoding issues in the pages field."""
    # Replace problematic characters in the pages field
    fixed_entry = re.sub(r'â€“', '–', bibtex_entry)
    return fixed_entry
def bibtex_to_formatted_text(bibtex_entry):
    """Convert a BibTeX entry to a formatted text citation, excluding unknown fields."""
    bibtex_entry = clean_pages_field(bibtex_entry)
    # Extract relevant information using regular expressions
    author_match = re.search(r'author\s*=\s*\{([^}]+)\}', bibtex_entry)
    title_match = re.search(r'title\s*=\s*\{([^}]+)\}', bibtex_entry)
    year_match = re.search(r'year\s*=\s*\{([^}]+)\}', bibtex_entry)
    doi_match = re.search(r'doi\s*=\s*\{([^}]+)\}', bibtex_entry)
    journal_match = re.search(r'journal\s*=\s*\{([^}]+)\}', bibtex_entry)
    volume_match = re.search(r'volume\s*=\s*\{([^}]+)\}', bibtex_entry)
    number_match = re.search(r'number\s*=\s*\{([^}]+)\}', bibtex_entry)
    pages_match = re.search(r'pages\s*=\s*\{([^}]+)\}', bibtex_entry)
    month_match = re.search(r'month\s*=\s*\{([^}]+)\}', bibtex_entry)
    keywords_match = re.search(r'keywords\s*=\s*\{([^}]+)\}', bibtex_entry)

    # Extract values or set to None if not found
    author = author_match.group(1) if author_match else None
    title = title_match.group(1) if title_match else None
    year = year_match.group(1) if year_match else None
    doi = doi_match.group(1) if doi_match else None
    journal = journal_match.group(1) if journal_match else None
    volume = volume_match.group(1) if volume_match else None
    number = number_match.group(1) if number_match else None
    pages = pages_match.group(1) if pages_match else None
    month = month_match.group(1) if month_match else None
    keywords = keywords_match.group(1) if keywords_match else None

    # Format the author list
    authors_text = ""
    if author:
        author_list = author.split(' and ')
        formatted_authors = []
        for auth in author_list:
            parts = auth.split(', ')
            if len(parts) == 2:
                formatted_authors.append(f"{parts[0][0]}. {parts[1]}")
            else:
                formatted_authors.append(auth)
        authors_text = ', '.join(formatted_authors)

    # Convert month abbreviation to capitalized format if available
    month_dict = {
        'jan': 'Jan.', 'feb': 'Feb.', 'mar': 'Mar.', 'apr': 'Apr.',
        'may': 'May', 'jun': 'June', 'jul': 'July', 'aug': 'Aug.',
        'sep': 'Sept.', 'oct': 'Oct.', 'nov': 'Nov.', 'dec': 'Dec.'
    }
    
    month_formatted = month_dict.get(month.lower(), month.capitalize()) if month else ""

    # Construct the formatted citation, excluding unknown fields
    citation_parts = []
    
    if authors_text:
        citation_parts.append(authors_text)
    
    if title:
        citation_parts.append(f"\"{title}\"")  # Remove the comma here
    
    if journal:
        citation_parts.append(f"in {journal}")
    
    if volume:
        citation_parts.append(f"vol. {volume}")
    
    if number:
        citation_parts.append(f"no. {number}")
    
    if pages:
        citation_parts.append(f"pp. {pages}")
    
    if month_formatted and year:
        citation_parts.append(f"{month_formatted} {year}")
    elif year:  # If only year is available
        citation_parts.append(year)

    if doi:
        citation_parts.append(f"doi: {doi}")

    # Join all parts together into a single string and ensure proper punctuation
    return ", ".join(citation_parts) + ".", keywords