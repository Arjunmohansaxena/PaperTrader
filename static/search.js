document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".symbol-search").forEach((input) => {
        const box = input.closest(".search-box");
        const suggestionsEl = box ? box.querySelector(".suggestions") : null;
        if (!suggestionsEl) return;

        let debounceTimer;

        input.addEventListener("input", () => {
            clearTimeout(debounceTimer);
            const query = input.value.trim();
            if (query.length < 2) {
                suggestionsEl.innerHTML = "";
                return;
            }
            debounceTimer = setTimeout(() => runSearch(query, input, suggestionsEl), 300);
        });

        document.addEventListener("click", (event) => {
            if (box && !box.contains(event.target)) {
                suggestionsEl.innerHTML = "";
            }
        });

        suggestionsEl.addEventListener("click", (event) => {
            const item = event.target.closest(".suggestion");
            if (!item) return;
            input.value = item.dataset.symbol;
            suggestionsEl.innerHTML = "";
            input.focus();
        });
    });
});

async function runSearch(query, input, suggestionsEl) {
    let response;
    try {
        response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
    } catch (err) {
        suggestionsEl.innerHTML = "";
        return;
    }
    if (!response.ok) {
        suggestionsEl.innerHTML = "";
        return;
    }
    const stocks = await response.json();
    if (input.value.trim() !== query) return; // stale response guard
    if (!stocks.length) {
        suggestionsEl.innerHTML = "";
        return;
    }
    suggestionsEl.innerHTML = stocks.map((stock) => `
        <div class="suggestion" data-symbol="${stock.symbol}">
            <strong>${stock.symbol}</strong>
            <span>${stock.description}</span>
        </div>
    `).join("");
}