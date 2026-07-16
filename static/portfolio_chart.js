(function () {
    const wrap = document.getElementById("portfolio-chart-svg-wrap");
    if (!wrap) return;

    const tabs = document.querySelectorAll(".portfolio-range-tab");
    const summaryValue = document.getElementById("portfolio-chart-summary-value");
    const summaryChange = document.getElementById("portfolio-chart-summary-change");
    const axisLabels = document.getElementById("portfolio-chart-axis-labels");

    let currentRange = "1M";
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
            return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        }
        if (range === "1W" || range === "1M") {
            return d.toLocaleDateString([], { month: "short", day: "numeric" });
        }
        return d.toLocaleDateString([], { month: "short", year: "numeric" });
    }

    function formatMoney(amount) {
        return "$" + amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function render(points, range) {
        if (!points || points.length < 2) {
            setEmpty("Not enough history yet to chart this range. Make a few trades and check back.");
            return;
        }

        const width = wrap.clientWidth || 600;
        const height = wrap.clientHeight || 220;
        const padding = 8;

        const values = points.map((p) => p.value);
        const min = Math.min(...values);
        const max = Math.max(...values);
        const spread = max - min || 1;

        const stepX = (width - padding * 2) / (points.length - 1);

        const coords = points.map((p, i) => {
            const x = padding + i * stepX;
            const y = padding + (height - padding * 2) * (1 - (p.value - min) / spread);
            return [x, y];
        });

        const linePath = coords.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`).join(" ");

        const areaPath =
            `M${coords[0][0].toFixed(2)},${(height - padding).toFixed(2)} ` +
            coords.map(([x, y]) => `L${x.toFixed(2)},${y.toFixed(2)}`).join(" ") +
            ` L${coords[coords.length - 1][0].toFixed(2)},${(height - padding).toFixed(2)} Z`;

        const first = values[0];
        const last = values[values.length - 1];
        const change = last - first;
        const changePct = first !== 0 ? (change / first) * 100 : 0;
        const isGain = change >= 0;

        const lineColor = isGain ? "var(--accent-green)" : "var(--accent-red)";
        const fillColor = isGain ? "var(--accent-green-bg)" : "var(--accent-red-bg)";

        wrap.innerHTML = `
            <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
                <path d="${areaPath}" fill="${fillColor}" stroke="none"></path>
                <path d="${linePath}" fill="none" stroke="${lineColor}" stroke-width="2"></path>
            </svg>
        `;

        if (summaryValue) {
            summaryValue.textContent = formatMoney(last);
        }

        if (summaryChange) {
            const sign = isGain ? "+" : "";
            summaryChange.textContent = `${sign}${formatMoney(change).replace("$", "$")} (${sign}${changePct.toFixed(2)}%)`;
            summaryChange.className = `chart-summary-change ${isGain ? "gain" : "loss"}`;
        }

        axisLabels.innerHTML =
            `<span>${formatDate(points[0].timestamp, range)}</span>` +
            `<span>${formatDate(points[points.length - 1].timestamp, range)}</span>`;
    }

    function loadRange(range) {
        currentRange = range;
        const token = ++requestToken;

        setLoading();

        fetch(`/api/portfolio/history?range=${encodeURIComponent(range)}`)
            .then((res) => res.json())
            .then((data) => {
                if (token !== requestToken) return;
                if (data.error || !data.points || data.points.length === 0) {
                    setEmpty(data.error || "No chart data available for this range yet.");
                    return;
                }
                render(data.points, range);
            })
            .catch((err) => {
                console.error(err);
                if (token === requestToken) {
                    setEmpty("Couldn't load portfolio history.");
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
