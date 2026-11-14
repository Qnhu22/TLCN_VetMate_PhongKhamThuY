document.addEventListener(
    "DOMContentLoaded",
    () => {
        const filterForm =
            document.getElementById(
                "accessFilterForm"
            );

        const searchInput =
            document.getElementById(
                "accessSearchInput"
            );

        const autoSubmitFields =
            document.querySelectorAll(
                "[data-auto-submit]"
            );

        if (filterForm) {
            autoSubmitFields.forEach(
                (field) => {
                    field.addEventListener(
                        "change",
                        () => {
                            filterForm.submit();
                        }
                    );
                }
            );
        }

        if (searchInput) {
            searchInput.addEventListener(
                "keydown",
                (event) => {
                    if (
                        event.key === "Escape"
                        && searchInput.value
                    ) {
                        searchInput.value = "";
                        searchInput.focus();
                    }
                }
            );
        }
    }
);