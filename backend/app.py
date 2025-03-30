from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import csv
import sys
from features.search import search_works, extract_and_save_to_csv
import shutil
import re

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

def sanitize_filename(filename):
    # Replace any non-alphanumeric characters (except spaces) with underscore
    return re.sub(r'[^a-zA-Z0-9\s]', '_', filename)

@app.route("/search", methods=["GET"])
def search():
    try:
        query = request.args.get("query", "")
        print(f"Received search query: {query}")
        if not query:
            return jsonify({"error": "Query parameter is required"}), 400

        # Clear the data folder
        if os.path.exists(DATA_FOLDER):
            for file in os.listdir(DATA_FOLDER):
                file_path = os.path.join(DATA_FOLDER, file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print(f"Error clearing file: {e}")

        results = search_works(query)
        if not results:
            return jsonify({"error": "No results found"}), 404

        # Sanitize the filename
        csv_filename = f'{sanitize_filename(query)}.csv'
        csv_path = os.path.join(DATA_FOLDER, csv_filename)
        extract_and_save_to_csv(results, csv_path)

        # Return initial results immediately
        return jsonify({
            "results": results[:10],
            "csv_filename": csv_filename,
            "total_results": len(results)
        })

    except Exception as e:
        print(f"Search error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/download/<filename>")
def download_csv(filename):
    try:
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
            chunk_size = 1000  # Process 1000 rows at a time
            chunk = []
            
            for row in reader:
                try:
                    paper = {
                        'source': str(row.get('Source', '')).strip() or 'Unknown',
                        'title': str(row.get('Title', '')).strip() or 'Unknown',
                        'download_url': str(row.get('Download_URL', '')).strip() or '',
                        'year': str(row.get('Year_Published', '')).strip() or 'Unknown'
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

if __name__ == "__main__":
    app.run(debug=True)
