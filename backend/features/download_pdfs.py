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

def download_pdfs_from_csv(csv_file_path, output_zip_name="downloaded_pdfs.zip"):
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
