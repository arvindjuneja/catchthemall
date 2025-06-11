import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import io
import numpy as np
import re
from scipy.spatial.distance import cdist

# Important: We need to be able to import from the embeddings script
from pokemon_clip_embeddings import PokemonCLIPProcessor

# --- New Imports ---
try:
    import easyocr
except ImportError:
    print("EasyOCR not found. Please run 'pip install easyocr'")
    easyocr = None

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Globals ---
app = Flask(__name__)
CORS(app)

# --- Load Models and Data ---
try:
    logger.info("🚀 Initializing server...")
    
    # Initialize the CLIP processor
    clip_processor = PokemonCLIPProcessor(model_name="ViT-B/32")
    
    # Load the search index
    image_type = "large"
    model_name_slug = clip_processor.model_name
    index_file = clip_processor.embeddings_dir / f"search_index_{image_type}_{model_name_slug}.pkl"
    
    if index_file.exists():
        logger.info(f"🔍 Loading search index from: {index_file}")
        import pickle
        with open(index_file, 'rb') as f:
            search_index = pickle.load(f)
        logger.info("✅ Search index loaded successfully.")
    else:
        logger.error("🚨 Search index not found! Please run the embedding script first.")
        search_index = None

    # --- Initialize OCR Reader ---
    if easyocr:
        logger.info("🔍 Initializing OCR Reader...")
        ocr_reader = easyocr.Reader(['en'])
        logger.info("✅ OCR Reader initialized.")
    else:
        ocr_reader = None

except Exception as e:
    logger.exception("💥 Failed to initialize server models.")
    clip_processor = None
    search_index = None
    ocr_reader = None

# --- Helper Functions ---
def clean_text(text):
    return re.sub(r'[^a-zA-Z0-9]', '', text).lower()

def get_full_card_details(card_id, processor):
    return next((card for card in processor.all_cards if card['id'] == card_id), None)

# --- API Endpoints ---
@app.route('/api/scan', methods=['POST'])
def scan_card():
    if 'card_image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    if not all([clip_processor, search_index, ocr_reader]):
        return jsonify({'error': 'Server not initialized properly. Check logs.'}), 500

    file = request.files['card_image']
    
    try:
        image_bytes = file.read()
        img_np = np.array(Image.open(io.BytesIO(image_bytes)))
        
        logger.info("📸 Received image, beginning scan with new 'Multi-Factor Scoring' logic...")

        # --- Stage 1: OCR Text Recognition ---
        ocr_results = ocr_reader.readtext(img_np, detail=0, paragraph=False)
        # Clean and get unique texts, prioritizing longer ones
        detected_texts = sorted(list(set([clean_text(t) for t in ocr_results])), key=len, reverse=True)
        raw_ocr_text = " ".join(ocr_results)
        logger.info(f"🧐 OCR detected {len(detected_texts)} unique text fragments.")

        # --- Stage 2: Extract Key Information from OCR ---
        # Find card numbers like "049/182" or "49/182"
        card_number_matches = re.findall(r'(\d+)\s*/\s*(\d+)', raw_ocr_text)
        logger.info(f"🔢 Found potential card numbers: {card_number_matches}")

        # --- Stage 3: Score all cards in the index ---
        card_scores = []
        for i, indexed_meta in enumerate(search_index['metadata']):
            score = 0
            full_card_details = get_full_card_details(indexed_meta['card_id'], clip_processor)
            if not full_card_details:
                continue

            # Check 1: Card Number Match (Highest Priority)
            if card_number_matches:
                card_num = full_card_details.get('number')
                set_total = full_card_details.get('set', {}).get('printedTotal')
                for ocr_num, ocr_total in card_number_matches:
                    if str(card_num) == str(ocr_num) and str(set_total) == str(ocr_total):
                        score += 100
                        logger.info(f"💥 Number Match! +100 for {full_card_details['name']}")
                        break
            
            # Check 2: Name Match
            card_name_clean = clean_text(full_card_details.get('name', ''))
            for text in detected_texts:
                if len(text) >= 4 and (text in card_name_clean or card_name_clean in text):
                    score += 20
                    break # Only score name once

            # Check 3: Attack Name Match
            if 'attacks' in full_card_details:
                for attack in full_card_details['attacks']:
                    attack_name_clean = clean_text(attack.get('name', ''))
                    if attack_name_clean and any(attack_name_clean in t for t in detected_texts):
                        score += 10
            
            if score > 0:
                card_scores.append({'score': score, 'index': i, 'meta': indexed_meta})
        
        if not card_scores:
            logger.warning("No cards scored > 0. Falling back to pure image search.")
            # Fallback logic here if needed, or just return no match
            return jsonify({'error': 'Could not find a matching card.'}), 404

        # --- Stage 4: Determine the best match ---
        card_scores.sort(key=lambda x: x['score'], reverse=True)
        logger.info(f"🏆 Top 3 candidates: " + ", ".join([f"{c['meta']['name']} ({c['score']})" for c in card_scores[:3]]))
        
        top_score = card_scores[0]['score']
        best_candidates = [c for c in card_scores if c['score'] == top_score]
        
        final_match_card = None
        match_method = "Scoring"

        if len(best_candidates) == 1:
            logger.info("Single best card found by score.")
            final_match_card = get_full_card_details(best_candidates[0]['meta']['card_id'], clip_processor)
        else:
            # Tie-breaker using image similarity
            logger.info(f"Score tie between {len(best_candidates)} cards. Using image similarity to break tie.")
            temp_image_path = "temp_query_card.png"
            Image.fromarray(img_np).save(temp_image_path)
            query_embedding = clip_processor.get_single_image_embedding(temp_image_path)
            os.remove(temp_image_path)

            if query_embedding is not None:
                tiebreaker_embeddings = np.array([search_index['embeddings'][c['index']] for c in best_candidates])
                similarities = 1 - cdist(query_embedding.reshape(1, -1), tiebreaker_embeddings, 'cosine')
                best_match_index = np.argmax(similarities)
                final_match_card = get_full_card_details(best_candidates[best_match_index]['meta']['card_id'], clip_processor)
                match_method = "Scoring with Image Tie-break"

        if final_match_card:
            final_match = {
                'metadata': final_match_card,
                'ocr_confirmed': True, # If we got here, it's via OCR
                'score': top_score,
                'match_method': match_method
            }
            logger.info(f"✅ Final match ({match_method}): {final_match['metadata']['name']}")
            return jsonify(final_match)
        else:
            logger.error("❌ Could not find a matching card in the end.")
            return jsonify({'error': 'Could not find a matching card.'}), 404

    except Exception as e:
        logger.exception("💥 Error during card scanning process.")
        return jsonify({'error': f'An internal error occurred: {e}'}), 500

@app.route('/')
def index():
    return "<h1>Poké-Scanner API v2 (with OCR)</h1>"

if __name__ == '__main__':
    cert_path = 'cert.pem'
    key_path = 'key.pem'
    
    if os.path.exists(cert_path) and os.path.exists(key_path):
        ssl_context = (cert_path, key_path)
        logger.info("✅ Starting Flask backend server with HTTPS...")
        app.run(host='0.0.0.0', port=5001, debug=True, ssl_context=ssl_context)
    else:
        logger.error("\n❌ ERROR: Could not find cert.pem or key.pem.") 