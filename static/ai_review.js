(function () {
    const body = document.getElementById("ai-review-body");
    if (!body) return;

    const generateBtn = document.getElementById("ai-review-generate");
    const downloadLink = document.getElementById("ai-review-download");

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    function listOrNone(items) {
        if (!items || items.length === 0) {
            return '<p class="ai-review-none">Nothing notable here.</p>';
        }
        return (
            "<ul>" +
            items.map((item) => `<li>${escapeHtml(item)}</li>`).join("") +
            "</ul>"
        );
    }

    function renderReview(record) {
        if (!record || !record.review) {
            body.innerHTML =
                '<div class="ai-review-empty">No review yet. Click "Generate Review" to get an AI read on your portfolio\'s diversification, risk, and performance.</div>';
            downloadLink.style.display = "none";
            return;
        }

        const r = record.review;
        const generatedDate = new Date(record.generated_at.replace(" ", "T") + "Z");
        const generatedLabel = isNaN(generatedDate.getTime())
            ? record.generated_at
            : generatedDate.toLocaleString();

        body.innerHTML = `
            <div class="ai-review-meta">Generated ${escapeHtml(generatedLabel)} · portfolio value at the time: $${Number(record.portfolio_value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
            <div class="ai-review-section">
                <h4>Summary</h4>
                <p>${escapeHtml(r.summary || "")}</p>
            </div>
            <div class="ai-review-section">
                <h4>Diversification</h4>
                <p>${escapeHtml(r.diversification_notes || "")}</p>
            </div>
            <div class="ai-review-section">
                <h4>Risk Flags</h4>
                ${listOrNone(r.risk_flags)}
            </div>
            <div class="ai-review-section">
                <h4>Strengths</h4>
                ${listOrNone(r.strengths)}
            </div>
            <div class="ai-review-section">
                <h4>Suggestions</h4>
                ${listOrNone(r.suggestions)}
            </div>
        `;

        downloadLink.href = `/portfolio/review/${record.review_id}/download`;
        downloadLink.style.display = "";
    }

    function renderError(message) {
        body.innerHTML = `<div class="ai-review-error">Couldn't generate a review: ${escapeHtml(message)}</div>`;
    }

    function renderLoading() {
        body.innerHTML = `
            <div class="ai-review-loading">
                <div class="ai-review-skeleton-line"></div>
                <div class="ai-review-skeleton-line"></div>
                <div class="ai-review-skeleton-line short"></div>
            </div>
        `;
    }

    async function loadLatest() {
        try {
            const res = await fetch("/api/portfolio/review/latest");
            const data = await res.json();
            renderReview(data.review ? data : null);
        } catch (err) {
            // Silently keep the empty state; not worth surfacing an error
            // just because the "latest review" fetch failed on page load.
        }
    }

    async function generateReview() {
        generateBtn.disabled = true;
        generateBtn.textContent = "Generating…";
        renderLoading();

        try {
            const res = await fetch("/api/portfolio/review", { method: "POST" });
            const data = await res.json();

            if (!res.ok) {
                renderError(data.error || "Something went wrong.");
            } else {
                renderReview(data);
            }
        } catch (err) {
            renderError("Could not reach the server.");
        } finally {
            generateBtn.disabled = false;
            generateBtn.textContent = "Generate Review";
        }
    }

    generateBtn.addEventListener("click", generateReview);
    loadLatest();
})();
