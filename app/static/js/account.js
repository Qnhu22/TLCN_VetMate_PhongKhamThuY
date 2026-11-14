
document.addEventListener("DOMContentLoaded", () => {
    const toasts = document.querySelectorAll(
        ".profile-toast"
    );

    toasts.forEach((toast) => {
        const closeButton = toast.querySelector(
            ".profile-toast-close"
        );

        let closed = false;

        const dismissToast = () => {
            if (closed) {
                return;
            }

            closed = true;
            toast.classList.add("is-hiding");

            window.setTimeout(() => {
                toast.remove();
            }, 220);
        };

        closeButton?.addEventListener(
            "click",
            dismissToast
        );

        window.setTimeout(
            dismissToast,
            5000
        );
    });
});
