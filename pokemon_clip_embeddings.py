#!/usr/bin/env python3
"""
Pokémon Card CLIP Embeddings Generator
=====================================
Generates CLIP embeddings for all downloaded Pokémon card images.
Creates a searchable vector database for semantic similarity search.
"""

import os
import json
import numpy as np
import pandas as pd
from PIL import Image
import torch
import clip
from tqdm import tqdm
import pickle
from pathlib import Path
import logging
from datetime import datetime
import argparse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('clip_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PokemonCLIPProcessor:
    def __init__(self, base_dir="pokemon_cards", model_name="ViT-B/32", device=None):
        """
        Initialize the CLIP processor for Pokémon cards.
        
        Args:
            base_dir (str): Base directory containing pokemon_cards folder
            model_name (str): CLIP model to use (ViT-B/32, ViT-B/16, ViT-L/14)
            device (str): Device to use ('cuda', 'cpu', or None for auto)
        """
        self.base_dir = Path(base_dir)
        self.images_dir = self.base_dir / "images"
        self.data_dir = self.base_dir / "data"
        self.embeddings_dir = self.base_dir / "embeddings"
        
        # Create embeddings directory
        self.embeddings_dir.mkdir(exist_ok=True)
        
        # Setup device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        logger.info(f"Using device: {self.device}")
        
        # Load CLIP model
        logger.info(f"Loading CLIP model: {model_name}")
        self.model, self.preprocess = clip.load(model_name, device=self.device)
        self.model_name = model_name.replace("/", "-")
        
        # Load card data
        self.load_card_data()
        
    def load_card_data(self):
        """Load the card metadata from JSON files."""
        try:
            # Load main card data
            with open(self.data_dir / "all_cards.json", 'r') as f:
                self.all_cards = json.load(f)
            logger.info(f"Loaded {len(self.all_cards)} cards from database")
            
            # Create lookup dictionary by image filename
            self.card_lookup = {}
            for card in self.all_cards:
                if 'images' in card and 'large' in card['images']:
                    # Extract filename from URL
                    large_url = card['images']['large']
                    filename = large_url.split('/')[-1]
                    # Create the expected local filename
                    local_filename = f"{card['set']['id']}-{card['number']}_{card['name'].replace(' ', '_')}_large.png"
                    self.card_lookup[local_filename] = card
                    
        except FileNotFoundError:
            logger.error("Card data not found. Make sure you've run the download script first.")
            raise
            
    def get_image_files(self, image_type="large"):
        """Get list of image files to process."""
        pattern = f"*_{image_type}.png"
        image_files = list(self.images_dir.glob(pattern))
        logger.info(f"Found {len(image_files)} {image_type} images to process")
        return sorted(image_files)
    
    def process_image(self, image_path):
        """Process a single image and return its CLIP embedding."""
        try:
            # Load and preprocess image
            image = Image.open(image_path).convert('RGB')
            image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)
            
            # Generate embedding
            with torch.no_grad():
                image_features = self.model.encode_image(image_tensor)
                # Normalize the features
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                
            return image_features.cpu().numpy().flatten()
            
        except Exception as e:
            logger.error(f"Error processing {image_path}: {e}")
            return None
    
    def get_single_image_embedding(self, image_path):
        """
        Public method to get embedding for a single external image.
        This is a convenience wrapper around process_image.
        """
        return self.process_image(image_path)
    
    def generate_embeddings(self, image_type="large", batch_size=32):
        """
        Generate CLIP embeddings for all images.
        
        Args:
            image_type (str): Type of images to process ('large' or 'small')
            batch_size (int): Number of images to process before saving checkpoint
        """
        image_files = self.get_image_files(image_type)
        
        if not image_files:
            logger.error(f"No {image_type} images found!")
            return
        
        # Output files
        embeddings_file = self.embeddings_dir / f"embeddings_{image_type}_{self.model_name}.pkl"
        metadata_file = self.embeddings_dir / f"metadata_{image_type}_{self.model_name}.json"
        checkpoint_file = self.embeddings_dir / f"checkpoint_{image_type}_{self.model_name}.pkl"
        
        # Load existing progress if available
        embeddings = []
        metadata = []
        processed_files = set()
        start_idx = 0
        
        if checkpoint_file.exists():
            logger.info("Loading checkpoint...")
            with open(checkpoint_file, 'rb') as f:
                checkpoint = pickle.load(f)
                embeddings = checkpoint['embeddings']
                metadata = checkpoint['metadata']
                processed_files = checkpoint['processed_files']
                start_idx = len(embeddings)
            logger.info(f"Resuming from {start_idx}/{len(image_files)} images")
        
        # Process images
        logger.info(f"Processing {len(image_files) - start_idx} remaining images...")
        
        for i, image_path in enumerate(tqdm(image_files[start_idx:], 
                                          desc=f"Generating {image_type} embeddings",
                                          initial=start_idx, 
                                          total=len(image_files))):
            
            if image_path.name in processed_files:
                continue
                
            # Generate embedding
            embedding = self.process_image(image_path)
            
            if embedding is not None:
                embeddings.append(embedding)
                
                # Get card metadata
                card_data = self.card_lookup.get(image_path.name, {})
                
                # Create metadata entry
                meta_entry = {
                    'filename': image_path.name,
                    'filepath': str(image_path),
                    'card_id': card_data.get('id', ''),
                    'name': card_data.get('name', ''),
                    'set_name': card_data.get('set', {}).get('name', ''),
                    'set_id': card_data.get('set', {}).get('id', ''),
                    'number': card_data.get('number', ''),
                    'types': card_data.get('types', []),
                    'subtypes': card_data.get('subtypes', []),
                    'supertype': card_data.get('supertype', ''),
                    'hp': card_data.get('hp', ''),
                    'rarity': card_data.get('rarity', ''),
                    'artist': card_data.get('artist', ''),
                    'embedding_model': self.model_name,
                    'processed_at': datetime.now().isoformat()
                }
                metadata.append(meta_entry)
                processed_files.add(image_path.name)
                
            # Save checkpoint every batch_size images
            if (i + 1) % batch_size == 0:
                checkpoint = {
                    'embeddings': embeddings,
                    'metadata': metadata,
                    'processed_files': processed_files
                }
                with open(checkpoint_file, 'wb') as f:
                    pickle.dump(checkpoint, f)
                logger.info(f"Checkpoint saved at {start_idx + i + 1}/{len(image_files)} images")
        
        # Convert embeddings to numpy array
        if embeddings:
            embeddings_array = np.array(embeddings)
            logger.info(f"Generated embeddings shape: {embeddings_array.shape}")
            
            # Save final embeddings
            with open(embeddings_file, 'wb') as f:
                pickle.dump({
                    'embeddings': embeddings_array,
                    'model_name': self.model_name,
                    'embedding_dim': embeddings_array.shape[1],
                    'num_images': len(embeddings_array),
                    'created_at': datetime.now().isoformat()
                }, f)
            
            # Save metadata
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Create CSV export
            df = pd.DataFrame(metadata)
            csv_file = self.embeddings_dir / f"metadata_{image_type}_{self.model_name}.csv"
            df.to_csv(csv_file, index=False)
            
            # Clean up checkpoint
            if checkpoint_file.exists():
                checkpoint_file.unlink()
            
            logger.info(f"✅ Successfully generated {len(embeddings)} embeddings!")
            logger.info(f"📁 Files saved:")
            logger.info(f"   - Embeddings: {embeddings_file}")
            logger.info(f"   - Metadata: {metadata_file}")
            logger.info(f"   - CSV: {csv_file}")
            
        else:
            logger.error("No embeddings generated!")
    
    def create_search_index(self, image_type="large"):
        """Create a searchable index from the embeddings."""
        embeddings_file = self.embeddings_dir / f"embeddings_{image_type}_{self.model_name}.pkl"
        metadata_file = self.embeddings_dir / f"metadata_{image_type}_{self.model_name}.json"
        
        if not embeddings_file.exists() or not metadata_file.exists():
            logger.error("Embeddings or metadata files not found. Run generate_embeddings first.")
            return
        
        # Load data
        with open(embeddings_file, 'rb') as f:
            embedding_data = pickle.load(f)
        
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        embeddings = embedding_data['embeddings']
        
        # Create search index
        search_index = {
            'embeddings': embeddings,
            'metadata': metadata,
            'model_name': self.model_name,
            'embedding_dim': embeddings.shape[1],
            'num_cards': len(embeddings),
            'created_at': datetime.now().isoformat()
        }
        
        # Save search index
        index_file = self.embeddings_dir / f"search_index_{image_type}_{self.model_name}.pkl"
        with open(index_file, 'wb') as f:
            pickle.dump(search_index, f)
        
        logger.info(f"✅ Search index created: {index_file}")
        return search_index
    
    def search_similar_cards(self, query_image_path, top_k=10, image_type="large"):
        """
        Find similar cards to a query image.
        
        Args:
            query_image_path (str): Path to query image
            top_k (int): Number of similar cards to return
            image_type (str): Type of embeddings to use
        """
        index_file = self.embeddings_dir / f"search_index_{image_type}_{self.model_name}.pkl"
        
        if not index_file.exists():
            logger.error("Search index not found. Run create_search_index first.")
            return None
        
        # Load search index
        with open(index_file, 'rb') as f:
            search_index = pickle.load(f)
        
        # Process query image
        query_embedding = self.process_image(query_image_path)
        if query_embedding is None:
            logger.error(f"Could not process query image: {query_image_path}")
            return None
        
        # Calculate similarities
        embeddings = search_index['embeddings']
        similarities = np.dot(embeddings, query_embedding)
        
        # Get top-k results
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            result = {
                'similarity': float(similarities[idx]),
                'metadata': search_index['metadata'][idx]
            }
            results.append(result)
        
        return results

def main():
    parser = argparse.ArgumentParser(description='Generate CLIP embeddings for Pokémon cards')
    parser.add_argument('--base-dir', default='pokemon_cards', help='Base directory containing pokemon_cards')
    parser.add_argument('--model', default='ViT-B/32', choices=['ViT-B/32', 'ViT-B/16', 'ViT-L/14'], 
                       help='CLIP model to use')
    parser.add_argument('--image-type', default='large', choices=['large', 'small'], 
                       help='Image type to process')
    parser.add_argument('--batch-size', type=int, default=32, help='Batch size for checkpointing')
    parser.add_argument('--device', choices=['cuda', 'cpu'], help='Device to use')
    parser.add_argument('--skip-embeddings', action='store_true', help='Skip embedding generation')
    parser.add_argument('--search', help='Path to query image for similarity search')
    parser.add_argument('--top-k', type=int, default=10, help='Number of similar cards to return')
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = PokemonCLIPProcessor(
        base_dir=args.base_dir,
        model_name=args.model,
        device=args.device
    )
    
    if not args.skip_embeddings:
        # Generate embeddings
        logger.info("🚀 Starting embedding generation...")
        processor.generate_embeddings(
            image_type=args.image_type,
            batch_size=args.batch_size
        )
        
        # Create search index
        logger.info("📚 Creating search index...")
        processor.create_search_index(image_type=args.image_type)
    
    # Perform search if query provided
    if args.search:
        logger.info(f"🔍 Searching for similar cards to: {args.search}")
        results = processor.search_similar_cards(
            args.search, 
            top_k=args.top_k,
            image_type=args.image_type
        )
        
        if results:
            print(f"\n🎯 Top {len(results)} similar cards:")
            for i, result in enumerate(results, 1):
                meta = result['metadata']
                similarity = result['similarity']
                print(f"{i:2d}. {meta['name']} ({meta['set_name']}) - Similarity: {similarity:.4f}")

if __name__ == "__main__":
    # Check requirements
    try:
        import clip
        import torch
    except ImportError as e:
        print("❌ Missing required packages. Install with:")
        print("pip install torch torchvision clip-by-openai pillow tqdm pandas numpy")
        exit(1)
    
    main()
