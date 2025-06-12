import requests
import xml.etree.ElementTree as ET
import re
import logging
# from crewai_tools import ScrapeWebsiteTool
import asyncio
from crawl4ai import AsyncWebCrawler
from .helper.extract_secrets import get_pubmed_api_key
import datetime

PUBMED_API_KEY = get_pubmed_api_key()

def fetch_full_text_from_doi(doi):
    """
    Given a DOI string, fetches the content at https://doi.org/{doi}
    and returns the extracted text (Markdown) using Crawl4AI.
    """
    if not doi:
        return ""
    # This function will be replaced by direct use of _fetch_full_text in a gathered context.
    # However, keeping it for now if it's used elsewhere, or can be removed if not.
    return asyncio.run(_fetch_full_text(f"https://doi.org/{doi}"))

async def _fetch_full_text(url, crawler=None):
    """
    Fetches the full text using the provided crawler instance if given,
    otherwise creates a new one (for backward compatibility).
    """
    if crawler is not None:
        return await _fetch_full_text_with_crawler(crawler, url)
    else:
        async with AsyncWebCrawler() as crawler_instance:
            return await _fetch_full_text_with_crawler(crawler_instance, url)

async def _fetch_full_text_with_crawler(crawler, url):
    try:
        result = await crawler.arun(url=url)
        if result and result.success and hasattr(result, "markdown"):
            return result.markdown
        else:
            logging.warning(f"Failed to fetch or extract markdown from {url}. Result: {result}")
            return ""
    except Exception as e:
        logging.error(f"Exception during fetching full text from {url}: {e}")
        return ""
def search_pubmed(query, max_results=100, start_year=0, end_year=0):
    """
    Search PubMed for articles matching the query and year range.
    Returns results formatted to be compatible with extract_and_save_to_csv.
    """
    logging.info(f"📚 Starting PubMed search for query: '{query}'")
    logging.info(f"Parameters: max_results={max_results}, year range: {start_year}-{end_year}")
    
    # Construct date range for the query
    date_range = ""
    today_str = datetime.date.today().strftime("%Y/%m/%d")
    if start_year and end_year:
        date_range = f"'{start_year}/01/01'[Date - Create]:'{end_year}/12/31[Date - Create]'"
        logging.info(f"Using date range filter: {start_year} to {end_year}")
    elif start_year:
        date_range = f"'{start_year}/01/01'[Date - Create]:'{today_str}'[Date - Create]"
        logging.info(f"Using date range filter: {start_year} to present ({today_str})")
    elif end_year:
        date_range = f"'0001/01/01'[Date - Create]:'{end_year}/12/31'[Date - Create]"
        logging.info(f"Using date range filter: earliest to {end_year}")
    
    if date_range:
        full_query = f"{query} AND {date_range}"
        logging.info(f"Full PubMed query with date range: '{full_query}'")
    else:
        full_query = query
        logging.info(f"Using query without date restrictions: '{full_query}'")
    
    # Search PubMed to get article IDs
    logging.info("Step 1: Retrieving article IDs from PubMed ESearch")
    esearch_url = (
        'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi'
        '?db=pubmed'
        f'&term={full_query}'
        f'&retmax={max_results}'
        '&retmode=json'
        f'&api_key={PUBMED_API_KEY}'
    )
    logging.debug(f"ESearch URL: {esearch_url}")
    
    try:
        esearch_response = requests.get(esearch_url)
        esearch_response.raise_for_status()  # Raise exception for HTTP errors
        
        esearch_data = esearch_response.json()
        if 'esearchresult' not in esearch_data or 'idlist' not in esearch_data['esearchresult']:
            logging.warning("No 'idlist' found in PubMed ESearch response")
            return []
        
        id_list = esearch_data['esearchresult']['idlist']
        count = int(esearch_data['esearchresult'].get('count', '0'))
        
        if not id_list:
            logging.info(f"PubMed search found 0 results for query: '{query}'")
            return []
        
        logging.info(f"PubMed found {count} total matches, retrieved {len(id_list)} article IDs")
        
        # Fetch article details
        logging.info("Step 2: Fetching detailed article data from PubMed EFetch")
        ids = ','.join(id_list)
        efetch_url = (
            'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'
            '?db=pubmed'
            f'&id={ids}'
            '&retmode=xml'
            f'&api_key={PUBMED_API_KEY}'
        )
        logging.debug(f"EFetch URL (without IDs for brevity): {efetch_url.split('&id=')[0]}")
        
        efetch_response = requests.get(efetch_url)
        efetch_response.raise_for_status()
        efetch_data = efetch_response.content
        
        # Parse XML response
        logging.info("Step 3: Parsing XML data from PubMed")
        root = ET.fromstring(efetch_data)
        articles = []
        articles_processed = 0
        articles_with_doi = 0
        articles_with_mesh = 0
        
        # Prepare for concurrent full-text fetching
        doi_to_fetch = []
        parsed_articles_metadata = []

        for article_node in root.findall('.//PubmedArticle'):
            articles_processed += 1
            title = article_node.findtext('.//ArticleTitle')
            abstract = article_node.findtext('.//AbstractText')
            
            # Extract authors
            authors = []
            for author_element in article_node.findall('.//Author'):
                last_name = author_element.findtext('LastName')
                fore_name = author_element.findtext('ForeName')
                if last_name and fore_name:
                    authors.append(f"{fore_name} {last_name}")
                elif last_name:
                    authors.append(last_name)
            authors_str = ', '.join(authors)
            
            # Extract publication date
            pub_date = article_node.find('.//PubDate')
            year = ""
            if pub_date is not None:
                year = pub_date.findtext('Year')
                month = pub_date.findtext('Month')
                day = pub_date.findtext('Day')
                date_parts = [year, month, day]
                date_str = '-'.join(part for part in date_parts if part)
            else:
                date_str = ''
            
            journal = article_node.findtext('.//Journal/Title')
            
            # Extract DOI
            doi = ''
            for eid in article_node.findall('.//ArticleId'):
                if eid.attrib.get('IdType') == 'doi':
                    doi_text = eid.text
                    if doi_text: # Ensure DOI text is not None or empty
                        doi = doi_text.strip()
                        articles_with_doi += 1
                        if doi not in doi_to_fetch: # Avoid duplicate fetches for the same DOI
                             doi_to_fetch.append(doi)
                    break
            
            # Extract keywords (MeSH terms)
            keyword_list = []
            for mesh_heading in article_node.findall('.//MeshHeading'):
                descriptor = mesh_heading.findtext('DescriptorName')
                if descriptor:
                    keyword_list.append(descriptor)
            
            if keyword_list:
                articles_with_mesh += 1
                logging.debug(f"Found {len(keyword_list)} MeSH terms for article: {title[:50] if title else 'Untitled'}...")
            
            # Extract PMID for building the URL
            pmid = ''
            for eid in article_node.findall('.//ArticleId'):
                if eid.attrib.get('IdType') == 'pubmed':
                    pmid = eid.text
                    break

            parsed_articles_metadata.append({
                'title': title,
                'abstract': abstract,
                'authors_str': authors_str,
                'year': year,
                'date_str': date_str,
                'journal': journal,
                'doi': doi,
                'keyword_list': keyword_list,
                'pmid': pmid
            })

        # Concurrently fetch all full texts using a single crawler instance
        logging.info(f"Step 4: Concurrently fetching full text for {len(doi_to_fetch)} unique DOIs.")

        async def fetch_all_full_texts(dois):
            async with AsyncWebCrawler() as crawler:
                tasks = [
                    _fetch_full_text(f"https://doi.org/{d}", crawler=crawler)
                    for d in dois
                ]
                return await asyncio.gather(*tasks)

        # Run the asynchronous tasks with a single crawler instance
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            fetched_full_texts_list = loop.run_until_complete(fetch_all_full_texts(doi_to_fetch))
        finally:
            loop.close()

        doi_to_full_text = dict(zip(doi_to_fetch, fetched_full_texts_list))
        logging.info(f"Successfully fetched {sum(1 for text in fetched_full_texts_list if text)} full texts out of {len(doi_to_fetch)} attempts.")

        # Construct final articles list
        for metadata in parsed_articles_metadata:
            # Create reference string
            reference = ""
            if metadata['authors_str']:
                reference = metadata['authors_str']
                if metadata['year']:
                    reference += f" ({metadata['year']})"
                if metadata['title']:
                    reference += f". {metadata['title']}"
                if metadata['journal']:
                    reference += f". {metadata['journal']}"
                if metadata['doi']:
                    reference += f". doi: {metadata['doi']}"
            
            # Format the article data to match what's expected by the extract_and_save_to_csv function
            article_data = {
                # Fields for extract_and_save_to_csv format
                'id': f"pubmed_{metadata['pmid']}" if metadata['pmid'] else f"pubmed_unknown_{len(articles)}",
                'title': metadata['title'],
                'abstract': metadata['abstract'],
                'doi': metadata['doi'],
                'downloadUrl': f"https://doi.org/{metadata['doi']}" if metadata['doi'] else (f"https://pubmed.ncbi.nlm.nih.gov/{metadata['pmid']}/" if metadata['pmid'] else ""),
                'yearPublished': metadata['year'] if metadata['year'] else "",
                'language': {'code': 'en'},  # Assuming English
                'dataProviders': [{'name': 'PubMed', 'url': f"https://pubmed.ncbi.nlm.nih.gov/"}],
                # Extra metadata fields for the processor
                'fullText': doi_to_full_text.get(metadata['doi'], "") if metadata['doi'] else "",
                'authors': metadata['authors_str'],
                'journal': metadata['journal'],
                'publication_date': metadata['date_str'],
                'meshTerms': metadata['keyword_list']
            }
            articles.append(article_data)
        
        logging.info(f"Successfully parsed and processed {articles_processed} articles from PubMed")
        logging.info(f"Articles with DOI: {articles_with_doi}/{articles_processed}")
        logging.info(f"Articles with MeSH terms: {articles_with_mesh}/{articles_processed}")
        
        return articles
        
    except requests.exceptions.RequestException as e:
        logging.error(f"PubMed API request failed: {str(e)}")
        return []
    except ET.ParseError as e:
        logging.error(f"XML parsing error with PubMed response: {str(e)}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error during PubMed search: {str(e)}")
        return []