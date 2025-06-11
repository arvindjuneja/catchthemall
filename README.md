# Pokémon TCG Collection Manager & Card Scanner

This project provides a suite of tools to download, manage, and analyze your Pokémon TCG collection. It includes a powerful card downloader, a tool to generate CLIP embeddings for image-based search, and a web-based card scanner to identify cards from your webcam.

## Features

- **Pokémon Card Downloader (`pokemon_downloader.py`)**:
  - Automatically fetches all Pokémon card sets and card data from the [Pokémon TCG API](https://pokemontcg.io/).
  - Downloads high-resolution and low-resolution card images.
  - Organizes cards into a clean folder structure.
  - Resumes downloads if interrupted.
  - Logs any failed downloads.

- **CLIP Embeddings Generator (`pokemon_clip_embeddings.py`)**:
  - Generates CLIP embeddings for all downloaded card images.
  - Creates a searchable database of your card collection based on image similarity.

- **Web-Based Card Scanner (`scanner.html`, `scanner.js`, `scanner_app.py`)**:
  - Uses your webcam to identify Pokémon cards in real-time.
  - Compares the webcam feed against the CLIP embeddings of your collection.
  - Displays the closest matching card from your collection.

- **Secure Server (`secure_server.py`)**:
  - Serves the web interface over HTTPS for secure webcam access.

## File Structure

The downloader script creates the following directory structure:

```
pokemon_cards/
├── images/           # All card images
│   ├── base1-1_Alakazam_large.png
│   ├── base1-1_Alakazam_small.png
│   └── ...
├── data/            # JSON and CSV data
│   ├── all_cards.json      # Complete database
│   ├── pokemon_cards.csv   # Spreadsheet format
│   └── ...
└── embeddings/       # CLIP embeddings
    └── clip_embeddings.pkl
```

## How to Run

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Download Pokémon Cards:**
    ```bash
    python pokemon_downloader.py
    ```
    This will download all card data and images into the `pokemon_cards` directory. This can take several hours and a few gigabytes of space.

3.  **Generate CLIP Embeddings:**
    ```bash
    python pokemon_clip_embeddings.py
    ```
    This will process the downloaded images and create the `clip_embeddings.pkl` file.

4.  **Run the Web Server:**
    Before running the server, you'll need to generate a self-signed SSL certificate for secure webcam access.
    ```bash
    openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/C=US/ST=CA/L=SF/O=Demo/CN=localhost"
    ```
    Then, start the server:
    ```bash
    python secure_server.py
    ```

5.  **Access the Card Scanner:**
    Open your web browser and navigate to `https://localhost:8000/scanner.html`. You may need to accept a security warning due to the self-signed certificate.
