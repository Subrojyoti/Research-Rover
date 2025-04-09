from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import os
import csv
import sys
from features.search import search_works, extract_and_save_to_csv
from features.download_pdfs import download_pdfs_from_csv
import shutil
import re
import time

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

def sanitize_filename(filename):
    # Replace any non-alphanumeric characters (except spaces) with underscore
    return re.sub(r'[^a-zA-Z0-9\s]', '_', filename)

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

@app.route("/download/<filename>")
def download_csv(filename):
    try:
        filename =f"_".join(filename.split("%20"))
        return send_from_directory(DATA_FOLDER, filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({"error": "File not found"}), 404

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

if __name__ == "__main__":
    app.run(debug=True)