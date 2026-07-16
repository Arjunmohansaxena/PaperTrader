document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".symbol-search, #sidebar-search-input").forEach((input) => {

        let suggestionsEl;
        let container = null;

        if (input.id === "sidebar-search-input") {
            suggestionsEl = document.getElementById("sidebar-search-results");
        } else {
            container = input.closest(".search-box");
            suggestionsEl = container ? container.querySelector(".suggestions") : null;
        }

        if (!suggestionsEl) return;

        let debounceTimer;

        input.addEventListener("input", () => {

            clearTimeout(debounceTimer);

            const query = input.value.trim();

            if (query.length < 2) {
                suggestionsEl.innerHTML = "";
                suggestionsEl.style.display = "none";
                return;
            }

            debounceTimer = setTimeout(() => {
                runSearch(query, input, suggestionsEl);
            }, 250);
        });

        document.addEventListener("click", (event) => {

            if (
                event.target !== input &&
                !suggestionsEl.contains(event.target)
            ) {
                suggestionsEl.innerHTML = "";
                suggestionsEl.style.display = "none";
            }

        });

        suggestionsEl.addEventListener("click", (event) => {

            const item = event.target.closest(".suggestion");
            if (!item) return;

            const symbol = item.dataset.symbol;

            // Sidebar search
            if (input.id === "sidebar-search-input") {
                window.location.href = `/company/${symbol}`;
                return;
            }

            // Buy / Sell page search
            input.value = symbol;
            suggestionsEl.innerHTML = "";
            suggestionsEl.style.display = "none";
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
        suggestionsEl.style.display = "none";
        return;

    }

    if (!response.ok) {
        suggestionsEl.innerHTML = "";
        suggestionsEl.style.display = "none";
        return;
    }

    const stocks = await response.json();
    console.log(stocks);

    if (input.value.trim() !== query) return;

    if (!stocks.length) {
        suggestionsEl.innerHTML = "";
        suggestionsEl.style.display = "none";
        return;
    }

    suggestionsEl.innerHTML = stocks.map(stock => `
        <div class="suggestion" data-symbol="${stock.symbol}">
            <div class="search-symbol">${stock.symbol}</div>
            <div class="search-name">${stock.description}</div>
        </div>
    `).join("");
    if (input.id === "sidebar-search-input") {
    suggestionsEl.style.display = "block";
}

}