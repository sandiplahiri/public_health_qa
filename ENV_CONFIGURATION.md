# Environment Configuration Guide

## Overview
All hardcoded configuration values have been moved to a `.env` file to improve security and maintainability.

## Files Modified
- `scrape_cdc/main.py` - Added dotenv loading and environment variable references
- `process_and_embed/main.py` - Added dotenv loading and environment variable references  
- `rag_webhook/main.py` - Added dotenv loading and environment variable references
- `scrape_cdc/requirements.txt` - Added python-dotenv
- `process_and_embed/requirements.txt` - Added python-dotenv
- `rag_webhook/requirements.txt` - Added python-dotenv

## Configuration Variables

### GCS & Google Cloud
- `GCS_BUCKET_NAME` - Google Cloud Storage bucket name
- `GCLOUD_PROJECT` - Google Cloud project ID
- `PROJECT_ID` - Project ID (fallback)
- `REGION` - Google Cloud region (default: `us-central1`)

### Vector Search
- `INDEX_ID` - Vertex AI Vector Search index ID
- `INDEX_ENDPOINT_ID` - Vector search index endpoint ID
- `DEPLOYED_INDEX_ID` - Deployed index ID
- `INDEX_ENDPOINT_DOMAIN` - Index endpoint domain/host

### Firestore
- `FIRESTORE_COLLECTION` - Firestore collection name (default: `health-chunks`)

### CDC Scraping
- `CDC_KEYFACTS_URL` - CDC flu keyfacts URL
- `CDC_PREVENTION_URL` - CDC flu prevention URL
- `USER_AGENT` - HTTP User-Agent header for scraping
- `CDC_BLOB_PREFIX` - Prefix for blob filenames (default: `cdc-flu-`)

### Text Processing
- `CHUNK_SIZE` - Text chunk size in characters (default: `1500`)
- `CHUNK_OVERLAP` - Overlap between chunks (default: `150`)
- `EMBEDDING_BATCH_SIZE` - Batch size for embeddings API (default: `5`)

### RAG Webhook
- `NEIGHBOR_COUNT` - Number of vector neighbors to retrieve (default: `3`)
- `TIMEOUT_SEC` - Request timeout in seconds (default: `20`)

## Setup Instructions

1. **Copy the template file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your actual values:**
   ```bash
   # Replace placeholder values with your actual configuration
   GCS_BUCKET_NAME=my-actual-bucket
   PROJECT_ID=my-project-id
   # ... etc
   ```

3. **Install dependencies:**
   Each module now includes `python-dotenv==1.0.0` in requirements.txt
   ```bash
   pip install -r scrape_cdc/requirements.txt
   pip install -r process_and_embed/requirements.txt
   pip install -r rag_webhook/requirements.txt
   ```

4. **Verify environment variables are loaded:**
   The `load_dotenv()` call at the start of each module will automatically load variables from `.env`

## Security Best Practices

- **Never commit `.env` to version control**
- Keep `.env.example` committed as a template for developers
- Add `.env` to `.gitignore` if not already present
- Use `.env.example` to document all required variables
- For production, use Google Cloud Secret Manager or similar services

## Environment Variable Precedence

The code respects the following precedence for environment variables:
1. System environment variables (highest priority)
2. Variables from `.env` file
3. Hardcoded defaults in the code (lowest priority)

This allows overriding values at deployment time while providing sensible defaults.
