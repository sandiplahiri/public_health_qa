# main.py in scrape-cdc (Final Version with Lazy Initialization)
import functions_framework
import requests
from bs4 import BeautifulSoup
from google.cloud import storage
import os

# Environment variable for the bucket name
BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME")

# List of URLs to scrape
URL_LIST = {
    "keyfacts": "https://www.cdc.gov/flu/about/?CDC_AAref_Val=https://www.cdc.gov/flu/about/keyfacts.htm",
    "prevention": "https://www.cdc.gov/flu/prevention/?CDC_AAref_Val=https://www.cdc.gov/flu/prevent/prevention.htm"
}

@functions_framework.http
def scrape_cdc_http(request):
    """
    Scrapes CDC pages and saves content to GCS.
    Initializes the client inside the function for robust startup.
    """
    if not BUCKET_NAME:
        return "GCS_BUCKET_NAME environment variable not set.", 500

    # --- LAZY INITIALIZATION ---
    # Initialize the client inside the function handler
    storage_client = storage.Client()
    # --- END INITIALIZATION ---

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }
    
    successful_scrapes = []
    failed_scrapes = []

    for name, url in URL_LIST.items():
        try:
            print(f"Scraping {name} from {url}...")
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            main_content = soup.find('div', attrs={'role': 'main'})
            text_content = main_content.get_text(separator='\n', strip=True) if main_content else soup.body.get_text(separator='\n', strip=True)

            bucket = storage_client.bucket(BUCKET_NAME)
            blob_name = f"cdc-flu-{name}.txt" # Use stable filename
            blob = bucket.blob(blob_name)
            blob.upload_from_string(text_content, content_type="text/plain")
            
            print(f"Successfully scraped and uploaded to gs://{BUCKET_NAME}/{blob_name}")
            successful_scrapes.append(name)
        except Exception as e:
            print(f"Error processing {name}: {e}")
            failed_scrapes.append(name)
            continue
    
    return f"Scraping complete. Success: {successful_scrapes}. Failed: {failed_scrapes}.", 200