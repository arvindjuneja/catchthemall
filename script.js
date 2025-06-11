document.addEventListener('DOMContentLoaded', () => {
    const setSelector = document.getElementById('set-selector');
    const cardsContainer = document.getElementById('cards-container');
    const modal = document.getElementById('card-modal');
    const modalClose = document.querySelector('.modal-close');
    const modalCardContent = document.getElementById('modal-card-content');
    
    // Filters
    const filterControls = document.getElementById('filter-controls');
    const searchBar = document.getElementById('search-bar');
    const typeFilter = document.getElementById('type-filter');
    const rarityFilter = document.getElementById('rarity-filter');

    let allCards = []; // To store all cards of the current set

    // Fetch sets data and populate dropdown
    fetch('pokemon_cards/data/sets.json')
        .then(response => response.json())
        .then(sets => {
            // Sort sets by release date, newest first
            sets.data.sort((a, b) => new Date(b.releaseDate) - new Date(a.releaseDate));
            
            sets.data.forEach(set => {
                const option = document.createElement('option');
                option.value = set.id;
                option.textContent = `${set.name} (${set.series})`;
                setSelector.appendChild(option);
            });
        });

    // Event listener for the dropdown
    setSelector.addEventListener('change', (event) => {
        const setId = event.target.value;
        if (setId) {
            loadCards(setId);
        } else {
            cardsContainer.innerHTML = '';
            filterControls.classList.add('hidden');
        }
    });

    async function loadCards(setId) {
        cardsContainer.innerHTML = '<h2>Loading cards...</h2>';
        try {
            const response = await fetch(`pokemon_cards/data/set_${setId}.json`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const cardData = await response.json();
            allCards = cardData.cards;
            
            populateFilters();
            displayCards(allCards);
            filterControls.classList.remove('hidden');

        } catch (error) {
            cardsContainer.innerHTML = `<p>Could not load cards for this set. Please try another.</p>`;
            console.error('Error fetching card data:', error);
            filterControls.classList.add('hidden');
        }
    }

    function displayCards(cardsToDisplay) {
        cardsContainer.innerHTML = '';
        if (cardsToDisplay.length === 0) {
            cardsContainer.innerHTML = '<p>No cards match the current filters.</p>';
            return;
        }

        cardsToDisplay.forEach(card => {
            const cardElement = createCardElement(card);
            cardElement.addEventListener('click', () => showCardDetails(card));
            cardsContainer.appendChild(cardElement);
        });
        
        init3dCardEffects();
    }

    function populateFilters() {
        const types = [...new Set(allCards.flatMap(card => card.types || []))];
        const rarities = [...new Set(allCards.map(card => card.rarity).filter(Boolean))];

        typeFilter.innerHTML = '<option value="">All Types</option>';
        types.sort().forEach(type => {
            const option = document.createElement('option');
            option.value = type;
            option.textContent = type;
            typeFilter.appendChild(option);
        });

        rarityFilter.innerHTML = '<option value="">All Rarities</option>';
        rarities.sort().forEach(rarity => {
            const option = document.createElement('option');
            option.value = rarity;
            option.textContent = rarity;
            rarityFilter.appendChild(option);
        });

        // Reset filters
        searchBar.value = '';
    }

    function filterCards() {
        const searchTerm = searchBar.value.toLowerCase();
        const selectedType = typeFilter.value;
        const selectedRarity = rarityFilter.value;

        const filteredCards = allCards.filter(card => {
            const nameMatch = card.name.toLowerCase().includes(searchTerm);
            const typeMatch = !selectedType || (card.types && card.types.includes(selectedType));
            const rarityMatch = !selectedRarity || card.rarity === selectedRarity;
            
            return nameMatch && typeMatch && rarityMatch;
        });

        displayCards(filteredCards);
    }

    searchBar.addEventListener('input', filterCards);
    typeFilter.addEventListener('change', filterCards);
    rarityFilter.addEventListener('change', filterCards);

    function createCardElement(card) {
        const cardElement = document.createElement('div');
        cardElement.classList.add('card');
        
        cardElement.innerHTML = `
            <div class="card__content">
                <img src="${card.images.small}" alt="${card.name}">
                <div class="card__shine"></div>
            </div>
        `;
        
        return cardElement;
    }

    function showCardDetails(card) {
        let attacksHtml = '<h3>Attacks</h3>';
        if (card.attacks && card.attacks.length > 0) {
            card.attacks.forEach(attack => {
                attacksHtml += `
                    <div class="attack">
                        <strong>${attack.name}</strong> (${attack.cost.join(', ')}) - <em>Damage: ${attack.damage}</em>
                        <p>${attack.text}</p>
                    </div>`;
            });
        } else {
            attacksHtml += '<p>No attacks listed.</p>';
        }

        let weaknessesHtml = '';
        if (card.weaknesses && card.weaknesses.length > 0) {
            weaknessesHtml = `<strong>Weaknesses:</strong> ${card.weaknesses.map(w => `${w.type} ${w.value}`).join(', ')}`;
        }

        let resistancesHtml = '';
        if (card.resistances && card.resistances.length > 0) {
            resistancesHtml = `<strong>Resistances:</strong> ${card.resistances.map(r => `${r.type} ${r.value}`).join(', ')}`;
        }

        const prices = card.cardmarket && card.cardmarket.prices ? card.cardmarket.prices : null;
        const pricesHtml = prices ? `
            <h3>Cardmarket Prices</h3>
            ${prices.averageSellPrice ? `<p><strong>Avg. Sell:</strong> €${prices.averageSellPrice.toFixed(2)}</p>` : ''}
            ${prices.lowPrice ? `<p><strong>Low:</strong> €${prices.lowPrice.toFixed(2)}</p>` : ''}
            ${prices.trendPrice ? `<p><strong>Trend:</strong> €${prices.trendPrice.toFixed(2)}</p>` : ''}
        ` : '<p>No price data available.</p>';
        
        modalCardContent.innerHTML = `
            <img src="${card.images.large}" alt="${card.name}">
            <div class="details">
                <h2>${card.name}</h2>
                <p><strong>Type:</strong> ${card.supertype} - ${card.subtypes ? card.subtypes.join(', ') : ''}</p>
                <p><strong>HP:</strong> ${card.hp}</p>
                ${card.evolvesFrom ? `<p><strong>Evolves From:</strong> ${card.evolvesFrom}</p>` : ''}
                
                ${attacksHtml}

                <h3>Details</h3>
                <p>${weaknessesHtml}</p>
                <p>${resistancesHtml}</p>
                <p><strong>Retreat Cost:</strong> ${card.retreatCost ? card.retreatCost.join(', ') : 'None'}</p>
                <p><strong>Rarity:</strong> ${card.rarity}</p>
                <p><strong>Artist:</strong> ${card.artist}</p>
                <p><strong>Set:</strong> ${card.set.name}</p>
                ${card.flavorText ? `<p><em>${card.flavorText}</em></p>` : ''}

                <div class="modal-prices">
                    ${pricesHtml}
                </div>
            </div>
        `;
        modal.style.display = 'block';
    }

    function init3dCardEffects() {
        const cards = document.querySelectorAll('.card');
    
        cards.forEach(card => {
            const content = card.querySelector('.card__content');
            const shine = card.querySelector('.card__shine');
    
            card.addEventListener('mousemove', e => {
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
    
                const centerX = rect.width / 2;
                const centerY = rect.height / 2;
    
                const rotateX = ((y - centerY) / centerY) * -20; // Increased rotation
                const rotateY = ((x - centerX) / centerX) * 20;
    
                content.style.transform = `rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.05, 1.05, 1.05)`;
    
                const angle = Math.atan2(y - centerY, x - centerX) * (180 / Math.PI) - 90;
                shine.style.background = `linear-gradient(${angle}deg, rgba(255, 255, 255, 0.2), rgba(255, 255, 255, 0) 80%)`;
                shine.style.opacity = '1';
            });
    
            card.addEventListener('mouseleave', () => {
                content.style.transform = 'rotateX(0) rotateY(0) scale3d(1, 1, 1)';
                shine.style.opacity = '0';
            });
        });
    }

    // Close modal listeners
    modalClose.addEventListener('click', () => {
        modal.style.display = 'none';
    });

    window.addEventListener('click', (event) => {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    });
}); 