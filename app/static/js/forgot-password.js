document.addEventListener(
    "DOMContentLoaded",
    () => {
        const form =
            document.getElementById(
                "forgotPasswordForm"
            );

        const emailInput =
            document.getElementById(
                "forgotEmail"
            );

        const emailError =
            document.getElementById(
                "forgotEmailError"
            );

        const submitButton =
            document.getElementById(
                "forgotSubmit"
            );

        if (
            form
            && emailInput
            && emailError
        ) {
            const inputShell =
                emailInput.closest(
                    ".forgot-input-shell"
                );

            const showEmailError = (
                message
            ) => {
                emailError.textContent =
                    message;

                inputShell?.classList.add(
                    "is-invalid"
                );
            };

            const clearEmailError = () => {
                emailError.textContent = "";

                inputShell?.classList.remove(
                    "is-invalid"
                );
            };

            emailInput.addEventListener(
                "input",
                clearEmailError
            );

            form.addEventListener(
                "submit",
                (event) => {
                    clearEmailError();

                    const email =
                        emailInput.value
                            .trim();

                    const emailPattern =
                        /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

                    if (!email) {
                        event.preventDefault();

                        showEmailError(
                            "Vui lòng nhập email."
                        );

                        emailInput.focus();
                        return;
                    }

                    if (
                        !emailPattern.test(
                            email
                        )
                    ) {
                        event.preventDefault();

                        showEmailError(
                            "Vui lòng nhập email hợp lệ."
                        );

                        emailInput.focus();
                        return;
                    }

                    if (submitButton) {
                        submitButton.disabled =
                            true;

                        submitButton.innerHTML =
                            "Đang gửi mã...";
                    }
                }
            );
        }

        const alerts =
            document.querySelectorAll(
                ".js-auto-dismiss"
            );

        alerts.forEach((alert) => {
            window.setTimeout(() => {
                alert.classList.add(
                    "is-hiding"
                );

                window.setTimeout(() => {
                    alert.remove();
                }, 300);
            }, 10000);
        });
    }
);