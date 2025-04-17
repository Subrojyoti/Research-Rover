import pandas as pd
from sentence_transformers import SentenceTransformer
import hdbscan
from nltk.tokenize import sent_tokenize
import faiss
import numpy as np
import nltk
import os
import time
import json

# --- NLTK Download ---
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    print("Downloading nltk 'punkt' tokenizer...")
    nltk.download('punkt')

# Chunking Parameters
CHUNK_MAX_TOKENS = 800  # Max tokens for FINAL chunks after splitting oversized ones
# HDBSCAN Parameters
HDBSCAN_MIN_CLUSTER_SIZE = 3  # Min sentences to form a dense cluster

# Load CSV file
def load_data(csv_filepath):
    """Loads the data from the CSV file."""
    print(f"Loading data from {csv_filepath}...")
    start_time = time.time()
    try:
        df = pd.read_csv(csv_filepath)
        print(f"Data loaded in {time.time() - start_time:.2f} seconds.")
        if 'Full_Text' not in df.columns or 'Doi' not in df.columns or 'Title' not in df.columns:
            raise ValueError("CSV must contain 'Full_Text', 'Doi', 'Title'.")
        df['Full_Text'] = df['Full_Text'].fillna('')
        df['Doi'] = df['Doi'].astype(str).fillna('Unknown DOI')
        df['Title'] = df['Title'].fillna('Unknown Title')
        df['Reference'] = df['Reference'].fillna('')
        df['Source'] = df['Source'].fillna('')
        df['Year_Published'] = df['Year_Published'].fillna(0)
        return df
    except FileNotFoundError:
        print(f"ERROR: CSV file not found at {csv_filepath}")
        exit()
    except ValueError as ve:
        print(f"ERROR in CSV data: {ve}")
        exit()
    except Exception as e:
        print(f"ERROR loading data: {e}")
        exit()

# --- Semantic Chunking Function (using HDBSCAN) ---
def semantic_chunking_hdbscan(sentences: list, embeddings: np.ndarray, min_cluster_size=HDBSCAN_MIN_CLUSTER_SIZE):
    """
    Perform semantic chunking by clustering sentence embeddings with HDBSCAN.
    Returns lists of sentence indices for each chunk.
    """
    if len(sentences) < min_cluster_size:
        return [list(range(len(sentences)))]  # Single chunk with all sentence indices
    
    try:
        clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, metric='euclidean', allow_single_cluster=True)
        labels = clusterer.fit_predict(embeddings)
    except Exception as e:
        print(f"Error during HDBSCAN clustering: {e}. Treating as one chunk.")
        return [list(range(len(sentences)))]
    
    # Group sentence indices by cluster labels
    chunks_dict = {}
    for i, label in enumerate(labels):
        cluster_label = str(label) if label != -1 else f"noise_{i}"
        if cluster_label not in chunks_dict:
            chunks_dict[cluster_label] = []
        chunks_dict[cluster_label].append(i)
    
    # Sort clusters for consistency
    sorted_keys = sorted(chunks_dict.keys(), key=lambda k: int(k) if k.isdigit() or (k.startswith('-') and k[1:].isdigit()) else float('inf'))
    chunk_indices_lists = [chunks_dict[label] for label in sorted_keys]
    return chunk_indices_lists  # List of lists: each sublist is a chunk's sentence indices

# --- Function to split oversized chunks (> 'CHUNK_MAX_TOKENS') ---
def split_oversized_sentence_chunks(chunk_indices_lists: list, sentences: list, max_tokens: int = CHUNK_MAX_TOKENS):
    """
    Splits chunks exceeding max_tokens into smaller chunks, returning sentence indices.
    """
    final_chunks = []
    for chunk_indices in chunk_indices_lists:
        chunk_tokens = sum(len(sentences[i].split()) for i in chunk_indices)
        if chunk_tokens <= max_tokens:
            final_chunks.append(chunk_indices)
        else:
            print(f"  Oversized chunk detected ({chunk_tokens} tokens), splitting by sentence...")
            current_sub_chunk_indices = []
            current_tokens = 0
            for idx in chunk_indices:
                sentence_tokens = len(sentences[idx].split())
                if current_tokens + sentence_tokens > max_tokens:
                    if current_sub_chunk_indices:
                        final_chunks.append(current_sub_chunk_indices)
                    if sentence_tokens > max_tokens:
                        print(f"   Warning: Single sentence exceeds max tokens ({sentence_tokens}/{max_tokens}).")
                        final_chunks.append([idx])
                    else:
                        current_sub_chunk_indices = [idx]
                        current_tokens = sentence_tokens
                else:
                    current_sub_chunk_indices.append(idx)
                    current_tokens += sentence_tokens
            if current_sub_chunk_indices:
                final_chunks.append(current_sub_chunk_indices)
    return [c for c in final_chunks if c]  # Remove empty chunks

# --- Data Processing Function ---
def process_data_generate_vectors_and_metadata(csv_path: str, sentence_model):
    """
    Loads CSV, chunks text using HDBSCAN, splits oversized chunks,
    generates embeddings by reusing sentence embeddings. Returns vectors and metadata.
    """
    df = load_data(csv_path)
    print("Processing data, chunking (HDBSCAN + Split), and generating embeddings...")
    all_vectors = []
    all_chunk_metadata = []
    start_time = time.time()
    doc_chunk_counter = {}

    for index, row in df.iterrows():
        doi = str(row.get('Doi', 'Unknown DOI'))
        full_text = row.get('Full_Text', '')
        if not full_text.strip():
            continue

        # Tokenize sentences
        try:
            sentences = sent_tokenize(full_text)
            if not sentences:
                continue
        except Exception as e:
            print(f"Error tokenizing sentences for DOI {doi}: {e}. Skipping.")
            continue

        # Encode all sentences once
        try:
            sentence_embeddings = sentence_model.encode(sentences, show_progress_bar=False, batch_size=64)  # Adjust batch_size as needed
            sentence_embeddings = sentence_embeddings.astype('float32')
            faiss.normalize_L2(sentence_embeddings)  # Normalize for clustering consistency
        except Exception as e:
            print(f"Error encoding sentences for DOI {doi}: {e}. Skipping.")
            continue

        # Perform HDBSCAN chunking with precomputed embeddings
        chunk_indices_lists = semantic_chunking_hdbscan(sentences, sentence_embeddings)
        if not chunk_indices_lists:
            continue

        # Split oversized chunks
        final_chunk_indices_lists = split_oversized_sentence_chunks(chunk_indices_lists, sentences)
        if not final_chunk_indices_lists:
            continue

        # Reset chunk counter for new document
        doc_chunk_counter[doi] = 0

        # Generate embeddings for final chunks by averaging sentence embeddings
        for chunk_indices in final_chunk_indices_lists:
            if not chunk_indices:
                continue
            # Compute chunk embedding as the mean of its sentence embeddings
            chunk_embedding = np.mean(sentence_embeddings[chunk_indices], axis=0)
            chunk_text = " ".join([sentences[i] for i in chunk_indices])
            metadata = {
                "text": chunk_text,
                "paperTitle": str(row.get('Title', '')),
                "doi": doi,
                "source": str(row.get('Source', '')),
                "yearPublished": int(row.get('Year_Published', 0)) if pd.notna(row.get('Year_Published')) else 0,
                "chunk_index_in_doc": doc_chunk_counter[doi]
            }
            all_vectors.append(chunk_embedding)
            all_chunk_metadata.append(metadata)
            doc_chunk_counter[doi] += 1

        if (index + 1) % 50 == 0:
            print(f"  Processed {index + 1}/{len(df)} papers...")

    print(f"Data processing finished in {time.time() - start_time:.2f} seconds.")
    if not all_vectors:
        print("No vectors were generated.")
        return None, None
    if len(all_vectors) != len(all_chunk_metadata):
        print(f"ERROR: Mismatch vector count ({len(all_vectors)}) vs metadata count ({len(all_chunk_metadata)}).")
        return None, None
    return np.array(all_vectors).astype('float32'), all_chunk_metadata

# --- Function to build FAISS index ---
def build_faiss_index(vectors: np.ndarray, index_type='IndexHNSWFlat'):
    if vectors is None or vectors.ndim != 2:
        raise ValueError("Input vectors must be 2D numpy array.")
    if vectors.shape[0] == 0:
        print("No vectors to index.")
        return None
    dimension = vectors.shape[1]
    print(f"Building FAISS index of type '{index_type}' with dim {dimension} for {vectors.shape[0]} vectors...")
    start_time = time.time()
    if index_type == 'IndexFlatL2':
        index = faiss.IndexFlatL2(dimension)
    elif index_type == 'IndexHNSWFlat':
        M = 48
        efConstruction = 512
        index = faiss.IndexHNSWFlat(dimension, M, faiss.METRIC_L2)
        index.hnsw.efConstruction = efConstruction
        print(f"  Using HNSW parameters: M={M}, efConstruction={efConstruction}")
    else:
        raise ValueError(f"Unsupported FAISS index type: {index_type}")
    index.add(vectors)
    print(f"FAISS index built in {time.time() - start_time:.2f} seconds.")
    return index

# --- Function to save JSON/Metadata ---
def save_metadata_list(metadata_list: list, output_path: str):
    print(f"Saving chunk metadata list to {output_path}...")
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata_list, f, indent=4, ensure_ascii=False)
        print("Metadata list saved successfully.")
    except Exception as e:
        print(f"Error saving metadata list: {e}")

def save_doi_mapped_json(metadata_list: list, output_path: str):
    print(f"Constructing and saving DOI-mapped data to {output_path}...")
    data_for_json = {}
    for i, metadata in enumerate(metadata_list):
        doi = metadata.get('doi', 'Unknown DOI')
        if doi not in data_for_json:
            data_for_json[doi] = []
        data_for_json[doi].append({
            "chunk": metadata.get('text', ''),
            "metadata": {k: v for k, v in metadata.items() if k not in ['text', 'distance']}
        })
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data_for_json, f, indent=4, ensure_ascii=False)
        print("DOI-mapped data saved successfully.")
    except Exception as e:
        print(f"Error saving DOI-mapped data: {e}")

# --- FAISS Search Function ---
def search_faiss(query: str, sentence_model, index: faiss.Index, metadata_list: list, k: int = 5):
    """ Searches FAISS index and returns metadata of top k results. """
    if index is None:
        print("FAISS index is not available.")
        return []
    if not metadata_list:
        print("Metadata list is empty.")
        return []
    print(f"\nSearching for top {k} results for query: '{query}'")
    start_time = time.time()
    try:
        query_vector = sentence_model.encode([query]).astype('float32')
        print(f"  Query vector shape: {query_vector.shape}")
    except Exception as e:
        print(f"Error encoding query: {e}")
        return []
    try:
        distances, indices = index.search(query_vector, k)
    except Exception as e:
        print(f"Error searching FAISS index: {e}")
        return []
    print(f"Search completed in {time.time() - start_time:.2f} seconds.")
    results = []
    if indices.size > 0:
        for i, idx in enumerate(indices[0]):
            if idx != -1 and 0 <= idx < len(metadata_list):
                result_metadata = metadata_list[idx].copy()
                result_metadata['distance'] = distances[0][i]
                results.append(result_metadata)
    return results