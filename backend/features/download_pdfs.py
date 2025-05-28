import csv
import requests
import zipfile
import os
from io import BytesIO
import re
from urllib.parse import unquote

def sanitize_filename(filename):
    """Sanitize the filename to be safe for all operating systems."""
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Limit length to avoid issues with long filenames
    return filename[:200]

def download_pubmed_pdfs(csv_file_path, output_zip_name):
    """
    Downloads PDFs from PubMed URLs using scidownl library.
    
    Args:
        csv_file_path (str): The path to the CSV file.
        output_zip_name (str): The name of the output zip file.
        
    Returns:
        tuple: (success, message) where success is a boolean and message is a string
    """
    try:
        # Import required libraries
        try:
            import pandas as pd
            from scidownl import scihub_download
        except ImportError as e:
            return False, f"Required library not installed: {str(e)}. Please install using 'pip install pandas scidownl'"
        
        # Create a temporary directory for PDFs
        pdf_dir = os.path.join(os.path.dirname(output_zip_name), "temp_pdfs")
        os.makedirs(pdf_dir, exist_ok=True)
        
        # Read CSV using pandas as in the original example
        try:
            df = pd.read_csv(csv_file_path)
            doi_list = df['Download_URL'].tolist()  # Get DOIs from the Download_URL column
        except Exception as e:
            return False, f"Error reading CSV with pandas: {str(e)}"
            
        if not doi_list:
            return False, "No DOIs/URLs found in the CSV file"
        
        # Download PDFs
        success_count = 0
        error_count = 0
        
        for idx, doi in enumerate(doi_list):
            if not doi or pd.isna(doi):
                continue
                
            # Create a safe filename with index prefix as in the original example
            safe_filename = f"{idx+1}_{doi.replace('/', '_')}.pdf"
            out_path = os.path.join(pdf_dir, safe_filename)
            
            try:
                print(f"Attempting to download: {doi}")
                scihub_download(doi, out=out_path)
                
                # Verify the file was actually downloaded and has content
                if os.path.exists(out_path) and os.path.getsize(out_path) > 100:  # Check file exists and isn't empty
                    print(f"Downloaded: {doi} as {safe_filename}")
                    success_count += 1
                else:
                    print(f"Download appeared to succeed but file is missing or empty: {doi}")
                    if os.path.exists(out_path):
                        os.remove(out_path)  # Remove empty file
                    error_count += 1
                    
            except Exception as e:
                print(f"Failed to download {doi}: {e}")
                error_count += 1
                # Continue with next DOI rather than stopping
        
        if success_count == 0:
            return False, f"No PDFs were successfully downloaded. {error_count} errors occurred."
        
        # Create a zip file containing the downloaded PDFs
        with zipfile.ZipFile(output_zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in os.listdir(pdf_dir):
                file_path = os.path.join(pdf_dir, file)
                if os.path.isfile(file_path) and os.path.getsize(file_path) > 0:
                    zipf.write(file_path, arcname=file)
        
        # Clean up the temporary directory
        try:
            for file in os.listdir(pdf_dir):
                file_path = os.path.join(pdf_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            os.rmdir(pdf_dir)
        except Exception as e:
            print(f"Warning: Could not clean up temporary directory: {e}")
        
        result_message = f"Successfully downloaded {success_count} PDFs"
        if error_count > 0:
            result_message += f" (with {error_count} failures)"
            
        return True, result_message
        
    except Exception as e:
        error_message = f"Error downloading PubMed PDFs: {str(e)}"
        print(error_message)
        return False, error_message

def download_core_pdfs(csv_file_path, output_zip_name):
    """
    Reads a CSV file, downloads PDFs from the 'Download_URL' column,
    handling both direct download URLs and arXiv URLs, and saves them
    into a zip file with proper naming.

    Args:
        csv_file_path (str): The path to the CSV file.
        output_zip_name (str): The name of the output zip file.

    Returns:
        tuple: (success, message) where success is a boolean and message is a string
    """
    try:
        pdf_files = []
        error_messages = []

        # Read the CSV file and extract the download URLs and titles
        with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                url = row.get("Download_URL")
                title = row.get("Title", "untitled")
                
                if not url:
                    continue

                try:
                    # Handle arXiv URLs
                    if "arxiv.org/abs/" in url:
                        pdf_url = url.replace("arxiv.org/abs/", "arxiv.org/pdf/") + ".pdf"
                    else:
                        pdf_url = url

                    # Download the PDF
                    response = requests.get(pdf_url, timeout=30)
                    response.raise_for_status()

                    # Create a safe filename from the title
                    safe_title = sanitize_filename(title)
                    filename = f"{safe_title}.pdf"

                    # Add to our list of PDFs
                    pdf_files.append((filename, response.content))
                    print(f"Downloaded: {filename}")

                except requests.exceptions.RequestException as e:
                    error_msg = f"Error downloading {url}: {str(e)}"
                    error_messages.append(error_msg)
                    print(error_msg)
                except Exception as e:
                    error_msg = f"Unexpected error processing {url}: {str(e)}"
                    error_messages.append(error_msg)
                    print(error_msg)

        if not pdf_files:
            return False, "No PDFs were successfully downloaded"

        # Create a zip file containing the downloaded PDFs
        with zipfile.ZipFile(output_zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filename, content in pdf_files:
                zipf.writestr(filename, content)

        success_message = f"Successfully downloaded {len(pdf_files)} PDFs"
        if error_messages:
            success_message += f" (with {len(error_messages)} errors)"

        return True, success_message

    except Exception as e:
        error_message = f"Error creating zip file: {str(e)}"
        print(error_message)
        return False, error_message

def determine_source_from_csv(csv_file_path):
    """
    Determine the source of papers in the CSV file (PubMed or CORE).
    
    Args:
        csv_file_path (str): Path to the CSV file
        
    Returns:
        str: "pubmed" or "core"
    """
    try:
        with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                source = row.get("Source", "").lower()
                if source:
                    if "pubmed" in source:
                        return "pubmed"
                    elif "core" in source:
                        return "core"
                    
                # If Source column doesn't clearly indicate, check URLs
                url = row.get("Download_URL", "")
                if url:
                    if "pubmed" in url or "ncbi.nlm.nih.gov" in url:
                        return "pubmed"
                    elif "core.ac.uk" in url or "arxiv.org" in url:
                        return "core"
            
        # Default to CORE if we can't determine
        return "core"
    except Exception as e:
        print(f"Error determining source: {e}")
        return "core"  # Default to CORE on error

def download_pdfs_from_csv(csv_file_path, output_zip_name="downloaded_pdfs.zip"):
    """
    Downloads PDFs from a CSV file, using the appropriate method based on the source.
    
    Args:
        csv_file_path (str): The path to the CSV file.
        output_zip_name (str): The name of the output zip file.
        
    Returns:
        tuple: (success, message) where success is a boolean and message is a string
    """
    # Determine if the CSV contains PubMed or CORE papers
    source = determine_source_from_csv(csv_file_path)
    
    # Use the appropriate download function
    if source == "pubmed":
        return download_pubmed_pdfs(csv_file_path, output_zip_name)
    else:
        return download_core_pdfs(csv_file_path, output_zip_name)
