# main.py in process-and-embed (Final version with robust chunking)
import functions_framework
from google.cloud import storage, firestore
import google.auth
import google.auth.transport.requests
import requests
import os
import re
import json

def chunk_text(text, chunk_size=1500, chunk_overlap=150):
    """Splits text into fixed-size, overlapping chunks."""
    if not text:
        return []
    
    words = text.split()
    chunks = []
    current_chunk_words = []
    
    for word in words:
        current_chunk_words.append(word)
        # Check if the current chunk is getting close to the size limit
        if len(" ".join(current_chunk_words)) > chunk_size:
            chunks.append(" ".join(current_chunk_words))
            # Create the overlap for the next chunk
            current_chunk_words = current_chunk_words[-chunk_overlap:]
            
    # Add the last remaining chunk
    if current_chunk_words:
        chunks.append(" ".join(current_chunk_words))
        
    return [c for c in chunks if c.strip()]

@functions_framework.cloud_event
def process_and_embed_gcs(cloud_event):
    PROJECT_ID = os.environ.get("GCLOUD_PROJECT")
    REGION = "us-central1"
    INDEX_ID = os.environ.get("INDEX_ID")
    FIRESTORE_COLLECTION = "health-chunks"

    credentials, project_id_from_auth = google.auth.default()
    if not PROJECT_ID: PROJECT_ID = project_id_from_auth
    
    storage_client = storage.Client()
    db = firestore.Client()
    
    data = cloud_event.data
    bucket_name = data["bucket"]
    file_name = data["name"]
    print(f"Processing file: {file_name} from bucket: {bucket_name}")
    
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    text_content = blob.download_as_text()
    
    chunks = chunk_text(text_content) # Use the new, better chunker
    print(f"Created {len(chunks)} text chunks.")

    # Get embeddings via REST
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    token = credentials.token
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}
    embedding_url = f"https://{REGION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{REGION}/publishers/google/models/text-embedding-004:predict"
    
    # Handle API limits by sending chunks in batches
    all_embeddings = []
    batch_size = 5 # The API has a limit on instances per request
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i:i + batch_size]
        instances = [{"content": chunk} for chunk in batch_chunks]
        response = requests.post(embedding_url, headers=headers, json={"instances": instances})
        response.raise_for_status()
        all_embeddings.extend([item['embeddings']['values'] for item in response.json()['predictions']])
    
    datapoints_to_upsert = []
    firestore_batch = db.batch()
    
    for i, (chunk, emb) in enumerate(zip(chunks, all_embeddings)):
        doc_id = f"{file_name}-{i}"
        datapoints_to_upsert.append({"datapoint_id": doc_id, "feature_vector": emb})
        doc_ref = db.collection(FIRESTORE_COLLECTION).document(doc_id)
        firestore_batch.set(doc_ref, {"text": chunk, "source": file_name})

    # Upsert to Vector Search
    upsert_url = f"https://{REGION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{REGION}/indexes/{INDEX_ID}:upsertDatapoints"
    response = requests.post(upsert_url, headers=headers, json={"datapoints": datapoints_to_upsert})
    response.raise_for_status()
    print(f"Successfully upserted {len(datapoints_to_upsert)} vectors to Index.")

    # Commit to Firestore
    firestore_batch.commit()
    print(f"Successfully saved {len(chunks)} chunks to Firestore.")