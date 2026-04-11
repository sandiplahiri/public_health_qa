# main.py in rag-webhook (Final, Corrected Host Version)
import functions_framework
import google.auth
import google.auth.transport.requests
import requests
import os
import json
import os, json, requests, functools
from typing import Dict, List, Tuple, Any
from google.auth.transport.requests import Request as GARequest
import json, traceback, requests
from google.cloud import firestore
import traceback



PROJECT_ID         = os.environ.get("PROJECT_ID", "rag-healthcare-1")
REGION             = os.environ.get("REGION", "us-central1")
INDEX_ENDPOINT_ID  = os.environ.get("INDEX_ENDPOINT_ID", "")    # 1785697043461701632
DEPLOYED_INDEX_ID     = os.environ.get("DEPLOYED_INDEX_ID", "")    # "public_health_index_1755901296871"    
INDEX_ENDPOINT_DOMAIN = os.environ.get("INDEX_ENDPOINT_DOMAIN", "")  # "1676906031.us-central1-211273875918.vdb.vertexai.goog"
TIMEOUT_SEC           = int(os.environ.get("TIMEOUT_SEC", "20"))
FIRESTORE_COLLECTION  = os.environ.get("FIRESTORE_COLLECTION", "") # "health-chunks"


@functions_framework.http
def dialogflow_rag_webhook(request):
    request_json = request.get_json(silent=True)
    user_query = request_json.get('text', '')

    if not user_query:
        return build_dialogflow_response("I'm sorry, I didn't understand the question.")
    
    try:
        PROJECT_ID = os.environ.get("GCLOUD_PROJECT")
        REGION = "us-central1"
        
        db = firestore.Client()

        credentials, project_id_from_auth = google.auth.default()
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)
        token = credentials.token
        if not PROJECT_ID:
            PROJECT_ID = project_id_from_auth
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        }

        # 1. Embed the user's query (this uses the standard AI Platform host)
        embedding_url = f"https://{REGION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{REGION}/publishers/google/models/text-embedding-004:predict"
        response = requests.post(embedding_url, headers=headers, json={"instances": [{"content": user_query}]})
        response.raise_for_status()
        query_embedding = response.json()['predictions'][0]['embeddings']['values']

        # 2. Query Vector Search to find neighbor IDs
        find_neighbors_url = f"https://{INDEX_ENDPOINT_DOMAIN}/v1/projects/{PROJECT_ID}/locations/{REGION}/indexEndpoints/{INDEX_ENDPOINT_ID}:findNeighbors"
        query_payload = {
            "deployedIndexId": DEPLOYED_INDEX_ID,
            "queries": [{"neighborCount": 3, "datapoint": {"featureVector": query_embedding}}]
        }
        response = requests.post(find_neighbors_url, headers=headers, json=query_payload)
        response.raise_for_status()
        
        context = ""
        nearest_neighbors_list = response.json().get('nearestNeighbors', [])
       
        # 3: Retrieve actual text from Firestore
        if nearest_neighbors_list and nearest_neighbors_list[0].get('neighbors'):
            neighbors = nearest_neighbors_list[0]['neighbors']
            neighbor_ids = [n['datapoint']['datapointId'] for n in neighbors]
            
            db = firestore.Client()
            doc_refs = [db.collection(FIRESTORE_COLLECTION).document(doc_id) for doc_id in neighbor_ids]
            docs = db.get_all(doc_refs)
            
            retrieved_texts = [doc.to_dict().get('text', '') for doc in docs if doc.exists]
            # De-duplicate the retrieved text 
            unique_texts = list(dict.fromkeys(retrieved_texts)) # This removes duplicates while preserving order
            context = "\n---\n".join(unique_texts)

        if not context:
            return build_dialogflow_response("I'm sorry, I couldn't find any relevant information in our documents.")


        # 4. Call Gemini with the clean, de-duplicated context
        prompt = f"Using the following context, answer the user's question.\nContext: {context}\nQuestion: {user_query}"
        gemini_url = f"https://{REGION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{REGION}/publishers/google/models/gemini-2.5-flash:generateContent"
        gemini_payload = { "contents": [{
            "role": "user",
            "parts": [{"text": prompt}]
        }]}
        
        response = requests.post(gemini_url, headers=headers, json=gemini_payload)
        response.raise_for_status()
        final_answer = response.json()['candidates'][0]['content']['parts'][0]['text']

    except Exception as e:
        print(f"ERROR IN RAG WEBHOOK PIPELINE: {e}")
        traceback.print_exc()
        final_answer = "I'm sorry, an error occurred while processing your request."

    return build_dialogflow_response(final_answer)

def build_dialogflow_response(text_response):
    """
    Return just one message and force replacement. That is,
      o Tell Dialogflow to completely ignore any static responses configured in the agent's UI (for example $session.params.response_text)
      o Instruct the agent to replace these entirely with the messages being sent directly from this webhook
    """
    response = {
        "fulfillment_response": {
        "merge_behavior": "REPLACE",
        "messages": [
            { "text": { "text": [text_response] } }
            ]
        },
        "session_info": { "parameters": { "response_text": text_response } }
    }

    return json.dumps(response), 200, {'Content-Type': "application/json"}