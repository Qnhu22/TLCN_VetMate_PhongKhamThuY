
document.addEventListener("DOMContentLoaded", () => {
    const speciesSelect =
        document.getElementById("speciesID");

    const breedSelect =
        document.getElementById("breedID");

    if (speciesSelect && breedSelect) {
        const initialBreed =
            breedSelect.dataset.selected || "";

        const updateBreeds = (selectedBreed = "") => {
            const speciesID = speciesSelect.value;

            breedSelect.querySelectorAll(
                "option[data-species]"
            ).forEach((option) => {
                const matches =
                    option.dataset.species === speciesID;

                option.hidden = !matches;
                option.disabled = !matches;
            });

            const chosen = breedSelect.querySelector(
                `option[value="${selectedBreed}"]`
            );

            breedSelect.value =
                chosen && !chosen.disabled
                    ? selectedBreed
                    : "";
        };

        speciesSelect.addEventListener(
            "change",
            () => updateBreeds()
        );

        updateBreeds(initialBreed);
    }

    document.querySelectorAll(
        ".profile-toast"
    ).forEach((toast) => {
        let closed = false;

        const dismiss = () => {
            if (closed) return;
            closed = true;

            toast.classList.add("is-hiding");

            window.setTimeout(() => {
                toast.remove();
            }, 220);
        };

        toast.querySelector(
            ".profile-toast-close"
        )?.addEventListener("click", dismiss);

        window.setTimeout(dismiss, 5000);
    });

    
    // =====================================================
    // PET PHOTO PREVIEW
    // =====================================================

    const photoInput = document.getElementById("petPhoto");
    const photoPreview = document.getElementById("petPhotoPreview");
    const removePhotoInput = document.getElementById("removePhoto");
    const removeButton = document.getElementById("removePetPhotoButton");
    const photoError = document.getElementById("petPhotoError");

    if (photoInput && photoPreview) {
        const allowedTypes = [
            "image/jpeg",
            "image/png",
            "image/webp",
        ];

        const maxSize = 5 * 1024 * 1024;
        let previewUrl = null;

        const showError = (message) => {
            if (photoError) {
                photoError.textContent = message;
            }
        };

        const clearPreviewUrl = () => {
            if (previewUrl) {
                URL.revokeObjectURL(previewUrl);
                previewUrl = null;
            }
        };

        const showPlaceholder = () => {
            photoPreview.replaceChildren();

            const icon = document.createElement("i");
            icon.className = "bi bi-camera";
            photoPreview.appendChild(icon);
        };

        photoInput.addEventListener("change", () => {
            const file = photoInput.files[0];

            if (!file) return;

            showError("");

            if (!allowedTypes.includes(file.type)) {
                showError(
                    "Chỉ chấp nhận ảnh JPG, PNG hoặc WebP."
                );
                photoInput.value = "";
                return;
            }

            if (file.size > maxSize) {
                showError(
                    "Dung lượng ảnh không được vượt quá 5 MB."
                );
                photoInput.value = "";
                return;
            }

            clearPreviewUrl();
            previewUrl = URL.createObjectURL(file);

            const img = document.createElement("img");
            img.alt = "Ảnh thú cưng vừa chọn";
            img.src = previewUrl;

            photoPreview.replaceChildren(img);

            if (removePhotoInput) {
                removePhotoInput.value = "0";
            }
        });

        removeButton?.addEventListener("click", () => {
            photoInput.value = "";
            clearPreviewUrl();
            showPlaceholder();
            showError("");

            if (removePhotoInput) {
                removePhotoInput.value = "1";
            }
        });

        window.addEventListener(
            "pagehide",
            clearPreviewUrl,
            { once: true }
        );
    }

});

