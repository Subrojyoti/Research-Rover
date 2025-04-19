import logging
import pandas as pd
import os
DATA_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))
print(DATA_FOLDER)
def get_context_from_result(search_results, CSV_FILE):
    llm_context_string = ""
    unique_papers = {} # Store unique papers: {doi: {'title': title, 'index': index}}
    context_docs_for_llm = []
    current_paper_index = 1

    # First pass: Identify unique papers and assign indices
    for result in search_results:
        # Use DOI as the primary key, handle potential missing DOIs
        doi = result.get('doi')
        title = result.get('paperTitle', 'Unknown Title')
        if doi and doi not in unique_papers:
            unique_papers[doi] = {'title': title, 'index': current_paper_index}
            current_paper_index += 1
        elif not doi:
            # Handle missing DOI - maybe use title or a placeholder if title is also missing
            # For simplicity, we might treat chunks without DOI as potentially separate sources if needed,
            # or group them under a generic placeholder. Let's assign a unique index based on title if DOI is missing.
            # This part might need refinement based on data quality.
            placeholder_key = f"missing_doi_{title}"
            if placeholder_key not in unique_papers:
                unique_papers[placeholder_key] = {'title': title, 'index': current_paper_index, 'is_placeholder': True}
                current_paper_index += 1


    # Second pass: Build the context string with assigned indices
    source_details_for_output = {} # {index: {'title': title, 'doi': doi}}
    for result in search_results:
        text = result.get('text', '')
        doi = result.get('doi')
        title = result.get('paperTitle', 'Unknown Title')

        if doi and doi in unique_papers:
            paper_info = unique_papers[doi]
            assigned_index = paper_info['index']
            if assigned_index not in source_details_for_output:
                source_details_for_output[assigned_index] = {'title': paper_info['title'], 'doi': doi}
        elif not doi:
            placeholder_key = f"missing_doi_{title}"
            if placeholder_key in unique_papers:
                paper_info = unique_papers[placeholder_key]
                assigned_index = paper_info['index']
                if assigned_index not in source_details_for_output:
                    source_details_for_output[assigned_index] = {'title': paper_info['title'], 'doi': None} # Mark DOI as None
            else:
                # Should not happen if first pass was correct, but as a fallback:
                assigned_index = 0 # Indicate an issue or unmapped chunk
                logging.warning(f"Could not map chunk to a unique paper: {title}")
        else:
            assigned_index = 0 # Should not happen
            logging.warning(f"DOI {doi} found in result but not in unique_papers map.")


        # Format for LLM context - include the assigned citation index
        # Only add index if successfully assigned
        if assigned_index > 0:
            context_docs_for_llm.append(f"[{assigned_index}] [Source Title: {title}]\nChunk Content: {text}\n---")
        else:
            # Include chunks even if mapping failed, but without an index the LLM can cite
            context_docs_for_llm.append(f"[Unmapped Source Title: {title}]\nChunk Content: {text}\n---")

    llm_context_string = "\n".join(context_docs_for_llm)
    # Prepare ordered lists for final output based on assigned indices
    final_paper_titles = [None] * len(source_details_for_output)
    final_paper_dois = [None] * len(source_details_for_output)
    for index, details in source_details_for_output.items():
        # Adjust index to be 0-based for list insertion
        list_index = index - 1
        if 0 <= list_index < len(final_paper_titles):
            final_paper_titles[list_index] = details['title']
            final_paper_dois[list_index] = details['doi'] # Store DOI for URL lookup

    # --- Fetch Download URLs ---
    final_download_urls = [None] * len(final_paper_titles)
    CSV_FILE_PATH = os.path.join(DATA_FOLDER, CSV_FILE)
    try:
        if os.path.exists(CSV_FILE_PATH):
            logging.info(f"Reading CSV for URLs: {CSV_FILE_PATH}")
            df_papers = pd.read_csv(CSV_FILE_PATH)

            # Ensure DOI column exists and handle potential missing values/types
            if 'Doi' in df_papers.columns and 'Download_URL' in df_papers.columns:
                # Convert both lookup DOIs and DataFrame DOIs to string for comparison
                df_papers['Doi'] = df_papers['Doi'].astype(str).fillna('N/A').str.strip()
                # Create a lookup map: DOI -> URL
                url_map = pd.Series(df_papers.Download_URL.values, index=df_papers.Doi).to_dict()

                for i, doi in enumerate(final_paper_dois):
                    if doi: # Only look up if DOI exists
                        url = url_map.get(str(doi).strip()) # Ensure lookup DOI is also string/stripped
                        final_download_urls[i] = url if pd.notna(url) else "URL not available in CSV"
                    else:
                        final_download_urls[i] = "URL not available (DOI missing)"
            else:
                logging.warning(f"'Doi' or 'Download_URL' column not found in {CSV_FILE_PATH}.")
                final_download_urls = ["URL lookup failed (Column missing)"] * len(final_paper_titles)

        else:
            logging.warning(f"Original CSV file not found: {CSV_FILE_PATH}. Cannot fetch download URLs.")
            final_download_urls = ["URL lookup failed (CSV not found)"] * len(final_paper_titles)
    
    except Exception as e:
        logging.error(f"Error reading or processing CSV {CSV_FILE_PATH} for URLs: {e}")
        final_download_urls = ["URL lookup failed (Error)"] * len(final_paper_titles)

    return llm_context_string, final_paper_titles, final_download_urls