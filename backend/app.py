from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import os
import csv
import sys
import json
from features.search import search_works, extract_and_save_to_csv
from features.download_pdfs import download_pdfs_from_csv
from features.embedding_and_indexing import process_data_generate_vectors_and_metadata, build_faiss_index, save_metadata_list, save_doi_mapped_json, search_faiss
from sentence_transformers import SentenceTransformer
import faiss
import re
import time
import pandas as pd


from utils.llm_setup import llm_instance as llm
# Increase CSV field size limit
maxInt = sys.maxsize
while True:
    try:
        csv.field_size_limit(maxInt)
        break
    except OverflowError:
        maxInt = int(maxInt/10)

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend-backend communication

# Define the PDF directory (absolute path)
DATA_FOLDER = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
os.makedirs(DATA_FOLDER, exist_ok=True)

# Global variable to track search progress
search_progress = {
    "stage": 0,
    "sub_stage": 0,
    "message": "Not started",
    "timestamp": time.time()
}

# Global variable to track embedding progress
embedding_progress = {
    "stage": 0,
    "message": "Not started",
    "timestamp": time.time()
}

def sanitize_filename(filename):
    # Replace any non-alphanumeric characters (except spaces) with underscore
    return re.sub(r'[^a-zA-Z0-9\s]', '_', filename)

# --- Search Endpoint ---
@app.route("/search", methods=["GET"])
def search():
    try:
        global search_progress
        query = request.args.get("query", "")
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))
        
        # Handle empty or invalid values for max_results, start_year, and end_year
        try:
            max_results = int(request.args.get("max_results", 10))
        except (ValueError, TypeError):
            max_results = 10
            
        try:
            start_year = int(request.args.get("start_year", 0))
        except (ValueError, TypeError):
            start_year = 0
            
        try:
            end_year = int(request.args.get("end_year", 0))
        except (ValueError, TypeError):
            end_year = 0
            
        print(f"Received search query: {query}, page: {page}, per_page: {per_page}, max_results: {max_results}, start_year: {start_year}, end_year: {end_year}")
        if not query:
            return jsonify({"error": "Query parameter is required"}), 400

        # Update progress - Stage 0: Starting search
        search_progress = {
            "stage": 0,
            "sub_stage": 0,
            "message": "Initializing search",
            "timestamp": time.time()
        }

        # Clear the data folder
        if os.path.exists(DATA_FOLDER):
            for file in os.listdir(DATA_FOLDER):
                file_path = os.path.join(DATA_FOLDER, file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(f"Error clearing file: {e}")

        # Update progress - Stage 1: Processing results
        search_progress = {
            "stage": 1,
            "sub_stage": 0,
            "message": "Querying CORE API",
            "timestamp": time.time()
        }
        
        results = search_works(query, max_results=max_results, start_year=start_year, end_year=end_year)
        if not results:
            search_progress = {
                "stage": -1,
                "sub_stage": 0,
                "message": "No results found",
                "timestamp": time.time()
            }
            return jsonify({"error": "No results found"}), 404
        
        # Update progress - Stage 2: Finding DOIs
        search_progress = {
            "stage": 2,
            "sub_stage": 0,
            "message": "Extracting paper metadata",
            "timestamp": time.time()
        }

        # Sanitize the filename
        csv_filename = f'{re.sub(r"[^a-zA-Z0-9]", "_", query)}.csv'
        csv_path = os.path.join(DATA_FOLDER, csv_filename)
        
        # Update progress - Stage 3: Creating CSV
        search_progress = {
            "stage": 3,
            "sub_stage": 0,
            "message": "Processing paper data",
            "timestamp": time.time()
        }
        
        processed_results = extract_and_save_to_csv(results, csv_path)

        # Update progress - Stage 4: Complete
        search_progress = {
            "stage": 4,
            "sub_stage": 0,
            "message": "Search complete",
            "timestamp": time.time()
        }
        # Calculate pagination
        total_results = len(processed_results)
        total_pages = (total_results + per_page - 1) // per_page  # Ceiling division
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, total_results)
        
        # Return paginated results
        return jsonify({
            "results": results[start_idx:end_idx],
            "csv_filename": csv_filename,
            "total_results": total_results,
            "current_page": page,
            "total_pages": total_pages,
            "per_page": per_page
        })

    except Exception as e:
        print(f"Search error: {str(e)}")
        search_progress = {
            "stage": -1,
            "sub_stage": 0,
            "message": f"Error: {str(e)}",
            "timestamp": time.time()
        }
        return jsonify({"error": str(e)}), 500

@app.route("/search_progress", methods=["GET"])
def get_search_progress():
    """Endpoint to get the current search progress"""
    return jsonify(search_progress)

@app.route("/embedding_progress", methods=["GET"])
def get_embedding_progress():
    """Endpoint to get the current embedding progress"""
    return jsonify(embedding_progress)

# --- Download CSV Endpoint ---
@app.route("/download/<filename>")
def download_csv(filename):
    try:
        filename =f"_".join(filename.split("%20"))
        return send_from_directory(DATA_FOLDER, filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404

# --- Get CSV Data Endpoint ---
@app.route("/get_csv_data/<filename>")
def get_csv_data(filename):
    try:
        csv_path = os.path.join(DATA_FOLDER, filename)
        if not os.path.exists(csv_path):
            print(f"CSV file not found: {csv_path}")
            return jsonify({"error": "CSV file not found"}), 404

        papers = []
        print(f"Reading CSV file: {csv_path}")
        
        # Read CSV in chunks to handle large files
        with open(csv_path, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            chunk_size = 10  # Process 10 rows at a time
            chunk = []
            
            for row in reader:
                try:
                    paper = {
                        'source': str(row.get('Source', '')).strip() or 'Unknown',
                        'title': str(row.get('Title', '')).strip() or 'Unknown',
                        'download_url': str(row.get('Download_URL', '')).strip() or '',
                        'year': str(row.get('Year_Published', '')).strip() or 'Unknown',
                        'keywords': str(row.get('Keywords', '')).strip() or '[]'
                    }
                    chunk.append(paper)
                    
                    if len(chunk) >= chunk_size:
                        papers.extend(chunk)
                        chunk = []
                        
                except Exception as row_error:
                    print(f"Error processing row: {row} - Error: {str(row_error)}")
                    continue
            
            if chunk:  # Add remaining papers
                papers.extend(chunk)
                    
        if not papers:
            print("No valid papers found in CSV")
            return jsonify({"error": "No valid data found in CSV"}), 404
                
        print(f"Successfully processed {len(papers)} papers")
        return jsonify(papers)
    except Exception as e:
        print(f"Error processing CSV: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": "Error processing CSV file"}), 500

# --- Get Paginated Results Endpoint ---
@app.route("/get_paginated_results", methods=["GET"])
def get_paginated_results():
    try:
        csv_filename = request.args.get("filename", "")
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))
        
        if not csv_filename:
            return jsonify({"error": "Filename parameter is required"}), 400
            
        csv_path = os.path.join(DATA_FOLDER, csv_filename)
        if not os.path.exists(csv_path):
            print(f"CSV file not found: {csv_path}")
            return jsonify({"error": "CSV file not found"}), 404

        papers = []
        print(f"Reading CSV file: {csv_path}")
        
        # Read CSV in chunks to handle large files
        with open(csv_path, 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                try:
                    paper = {
                        'source': str(row.get('Source', '')).strip() or 'Unknown',
                        'title': str(row.get('Title', '')).strip() or 'Unknown',
                        'download_url': str(row.get('Download_URL', '')).strip() or '',
                        'year': str(row.get('Year_Published', '')).strip() or 'Unknown',
                        'keywords': str(row.get('Keywords', '')).strip() or '[]'
                    }
                    papers.append(paper)
                except Exception as row_error:
                    print(f"Error processing row: {row} - Error: {str(row_error)}")
                    continue
                    
        if not papers:
            print("No valid papers found in CSV")
            return jsonify({"error": "No valid data found in CSV"}), 404
        
        # Calculate pagination
        total_results = len(papers)
        total_pages = (total_results + per_page - 1) // per_page  # Ceiling division
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, total_results)
        
        # Return paginated results
        return jsonify({
            "results": papers[start_idx:end_idx],
            "total_results": total_results,
            "current_page": page,
            "total_pages": total_pages,
            "per_page": per_page
        })
                
    except Exception as e:
        print(f"Error processing CSV: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": "Error processing CSV file"}), 500

# --- Download PDFs Endpoint ---
@app.route("/download_pdfs/<filename>")
def download_pdfs(filename):
    try:
        # Get the CSV file path
        csv_file_path = os.path.join(DATA_FOLDER, filename)
        
        if not os.path.exists(csv_file_path):
            return jsonify({"error": "CSV file not found"}), 404
            
        # Create a unique zip filename based on the CSV filename
        zip_filename = f"{os.path.splitext(filename)[0]}_pdfs.zip"
        zip_path = os.path.join(DATA_FOLDER, zip_filename)
        
        # Download PDFs and create zip file
        download_pdfs_from_csv(csv_file_path, zip_path)
        
        if not os.path.exists(zip_path):
            return jsonify({"error": "Failed to create zip file"}), 500
            
        # Send the zip file
        return send_file(
            zip_path,
            as_attachment=True,
            download_name=zip_filename,
            mimetype='application/zip'
        )
        
    except Exception as e:
        app.logger.error(f"Error downloading PDFs: {str(e)}")
        return jsonify({"error": "Failed to download PDFs"}), 500

# --- Create Embedding Endpoint & Build FAISS Index Endpoint ---
@app.route("/create_embedding/<filename>")
def create_embedding_and_build_faiss_index(filename):
    start = time.time()
    try:
        global embedding_progress
        # Load data from CSV file
        csv_path = os.path.join(DATA_FOLDER, filename)
        if not os.path.exists(csv_path):
            return jsonify({"error": "CSV file not found"}), 404
        embedding_progress = {
            "stage": 0,
            "message": "Loading data and initializing embedding model",
            "timestamp": time.time()
        }
        
        JSON_DOI_MAPPED_FILE = filename.replace(".csv", "_paper_data_doi_mapped_hdbscan.json")
        JSON_DOI_MAPPED_FILE_PATH = os.path.join(DATA_FOLDER, JSON_DOI_MAPPED_FILE)

        METADATA_FILE = filename.replace(".csv", "_paper_chunk_metadata_hdbscan.json")
        METADATA_FILE_PATH = os.path.join(DATA_FOLDER, METADATA_FILE)

        FAISS_INDEX_FILE = filename.replace(".csv", "_paper_chunks_hdbscan.index")
        FAISS_INDEX_FILE_PATH = os.path.join(DATA_FOLDER, FAISS_INDEX_FILE)

        # Check if all files exist
        if os.path.exists(FAISS_INDEX_FILE_PATH) and os.path.exists(METADATA_FILE_PATH) and os.path.exists(JSON_DOI_MAPPED_FILE_PATH):
            embedding_progress = {
                "stage": 3,
                "message": "Embeddings already exist",
                "timestamp": time.time()
            }
            return jsonify({"message": "All files already exist"}), 200

        # --- EMBEDDING_MODEL ---
        EMBEDDING_MODEL = 'all-mpnet-base-v2'
        embedding_progress = {
            "stage": 1,
            "message": "Loading embedding model",
            "timestamp": time.time()
        }
        try:
            sentence_model = SentenceTransformer(EMBEDDING_MODEL)
        except Exception as e:
            embedding_progress = {
                "stage": -1,
                "message": "Failed to load embedding model",
                "timestamp": time.time()
            }
            return jsonify({"error": "Failed to load embedding model"}), 500

        embedding_progress = {
            "stage": 2,
            "message": "Processing data and generating embeddings",
            "timestamp": time.time()
        }
        
        # Use HDBSCAN chunking + split oversized chunks
        all_vectors, all_chunk_metadata = process_data_generate_vectors_and_metadata(csv_path, sentence_model)
        if all_vectors is None or all_chunk_metadata is None:
            embedding_progress = {
                "stage": -1,
                "message": "Failed to process data",
                "timestamp": time.time()
            }
            return jsonify({"error": "Failed to process data"}), 500
        # Build FAISS index
        faiss_index = build_faiss_index(all_vectors)
        if faiss_index is None:
            embedding_progress = {
                "stage": -1,
                "message": "Failed to build FAISS index",
                "timestamp": time.time()
            }
            return jsonify({"error": "Failed to build FAISS index"}), 500
        if faiss_index:
            try:
                faiss.write_index(faiss_index, FAISS_INDEX_FILE_PATH)
            except Exception as e:
                embedding_progress = {
                    "stage": -1,
                    "message": "Failed to save FAISS index",
                    "timestamp": time.time()
                }
                return jsonify({"error": "Failed to save FAISS index"}), 500
        if all_chunk_metadata:
            save_metadata_list(all_chunk_metadata, METADATA_FILE_PATH)
            save_doi_mapped_json(all_chunk_metadata, JSON_DOI_MAPPED_FILE_PATH)
        print(f"Metadata saved")
        embedding_progress = {
            "stage": 3,
            "message": "Embeddings created successfully",
            "timestamp": time.time()
        }
        end = time.time()
        app.logger.info(f"Embeddings created successfully in {end - start:.2f} seconds")
        return jsonify({"message": "Embeddings created successfully"}), 200
        
    except Exception as e:
        embedding_progress = {
            "stage": -1,
            "message": f"Error: {str(e)}",
            "timestamp": time.time()
        }
        return jsonify({"error": str(e)}), 500
   
        
# --- Chat Conversation Endpoint ---
@app.route("/chat_conversation/<filename>", methods=["POST"])
def chat_conversation(filename):
    # try:
    data = request.json
    query = data.get("query", "")
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400
    base_filename = filename.replace(".csv", "")
    FAISS_INDEX_FILE = f"{base_filename}_paper_chunks_hdbscan.index"
    FAISS_INDEX_FILE_PATH = os.path.join(DATA_FOLDER, FAISS_INDEX_FILE)
    METADATA_FILE = f"{base_filename}_paper_chunk_metadata_hdbscan.json"
    METADATA_FILE_PATH = os.path.join(DATA_FOLDER, METADATA_FILE)
    CSV_FILE = filename
    CSV_FILE_PATH = os.path.join(DATA_FOLDER, CSV_FILE)

    # Loading the embedding model
    EMBEDDING_MODEL = 'all-mpnet-base-v2'
    sentence_model = SentenceTransformer(EMBEDDING_MODEL)

    if FAISS_INDEX_FILE_PATH and METADATA_FILE_PATH and sentence_model:
        if llm is None:
            app.logger.error("LLM instance is None. Chat functionality will not work.")
            return jsonify({"error": "LLM instance is not initialized."}), 500
        
        try:
            faiss_index = faiss.read_index(FAISS_INDEX_FILE_PATH)
            with open(METADATA_FILE_PATH, 'r', encoding='utf-8') as f: all_chunk_metadata = json.load(f)
        except Exception as e:
            return jsonify({"error": "Failed to load metadata file"}), 500
        
        search_results = search_faiss(query, sentence_model, faiss_index, all_chunk_metadata, k= 5)

        if not search_results:
            app.logger.info("No relevant documents found for the query.")
            # Return the requested structure but indicate no results
            return jsonify({
                "paperTitles": [],
                "downloadUrls": [],
                "responseText": "I cannot answer the question based on the provided context, as no relevant documents were found."
            })
    
        if search_results:
            app.logger.info(f"Search results found: {len(search_results)}")
            # --- Process Search Results and Prepare Context ---
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
                        app.logger.warning(f"Could not map chunk to a unique paper: {title}")
                else:
                    assigned_index = 0 # Should not happen
                    app.logger.warning(f"DOI {doi} found in result but not in unique_papers map.")


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
            try:
                if os.path.exists(CSV_FILE_PATH):
                    app.logger.info(f"Reading CSV for URLs: {CSV_FILE_PATH}")
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
                        app.logger.warning(f"'Doi' or 'Download_URL' column not found in {CSV_FILE_PATH}.")
                        final_download_urls = ["URL lookup failed (Column missing)"] * len(final_paper_titles)

                else:
                    app.logger.warning(f"Original CSV file not found: {CSV_FILE_PATH}. Cannot fetch download URLs.")
                    final_download_urls = ["URL lookup failed (CSV not found)"] * len(final_paper_titles)
            
            except Exception as e:
                app.logger.error(f"Error reading or processing CSV {CSV_FILE_PATH} for URLs: {e}")
                final_download_urls = ["URL lookup failed (Error)"] * len(final_paper_titles)

            # llm prompt
            llm_prompt = f"""
    Your task is to answer the following question based ONLY on the context documents provided below.

    Instructions:
    - Answer the question solely using the information present in the 'Context Documents' section.
    - Do not use any external knowledge or prior assumptions.

    - **Paraphrase and Synthesize:**
        - **Do NOT copy sentences directly** from the context documents.
        - Rephrase the information accurately in your own words, preserving the original meaning.
        - Synthesize information from multiple sources where appropriate to provide a cohesive answer.

    - **Citation Requirements:**
        - You MUST cite the source(s) for every piece of information presented in your answer.
        - Use the index number provided in brackets (e.g., [1], [2]) corresponding to the source document listed in the 'Context Documents' (e.g., `[1] [Source Title: ...]`).
        - **Place the citation(s) ONLY at the end of the sentence, or at the end of a sequence of sentences, that are directly supported by that source(s).**
        - **Citation Placement Example:** If sentence A and sentence B are both based *only* on source [1], and sentence C is based *only* on source [4], the correct format is: "Sentence A. Sentence B.[1] Sentence C.[4]".
        - **Multiple Sources Example:** If a statement synthesizes information from sources [1] and [3], cite it as: "Synthesized statement.[1][3]".

    - **Clarity:** Define pronouns clearly (e.g., avoid ambiguous "it" or "they"). Refer back to specific entities mentioned in the context.
    - **Completeness:** Ensure all parts of the question are addressed if possible within the context.
    - **Unknown Answer:** If the answer cannot be found within the provided context documents, explicitly state: "I cannot answer the question based on the provided context."
    - **Conciseness:** Be direct and avoid unnecessary waffle.

    Context Documents:
    {llm_context_string}

    Question:
    {query}

    Answer (Paraphrased text based *only* on the context above. Citations MUST be placed at the end of the sentence or group of sentences they support, like sentence1. sentence2.[1] sentence3.[4]):
    """

            # --- Call LLM ---
            try:
                app.logger.info("Sending prompt to LLM.")
                # You might want to configure generation parameters (temperature, max output tokens, etc.)
                # response = llm.generate_content(llm_prompt, generation_config=genai.types.GenerationConfig(...))
                llm_response = llm.generate_content(llm_prompt)

                # Accessing the text might differ slightly depending on the library version
                # Check the structure of llm_response if .text doesn't work (e.g., might be llm_response.parts[0].text)
                if hasattr(llm_response, 'text'):
                    response_text = llm_response.text
                elif hasattr(llm_response, 'parts') and llm_response.parts:
                    response_text = llm_response.parts[0].text
                else:
                    # Fallback or error handling if response structure is unexpected
                    app.logger.error(f"Unexpected LLM response structure: {llm_response}")
                    response_text = "Error: Could not parse LLM response."


                app.logger.info(f"LLM response received.") # Avoid logging full response if sensitive/long

            except Exception as e:
                app.logger.error(f"Error calling LLM: {e}")
                return jsonify({"error": f"LLM generation failed: {e}"}), 500

            # --- Structure Final JSON Response ---
            final_response = {
                "paperTitles": final_paper_titles,
                "downloadUrls": final_download_urls,
                "responseText": response_text.strip() # Clean up whitespace
            }

            return jsonify(final_response)
  
if __name__ == "__main__":
    app.run(debug=True)