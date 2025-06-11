document.addEventListener('DOMContentLoaded', async () => {
    const cardsContainer = document.getElementById('cards-container');

    async function loadCollection() {
        const collectionIds = JSON.parse(localStorage.getItem('pokemonCollection')) || [];
        
        if (collectionIds.length === 0) {
            cardsContainer.innerHTML = '<p>Your collection is empty. Start scanning some cards!</p>';
            return;
        }

        cardsContainer.innerHTML = '<p>Loading your collection...</p>';

        try {
            // This assumes an 'all_cards.json' file exists. 
            // The downloader script would need to be modified to create this.
            // For now, let's assume it has been created.
            const response = await fetch('pokemon_cards/data/all_cards.json');
            if (!response.ok) {
                throw new Error('Failed to load card database.');
            }
            const allCards = await response.json();
            
            // Create a lookup for faster access
            const cardDataLookup = {};
            allCards.forEach(card => {
                cardDataLookup[card.id] = card;
            });

            const collectedCards = collectionIds.map(id => cardDataLookup[id]).filter(Boolean);

            displayCollection(collectedCards);

        } catch (error) {
            console.error("Error loading collection:", error);
            cardsContainer.innerHTML = '<p>Could not load your collection due to an error. Make sure the `all_cards.json` file is available.</p>';
        }
    }

    function displayCollection(cards) {
        cardsContainer.innerHTML = '';
        cards.forEach(card => {
            const cardElement = document.createElement('div');
            cardElement.classList.add('card');
            cardElement.innerHTML = `
                <div class="card__content">
                    <img src="${card.images.small}" alt="${card.name}">
                </div>
            `;
            cardsContainer.appendChild(cardElement);
        });
    }

    loadCollection();
}); 