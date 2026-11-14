document.addEventListener(
    "DOMContentLoaded",
    () => {
        const form =
            document.getElementById(
                "resetPasswordForm"
            );

        const password =
            document.getElementById(
                "resetPassword"
            );

        const confirmPassword =
            document.getElementById(
                "resetConfirmPassword"
            );

        const togglePassword =
            document.getElementById(
                "toggleResetPassword"
            );

        const toggleConfirm =
            document.getElementById(
                "toggleResetConfirmPassword"
            );

        const lengthRule =
            document.getElementById(
                "passwordLengthRule"
            );

        const confirmError =
            document.getElementById(
                "confirmPasswordClientError"
            );

        const submitButton =
            document.getElementById(
                "resetPasswordSubmit"
            );

        const mascot =
            document.getElementById(
                "resetPasswordMascot"
            );

        const mascotMessage =
            document.getElementById(
                "resetMascotMessage"
            );


        const setMascotMessage = (
            message
        ) => {
            if (mascotMessage) {
                mascotMessage.textContent =
                    message;
            }
        };


        const updateMascot = () => {
            if (!mascot) {
                return;
            }

            const passwordFocused =
                document.activeElement
                    === password
                || document.activeElement
                    === confirmPassword;

            const showingPassword =
                (
                    document.activeElement
                        === password
                    && password?.type
                        === "text"
                )
                || (
                    document.activeElement
                        === confirmPassword
                    && confirmPassword?.type
                        === "text"
                );

            mascot.classList.toggle(
                "is-covering",
                passwordFocused
            );

            mascot.classList.toggle(
                "is-peeking",
                passwordFocused
                    && showingPassword
            );

            if (!passwordFocused) {
                setMascotMessage(
                    "Tạo mật khẩu mới thật an toàn nhé!"
                );

                return;
            }

            if (showingPassword) {
                setMascotMessage(
                    "Mình chỉ hé mắt một chút thôi 👀"
                );
            } else {
                setMascotMessage(
                    "Yên tâm, mình không nhìn đâu!"
                );
            }
        };


        const bindPasswordFocus = (
            input
        ) => {
            if (!input) {
                return;
            }

            input.addEventListener(
                "focus",
                updateMascot
            );

            input.addEventListener(
                "blur",
                () => {
                    window.setTimeout(
                        updateMascot,
                        0
                    );
                }
            );
        };


        bindPasswordFocus(
            password
        );

        bindPasswordFocus(
            confirmPassword
        );


        const bindToggle = (
            button,
            input
        ) => {
            if (
                !button
                || !input
            ) {
                return;
            }

            button.addEventListener(
                "click",
                () => {
                    const showing =
                        input.type
                            === "text";

                    input.type =
                        showing
                            ? "password"
                            : "text";

                    button.setAttribute(
                        "aria-pressed",
                        String(!showing)
                    );

                    button.setAttribute(
                        "aria-label",
                        showing
                            ? "Hiện mật khẩu"
                            : "Ẩn mật khẩu"
                    );

                    const icon =
                        button.querySelector(
                            "i"
                        );

                    if (icon) {
                        icon.className =
                            showing
                                ? "bi bi-eye"
                                : "bi bi-eye-slash";
                    }

                    input.focus({
                        preventScroll: true
                    });

                    updateMascot();
                }
            );
        };


        bindToggle(
            togglePassword,
            password
        );

        bindToggle(
            toggleConfirm,
            confirmPassword
        );


        const updatePasswordRule = () => {
            if (
                !password
                || !lengthRule
            ) {
                return;
            }

            lengthRule.classList.toggle(
                "is-valid",
                password.value.length >= 8
            );
        };


        const updateConfirmState = () => {
            if (
                !password
                || !confirmPassword
                || !confirmError
            ) {
                return true;
            }

            const hasValue =
                confirmPassword.value
                    .length > 0;

            const matches =
                confirmPassword.value
                    === password.value;

            confirmError.hidden =
                !hasValue
                || matches;

            return matches;
        };


        password?.addEventListener(
            "input",
            () => {
                updatePasswordRule();
                updateConfirmState();
            }
        );

        confirmPassword?.addEventListener(
            "input",
            updateConfirmState
        );


        form?.addEventListener(
            "submit",
            (event) => {
                const passwordValid =
                    password
                    && password.value.length
                        >= 8;

                const passwordsMatch =
                    updateConfirmState();

                if (
                    !passwordValid
                    || !passwordsMatch
                ) {
                    event.preventDefault();

                    if (!passwordValid) {
                        password?.focus();

                        return;
                    }

                    confirmPassword?.focus();

                    return;
                }

                if (submitButton) {
                    submitButton.disabled =
                        true;

                    submitButton.innerHTML =
                        `
                            Đang cập nhật
                            <span
                                aria-hidden="true"
                            >
                                ...
                            </span>
                        `;
                }
            }
        );


        const alerts =
            document.querySelectorAll(
                ".js-auto-dismiss"
            );

        alerts.forEach(
            (alert) => {
                window.setTimeout(
                    () => {
                        alert.classList.add(
                            "is-hiding"
                        );

                        window.setTimeout(
                            () => {
                                alert.remove();
                            },
                            300
                        );
                    },
                    10000
                );
            }
        );


        updatePasswordRule();
        updateConfirmState();
        updateMascot();
    }
);