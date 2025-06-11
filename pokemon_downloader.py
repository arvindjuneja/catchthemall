#!/usr/bin/env python3
"""
Pokemon Card Downloader
Downloads all Pokemon cards from the Pokemon TCG API and saves card data + images
"""

import requests
import json
import os
import time
from urllib.parse import urlparse
from pathlib import Path
import csv
from datetime import datetime
import argparse

class PokemonCardDownloader:
    def __init__(self, output_dir="pokemon_cards"):
        self.base_url = "https://api.pokemontcg.io/v2"
        self.output_dir = Path(output_dir)
        self.images_dir = self.output_dir / "images"
        self.data_dir = self.output_dir / "data"
        
        # Create directories
        self.output_dir.mkdir(exist_ok=True)
        self.images_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)
        
        # Stats
        self.total_cards = 0
        self.downloaded_cards = 0
        self.failed_downloads = 0
        self.failed_cards = []
        
        print(f"🎯 Pokemon Card Downloader initialized")
        print(f"📁 Output directory: {self.output_dir.absolute()}")
    
    def get_all_sets(self):
        """Get all available Pokemon card sets"""
        print("📋 Fetching all Pokemon card sets...")
        
        try:
            response = requests.get(f"{self.base_url}/sets", timeout=30)
            response.raise_for_status()
            sets_data = response.json()
            
            sets = sets_data.get('data', [])
            print(f"✅ Found {len(sets)} sets")
            
            # Save sets data
            with open(self.data_dir / "sets.json", 'w') as f:
                json.dump(sets_data, f, indent=2)
            
            return sets
            
        except Exception as e:
            print(f"❌ Error fetching sets: {e}")
            return []
    
    def get_cards_from_set(self, set_id, page=1, page_size=250):
        """Get cards from a specific set"""
        try:
            params = {
                'q': f'set.id:{set_id}',
                'page': page,
                'pageSize': page_size
            }
            
            response = requests.get(f"{self.base_url}/cards", params=params, timeout=30)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"❌ Error fetching cards from set {set_id}: {e}")
            return None
    
    def download_image(self, url, filename):
        """Download a single image"""
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to download {url}: {e}")
            return False
    
    def process_card(self, card):
        """Process a single card - download image and save data"""
        card_id = card.get('id', 'unknown')
        
        try:
            # Create safe filename
            safe_name = "".join(c for c in f"{card_id}_{card.get('name', 'unknown')}" if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_name = safe_name.replace(' ', '_')[:50]  # Limit length
            
            # Download large image if available
            large_image_url = card.get('images', {}).get('large')
            if large_image_url:
                image_filename = self.images_dir / f"{safe_name}_large.png"
                if not image_filename.exists():  # Skip if already downloaded
                    if self.download_image(large_image_url, image_filename):
                        card['local_image_large'] = str(image_filename)
                    else:
                        self.failed_downloads += 1
                        self.failed_cards.append({
                            'card_id': card_id,
                            'error': 'Failed to download large image',
                            'url': large_image_url
                        })
                else:
                    card['local_image_large'] = str(image_filename)
            
            # Download small image if available
            small_image_url = card.get('images', {}).get('small')
            if small_image_url:
                image_filename = self.images_dir / f"{safe_name}_small.png"
                if not image_filename.exists():
                    if self.download_image(small_image_url, image_filename):
                        card['local_image_small'] = str(image_filename)
                    else:
                        self.failed_downloads += 1
            
            self.downloaded_cards += 1
            
            # Progress update every 10 cards
            if self.downloaded_cards % 10 == 0:
                print(f"📥 Downloaded {self.downloaded_cards}/{self.total_cards} cards ({self.downloaded_cards/self.total_cards*100:.1f}%)")
            
            return card
            
        except Exception as e:
            print(f"❌ Error processing card {card_id}: {e}")
            self.failed_cards.append({
                'card_id': card_id,
                'error': str(e)
            })
            return None
    
    def download_all_cards(self):
        """Download all Pokemon cards"""
        print("🚀 Starting Pokemon card download...")
        start_time = datetime.now()
        
        # Get all sets
        sets = self.get_all_sets()
        if not sets:
            print("❌ No sets found, exiting")
            return
        
        all_cards = []
        
        # First pass: count total cards
        print("🔢 Counting total cards...")
        for set_data in sets:
            set_id = set_data.get('id')
            total_in_set = set_data.get('total', 0)
            self.total_cards += total_in_set
        
        print(f"📊 Total cards to download: {self.total_cards}")
        
        # Second pass: download everything
        for i, set_data in enumerate(sets, 1):
            set_id = set_data.get('id')
            set_name = set_data.get('name', 'Unknown Set')
            total_in_set = set_data.get('total', 0)
            
            print(f"\n📦 Processing set {i}/{len(sets)}: {set_name} ({set_id}) - {total_in_set} cards")
            
            page = 1
            cards_in_set = []
            
            while True:
                print(f"   📄 Fetching page {page}...")
                cards_response = self.get_cards_from_set(set_id, page)
                
                if not cards_response:
                    break
                
                cards = cards_response.get('data', [])
                if not cards:
                    break
                
                # Process each card
                for card in cards:
                    processed_card = self.process_card(card)
                    if processed_card:
                        cards_in_set.append(processed_card)
                        all_cards.append(processed_card)
                
                # Check if we have more pages
                if len(cards) < 250:  # Less than page size means last page
                    break
                
                page += 1
                time.sleep(0.1)  # Be nice to the API
            
            # Save set data
            set_filename = self.data_dir / f"set_{set_id}.json"
            with open(set_filename, 'w') as f:
                json.dump({
                    'set_info': set_data,
                    'cards': cards_in_set,
                    'total_cards': len(cards_in_set)
                }, f, indent=2)
            
            print(f"✅ Completed set {set_name}: {len(cards_in_set)} cards")
        
        # Save all cards data
        print("\n💾 Saving complete card database...")
        with open(self.data_dir / "all_cards.json", 'w') as f:
            json.dump(all_cards, f, indent=2)
        
        # Create CSV for easy analysis
        self.create_csv_export(all_cards)
        
        # Save failed downloads log
        if self.failed_cards:
            with open(self.data_dir / "failed_downloads.json", 'w') as f:
                json.dump(self.failed_cards, f, indent=2)
        
        # Final statistics
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n🎉 Download completed!")
        print(f"📊 Statistics:")
        print(f"   • Total cards processed: {len(all_cards)}")
        print(f"   • Successful downloads: {self.downloaded_cards}")
        print(f"   • Failed downloads: {self.failed_downloads}")
        print(f"   • Total time: {duration}")
        print(f"   • Average time per card: {duration.total_seconds()/len(all_cards):.2f}s")
        print(f"📁 Files saved to: {self.output_dir.absolute()}")
    
    def create_csv_export(self, cards):
        """Create CSV export for easy analysis"""
        print("📊 Creating CSV export...")
        
        csv_filename = self.data_dir / "pokemon_cards.csv"
        
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'id', 'name', 'set_name', 'set_id', 'number', 'rarity',
                'hp', 'types', 'supertype', 'subtypes',
                'image_small_url', 'image_large_url',
                'local_image_small', 'local_image_large',
                'market_price', 'tcgplayer_url'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for card in cards:
                # Flatten the data
                row = {
                    'id': card.get('id', ''),
                    'name': card.get('name', ''),
                    'set_name': card.get('set', {}).get('name', ''),
                    'set_id': card.get('set', {}).get('id', ''),
                    'number': card.get('number', ''),
                    'rarity': card.get('rarity', ''),
                    'hp': card.get('hp', ''),
                    'types': ', '.join(card.get('types', [])),
                    'supertype': card.get('supertype', ''),
                    'subtypes': ', '.join(card.get('subtypes', [])),
                    'image_small_url': card.get('images', {}).get('small', ''),
                    'image_large_url': card.get('images', {}).get('large', ''),
                    'local_image_small': card.get('local_image_small', ''),
                    'local_image_large': card.get('local_image_large', ''),
                    'market_price': card.get('tcgplayer', {}).get('prices', {}).get('holofoil', {}).get('market', ''),
                    'tcgplayer_url': card.get('tcgplayer', {}).get('url', '')
                }
                
                writer.writerow(row)
        
        print(f"✅ CSV export saved: {csv_filename}")

    def get_all_card_data(self):
        """Get all card data from the downloaded JSON files."""
        all_cards = []
        for file_path in self.data_dir.glob("set_*.json"):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'cards' in data:
                    all_cards.extend(data['cards'])
        return all_cards

    def create_unified_card_database(self):
        """Create a single JSON file containing all cards."""
        logger.info("Creating unified card database...")
        all_cards = self.get_all_card_data()
        
        if not all_cards:
            logger.error("No card data found to unify.")
            return

        output_path = self.data_dir / "all_cards.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_cards, f, indent=2)
            
        logger.info(f"✅ Unified database created with {len(all_cards)} cards at: {output_path}")

    def run(self, download_images=True):
        """Run the downloader"""
        self.download_all_cards()
        # After downloading, create the unified database
        self.create_unified_card_database()

def main():
    """Main function"""
    # Initialize downloader
    downloader = PokemonCardDownloader()

    # Setup argument parser
    parser = argparse.ArgumentParser(description="Pokémon TCG Data Downloader")
    parser.add_argument("--skip-images", action="store_true", help="Skip downloading card images")
    parser.add_argument("--create-db-only", action="store_true", help="Only create the unified database from existing files")
    args = parser.parse_args()

    # Start process
    try:
        if args.create_db_only:
            downloader.create_unified_card_database()
        else:
            downloader.run(download_images=not args.skip_images)
    except KeyboardInterrupt:
        print("\n⏹️  Download interrupted by user")

if __name__ == "__main__":
    main()