document.addEventListener('DOMContentLoaded', () => {
    const startScanBtn = document.getElementById('start-scan-btn');
    const captureBtn = document.getElementById('capture-btn');
    const cameraFeed = document.getElementById('camera-feed');
    const scannerUi = document.getElementById('scanner-ui');
    const resultsContainer = document.getElementById('results-container');
    const resultCardContainer = document.getElementById('result-card');
    const loadingIndicator = document.getElementById('loading-indicator');
    const saveCollectionBtn = document.getElementById('save-collection-btn');
    const scanAgainBtn = document.getElementById('scan-again-btn');

    let stream = null;
    let matchedCardData = null;

    startScanBtn.addEventListener('click', async () => {
        try {
            stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: 'environment' // Prefer the rear camera
                }
            });
            cameraFeed.srcObject = stream;
            startScanBtn.classList.add('hidden');
            captureBtn.classList.remove('hidden');
        } catch (err) {
            console.error("Error accessing camera:", err);
            alert("Could not access the camera. Please ensure you have given permission.");
        }
    });

    captureBtn.addEventListener('click', async () => {
        if (!stream) return;

        scannerUi.classList.add('hidden');
        loadingIndicator.classList.remove('hidden');

        const canvas = document.createElement('canvas');
        canvas.width = cameraFeed.videoWidth;
        canvas.height = cameraFeed.videoHeight;
        const context = canvas.getContext('2d');
        context.drawImage(cameraFeed, 0, 0, canvas.width, canvas.height);

        canvas.toBlob(async (blob) => {
            const formData = new FormData();
            formData.append('card_image', blob, 'scan.png');

            try {
                // Use the same hostname as the page, but on port 5001 (the backend)
                const apiUrl = `https://${window.location.hostname}:5001/api/scan`;
                console.log(`Sending scan request to: ${apiUrl}`); // For debugging

                const response = await fetch(apiUrl, {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    throw new Error(`Server returned ${response.status}`);
                }

                const result = await response.json();
                matchedCardData = result; // Store the full result
                displayResult(result);

            } catch (err) {
                console.error("Error scanning card:", err);
                alert("Failed to scan the card. Please try again.");
                showScanner(); // Go back to scanner
            } finally {
                loadingIndicator.classList.add('hidden');
            }
        }, 'image/png');
    });
    
    function displayResult(result) {
        const card = result.metadata;
        const prices = card.cardmarket ? card.cardmarket.prices : null;

        let pricesHtml = '<div class="price-item"><span class="price-label">No price data available.</span></div>';
        if (prices) {
            pricesHtml = `
                <div class="price-item">
                    <span class="price-label">Avg. Sell</span>
                    <span class="price-value">€${prices.averageSellPrice?.toFixed(2) || 'N/A'}</span>
                </div>
                <div class="price-item">
                    <span class="price-label">Low</span>
                    <span class="price-value">€${prices.lowPrice?.toFixed(2) || 'N/A'}</span>
                </div>
                <div class="price-item">
                    <span class="price-label">Trend</span>
                    <span class="price-value">€${prices.trendPrice?.toFixed(2) || 'N/A'}</span>
                </div>
            `;
        }

        const ocr_confirmed_html = result.ocr_confirmed ? 
            '<span class="ocr-status confirmed">✔ Text Match</span>' :
            '<span class="ocr-status fallback">Image Match Only</span>';

        resultCardContainer.innerHTML = `
            <div class="scan-result-card">
                <div class="scan-result-image">
                    <img src="${card.images.large}" alt="${card.name}">
                </div>
                <div class="scan-result-details">
                    <div class="scan-result-header">
                        <h2>${card.name}</h2>
                        ${ocr_confirmed_html}
                    </div>
                    <div class="info-grid">
                        <div class="info-item"><span class="info-label">Set</span><span class="info-value">${card.set.name}</span></div>
                        <div class="info-item"><span class="info-label">Rarity</span><span class="info-value">${card.rarity}</span></div>
                        <div class="info-item"><span class="info-label">HP</span><span class="info-value">${card.hp || 'N/A'}</span></div>
                        <div class="info-item"><span class="info-label">Types</span><span class="info-value">${card.types?.join(', ') || 'N/A'}</span></div>
                    </div>
                    <div class="price-info">
                        <h3>Cardmarket Price</h3>
                        <div class="price-grid">
                            ${pricesHtml}
                        </div>
                    </div>
                </div>
            </div>
        `;
        resultsContainer.classList.remove('hidden');
    }

    function showScanner() {
        resultsContainer.classList.add('hidden');
        scannerUi.classList.remove('hidden');
        matchedCardData = null;
    }

    scanAgainBtn.addEventListener('click', showScanner);

    saveCollectionBtn.addEventListener('click', () => {
        if (!matchedCardData) return;

        const cardId = matchedCardData.metadata.card_id;
        let collection = JSON.parse(localStorage.getItem('pokemonCollection')) || [];
        
        if (!collection.includes(cardId)) {
            collection.push(cardId);
            localStorage.setItem('pokemonCollection', JSON.stringify(collection));
            alert(`${matchedCardData.metadata.name} has been added to your collection!`);
        } else {
            alert(`${matchedCardData.metadata.name} is already in your collection.`);
        }
        showScanner();
    });
}); 