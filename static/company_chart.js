(function () {
    const wrap = document.getElementById("chart-svg-wrap");
    if (!wrap) return;

    const symbol = wrap.dataset.symbol;
    const tabs = document.querySelectorAll(".range-tab");
    const summaryPrice = document.getElementById("chart-summary-price");
    const summaryChange = document.getElementById("chart-summary-change");
    const axisLabels = document.getElementById("chart-axis-labels");

    let currentRange = "1D";
    let requestToken = 0;

    function setLoading() {
        wrap.innerHTML = '<div class="chart-loading">Loading chart…</div>';
        axisLabels.innerHTML = "";
    }

    function setEmpty(message) {
        wrap.innerHTML = `<div class="chart-empty">${message}</div>`;
        axisLabels.innerHTML = "";
    }

    function formatDate(timestamp, range) {
        const d = new Date(timestamp * 1000);

        if (range === "1D") {
            return d.toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
            });
        }

        if (range === "1W" || range === "1M") {
            return d.toLocaleDateString([], {
                month: "short",
                day: "numeric",
            });
        }

        return d.toLocaleDateString([], {
            month: "short",
            year: "numeric",
        });
    }

    function render(points, range) {
        if (!points || points.length < 2) {
            setEmpty("Chart data isn't available for this range right now.");
            return;
        }

        const width = wrap.clientWidth || 600;
        const height = wrap.clientHeight || 220;
        const padding = 8;

        // Use closing prices from the backend
        const prices = points.map((p) => p.close);

        const min = Math.min(...prices);
        const max = Math.max(...prices);
        const spread = max - min || 1;

        const stepX = (width - padding * 2) / (points.length - 1);

        const coords = points.map((p, i) => {
            const x = padding + i * stepX;
            const y =
                padding +
                (height - padding * 2) *
                    (1 - (p.close - min) / spread);

            return [x, y];
        });

        const linePath = coords
            .map(([x, y], i) =>
                `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`
            )
            .join(" ");

        const areaPath =
            `M${coords[0][0].toFixed(2)},${(height - padding).toFixed(2)} ` +
            coords
                .map(([x, y]) => `L${x.toFixed(2)},${y.toFixed(2)}`)
                .join(" ") +
            ` L${coords[coords.length - 1][0].toFixed(2)},${(
                height - padding
            ).toFixed(2)} Z`;

        const first = prices[0];
        const last = prices[prices.length - 1];

        const change = last - first;
        const changePct = first !== 0 ? (change / first) * 100 : 0;

        const isGain = change >= 0;

        const lineColor = isGain
            ? "var(--accent-green)"
            : "var(--accent-red)";

        const fillColor = isGain
            ? "var(--accent-green-bg)"
            : "var(--accent-red-bg)";

        wrap.innerHTML = `
            <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
                <path d="${areaPath}" fill="${fillColor}" stroke="none"></path>
                <path d="${linePath}" fill="none" stroke="${lineColor}" stroke-width="2"></path>
            </svg>
        `;

        if (summaryPrice) {
            summaryPrice.textContent = `$${last.toFixed(2)}`;
        }

        if (summaryChange) {
            const sign = isGain ? "+" : "";

            summaryChange.textContent =
                `${sign}${change.toFixed(2)} (${sign}${changePct.toFixed(2)}%)`;

            summaryChange.className =
                `chart-summary-change ${isGain ? "gain" : "loss"}`;
        }

        axisLabels.innerHTML =
            `<span>${formatDate(points[0].timestamp, range)}</span>` +
            `<span>${formatDate(points[points.length - 1].timestamp, range)}</span>`;
    }

    function loadRange(range) {
        currentRange = range;
        const token = ++requestToken;

        setLoading();

        fetch(`/api/company/${encodeURIComponent(symbol)}/history?range=${encodeURIComponent(range)}`)
            .then((res) => res.json())
            .then((data) => {
                if (token !== requestToken) return;

                if (data.error || !data.points || data.points.length === 0) {
                    setEmpty(data.error || "No chart data available for this range.");
                    return;
                }

                render(data.points, range);
            })
            .catch((err) => {
                console.error(err);
                if (token === requestToken) {
                    setEmpty("Couldn't load chart data.");
                }
            });
    }

    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            tabs.forEach((t) => t.classList.remove("active"));
            tab.classList.add("active");
            loadRange(tab.dataset.range);
        });
    });

    loadRange(currentRange);
})();