import pandas as pd
from sentence_transformers import SentenceTransformer
import hdbscan # <<< NEW IMPORT
from nltk.tokenize import sent_tokenize
import faiss
import numpy as np
import nltk
import os
import time
import json

# --- NLTK Download ---
try: nltk.data.find('tokenizers/punkt')
except nltk.downloader.DownloadError: print("Downloading nltk 'punkt' tokenizer..."); nltk.download('punkt')


# Chunking Parameters
CHUNK_MAX_TOKENS = 800 # Max tokens for FINAL chunks after splitting oversized ones
# HDBSCAN Parameters
HDBSCAN_MIN_CLUSTER_SIZE = 3 # Min sentences to form a dense cluster

# load csv file
def load_data(csv_filepath):
    """Loads the data from the CSV file."""
    print(f"Loading data from {csv_filepath}..."); start_time = time.time()
    try:
        df = pd.read_csv(csv_filepath); print(f"Data loaded in {time.time() - start_time:.2f} seconds.")
        if 'Full_Text' not in df.columns or 'Doi' not in df.columns or 'Title' not in df.columns: raise ValueError("CSV must contain 'Full_Text', 'Doi', 'Title'.")
        df['Full_Text'] = df['Full_Text'].fillna(''); df['Doi'] = df['Doi'].astype(str).fillna('Unknown DOI'); df['Title'] = df['Title'].fillna('Unknown Title')
        df['Reference'] = df['Reference'].fillna(''); df['Source'] = df['Source'].fillna(''); df['Year_Published'] = df['Year_Published'].fillna(0)
        return df
    except FileNotFoundError: print(f"ERROR: CSV file not found at {csv_filepath}"); exit()
    except ValueError as ve: print(f"ERROR in CSV data: {ve}"); exit()
    except Exception as e: print(f"ERROR loading data: {e}"); exit()

# --- Semantic Chunking Function (using HDBSCAN) ---
def semantic_chunking_hdbscan(text, sentence_model, min_cluster_size=HDBSCAN_MIN_CLUSTER_SIZE):
    """
    Perform semantic chunking by clustering similar sentences using HDBSCAN.
    Handles mixed key types for sorting.
    """
    if not text or not isinstance(text, str):
        return []

    try:
        sentences = sent_tokenize(text)
        if not sentences: return []
    except Exception as e:
        print(f"Error tokenizing sentences: {e}. Treating as one chunk.")
        return [text]

    if len(sentences) < min_cluster_size:
        return [text]

    try:
        embeddings = sentence_model.encode(sentences, show_progress_bar=False)
        embeddings = embeddings.astype('float32')
        faiss.normalize_L2(embeddings)
    except Exception as e:
        print(f"Error encoding sentences: {e}. Treating as one chunk.")
        return [text]

    try:
        clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, metric='euclidean', allow_single_cluster=True)
        labels = clusterer.fit_predict(embeddings)
    except Exception as e:
        print(f"Error during HDBSCAN clustering: {e}. Treating as one chunk.")
        return [text]

    # Group sentences by cluster labels
    chunks_dict = {}
    for i, (sentence, label) in enumerate(zip(sentences, labels)):
        # === FIX: Convert integer labels to strings for consistent sorting ===
        cluster_label = str(label) if label != -1 else f"noise_{i}"
        # ====================================================================
        if cluster_label not in chunks_dict:
            chunks_dict[cluster_label] = []
        chunks_dict[cluster_label].append(sentence)

    # Form chunks by concatenating sentences - sorted() now works on string keys
    # Sorting ensures chunks are roughly in original order (clusters first, then noise)
    try:
        # Sort keys numerically where possible, then alphabetically for 'noise_...'
        # This custom sort handles stringified numbers correctly.
        sorted_keys = sorted(chunks_dict.keys(), key=lambda k: int(k) if k.isdigit() or (k.startswith('-') and k[1:].isdigit()) else float('inf'))
        chunk_texts = [' '.join(chunks_dict[label]) for label in sorted_keys]

        # Alternative simpler sort (might mix noise points within number order slightly):
        # chunk_texts = [' '.join(chunks_dict[label]) for label in sorted(chunks_dict.keys())]

    except Exception as e:
         print(f"Error sorting cluster keys or joining chunks: {e}")
         # Fallback: process in arbitrary order if sorting fails
         chunk_texts = [' '.join(sentences) for sentences in chunks_dict.values()]


    return chunk_texts


# --- Function to split oversized chunks (> 'CHUNK_MAX_TOKENS') ---
def split_oversized_chunks(chunks: list, max_tokens: int = CHUNK_MAX_TOKENS):
    """
    Splits chunks that exceed the max_tokens limit based on sentence boundaries.

    Args:
        chunks (list): List of text chunks (potentially oversized).
        max_tokens (int): The maximum desired token count (word count) per chunk.

    Returns:
        list: List of chunks, none exceeding max_tokens (unless a single sentence is too long).
    """
    final_chunks = []
    for chunk in chunks:
        chunk_tokens = len(chunk.split())
        if chunk_tokens <= max_tokens:
            final_chunks.append(chunk)
        else:
            # Chunk is too long, split by sentences
            print(f"  Oversized chunk detected ({chunk_tokens} tokens), splitting by sentence...")
            try:
                sentences = sent_tokenize(chunk)
            except Exception as e:
                print(f"    Error tokenizing oversized chunk: {e}. Keeping as is.")
                final_chunks.append(chunk) # Keep original if sentences can't be found
                continue

            current_sub_chunk_sentences = []
            current_sub_chunk_tokens = 0
            for sentence in sentences:
                sentence_tokens = len(sentence.split())
                # Handle single sentences that are too long
                if sentence_tokens > max_tokens:
                    # Add previous sub-chunk if exists
                    if current_sub_chunk_sentences:
                        final_chunks.append(" ".join(current_sub_chunk_sentences))
                    # Add the long sentence as its own chunk
                    final_chunks.append(sentence)
                    print(f"    Warning: Single sentence within oversized chunk exceeds max tokens ({sentence_tokens}/{max_tokens}).")
                    current_sub_chunk_sentences = [] # Reset
                    current_sub_chunk_tokens = 0
                    continue

                # If adding sentence fits, add it
                if current_sub_chunk_tokens + sentence_tokens <= max_tokens:
                    current_sub_chunk_sentences.append(sentence)
                    current_sub_chunk_tokens += sentence_tokens
                # If adding sentence doesn't fit, finalize previous sub-chunk and start new one
                else:
                    if current_sub_chunk_sentences: # Should always have something unless first sentence was too long
                        final_chunks.append(" ".join(current_sub_chunk_sentences))
                    current_sub_chunk_sentences = [sentence]
                    current_sub_chunk_tokens = sentence_tokens

            # Add the last sub-chunk being built
            if current_sub_chunk_sentences:
                final_chunks.append(" ".join(current_sub_chunk_sentences))

    return [c for c in final_chunks if c.strip()] # Ensure no empty strings


# --- Data Processing Function ---
def process_data_generate_vectors_and_metadata(csv_path: str, sentence_model):
    """
    Loads CSV, chunks text using HDBSCAN + splits oversized chunks,
    generates embeddings. Returns lists of vectors and metadata.
    """
    df = load_data(csv_path)
    print("Processing data, chunking (HDBSCAN + Split), and generating embeddings...")
    all_vectors = []; all_chunk_metadata = []
    start_time = time.time()
    doc_chunk_counter = {}

    for index, row in df.iterrows():
        doi = str(row.get('Doi', 'Unknown DOI')); full_text = row.get('Full_Text', '')
        if not full_text.strip(): continue

        # 1. Perform HDBSCAN semantic chunking
        hdbscan_chunks = semantic_chunking_hdbscan(full_text, sentence_model)
        if not hdbscan_chunks: continue

        # 2. Split any chunks that are too long
        final_chunks = split_oversized_chunks(hdbscan_chunks, max_tokens=CHUNK_MAX_TOKENS)
        if not final_chunks: continue

        # Reset chunk counter for new document
        doc_chunk_counter[doi] = 0

        # 3. Generate embeddings for the FINAL chunks
        try: chunk_embeddings = sentence_model.encode(final_chunks, show_progress_bar=False)
        except Exception as e: print(f"Error embedding final chunks for DOI {doi}: {e}"); continue

        # 4. Store vectors and metadata
        for chunk in final_chunks:
            vector = chunk_embeddings[doc_chunk_counter[doi]]
            metadata = {
                "text": chunk, "paperTitle": str(row.get('Title', '')), "doi": doi,
                "source": str(row.get('Source', '')),
                "yearPublished": int(row.get('Year_Published', 0)) if pd.notna(row.get('Year_Published')) else 0,
                "chunk_index_in_doc": doc_chunk_counter[doi] # Index relative to final chunks of this doc
            }
            all_vectors.append(vector); all_chunk_metadata.append(metadata)
            doc_chunk_counter[doi] += 1

        if (index + 1) % 50 == 0: print(f"  Processed {index + 1}/{len(df)} papers...")

    print(f"Data processing finished in {time.time() - start_time:.2f} seconds.")
    if not all_vectors: print("No vectors were generated."); return None, None
    if len(all_vectors) != len(all_chunk_metadata):
        print(f"ERROR: Mismatch vector count ({len(all_vectors)}) vs metadata count ({len(all_chunk_metadata)})."); return None, None
    return np.array(all_vectors).astype('float32'), all_chunk_metadata


# --- Function to build FAISS index ---
def build_faiss_index(vectors: np.ndarray, index_type='IndexHNSWFlat'):
    if vectors is None or vectors.ndim != 2: raise ValueError(f"Input vectors must be 2D numpy array.")
    if vectors.shape[0] == 0: print("No vectors to index."); return None
    dimension = vectors.shape[1]; print(f"Building FAISS index of type '{index_type}' with dim {dimension} for {vectors.shape[0]} vectors...")
    start_time = time.time()
    if index_type == 'IndexFlatL2': index = faiss.IndexFlatL2(dimension)
    elif index_type == 'IndexHNSWFlat':
        M = 48; efConstruction = 512; index = faiss.IndexHNSWFlat(dimension, M, faiss.METRIC_L2); index.hnsw.efConstruction = efConstruction
        print(f"  Using HNSW parameters: M={M}, efConstruction={efConstruction}")
    else: raise ValueError(f"Unsupported FAISS index type: {index_type}")
    index.add(vectors); print(f"FAISS index built in {time.time() - start_time:.2f} seconds.")
    return index


# --- Function to save JSON/Metadata ---
def save_metadata_list(metadata_list: list, output_path: str):
    print(f"Saving chunk metadata list to {output_path}...")
    try:
        with open(output_path, 'w', encoding='utf-8') as f: json.dump(metadata_list, f, indent=4, ensure_ascii=False)
        print("Metadata list saved successfully.")
    except Exception as e: print(f"Error saving metadata list: {e}")
def save_doi_mapped_json(metadata_list: list, output_path: str):
    print(f"Constructing and saving DOI-mapped data to {output_path}...")
    data_for_json = {}
    for i, metadata in enumerate(metadata_list):
        doi = metadata.get('doi', 'Unknown DOI')
        if doi not in data_for_json: data_for_json[doi] = []
        data_for_json[doi].append({
            "chunk": metadata.get('text', ''),
            "metadata": {k: v for k, v in metadata.items() if k not in ['text', 'distance']}
        })
    try:
        with open(output_path, 'w', encoding='utf-8') as f: json.dump(data_for_json, f, indent=4, ensure_ascii=False)
        print("DOI-mapped data saved successfully.")
    except Exception as e: print(f"Error saving DOI-mapped data: {e}")

# --- FAISS Search Function ---
def search_faiss(query: str, sentence_model, index: faiss.Index, metadata_list: list, k: int = 5):
    """ Searches FAISS index and returns metadata of top k results. """
    if index is None: print("FAISS index is not available."); return []
    if not metadata_list: print("Metadata list is empty."); return []
    print(f"\nSearching for top {k} results for query: '{query}'"); start_time = time.time()
    try: query_vector = sentence_model.encode([query]).astype('float32'); print(f"  Query vector shape: {query_vector.shape}")
    except Exception as e: print(f"Error encoding query: {e}"); return []
    try: distances, indices = index.search(query_vector, k)
    except Exception as e: print(f"Error searching FAISS index: {e}"); return []
    print(f"Search completed in {time.time() - start_time:.2f} seconds.")
    results = []
    if indices.size > 0:
        for i, idx in enumerate(indices[0]):
            if idx != -1 and 0 <= idx < len(metadata_list):
                result_metadata = metadata_list[idx].copy(); result_metadata['distance'] = distances[0][i]
                results.append(result_metadata)
    return results
