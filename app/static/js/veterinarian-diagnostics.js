document.addEventListener("DOMContentLoaded", () => {
    const rows = document.getElementById("diagnosticRows");
    const template = document.getElementById("diagnosticRowTemplate");
    if (!rows || !template) return;
    document.getElementById("addDiagnosticRow")?.addEventListener("click", () => {
        const error = document.getElementById("diagnosticRowError");
        if (rows.children.length >= 30) {
            if (error) error.textContent = "Tối đa 30 chỉ số chi tiết.";
            return;
        }
        rows.appendChild(template.content.cloneNode(true));
        if (error) error.textContent = "";
    });
    rows.addEventListener("click", (event) => {
        const button = event.target.closest("[data-remove-diagnostic-row]");
        if (button) button.closest("tr")?.remove();
    });
});
