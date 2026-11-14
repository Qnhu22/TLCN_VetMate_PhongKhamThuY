document.addEventListener(
    "DOMContentLoaded",
    () => {
        const form =
            document.getElementById(
                "resetOtpForm"
            );

        const inputs = Array.from(
            document.querySelectorAll(
                ".forgot-otp-input"
            )
        );

        const hiddenInput =
            document.getElementById(
                "resetOtpValue"
            );

        const submitButton =
            document.getElementById(
                "resetOtpSubmit"
            );

        const otpCountdown =
            document.getElementById(
                "resetOtpCountdown"
            );

        const resendButton =
            document.getElementById(
                "resetResendButton"
            );

        const resendCountdown =
            document.getElementById(
                "resetResendCountdown"
            );

        const expiresAt =
            Number(
                window
                    .VETMATE_RESET_OTP_EXPIRES_AT
            ) * 1000;

        const resendAvailableAt =
            Number(
                window
                    .VETMATE_RESET_RESEND_AVAILABLE_AT
            ) * 1000;


        const updateHiddenOtp = () => {
            if (!hiddenInput) {
                return;
            }

            hiddenInput.value =
                inputs
                    .map(
                        (input) =>
                            input.value
                    )
                    .join("");
        };


        const updateFilledState = (
            input
        ) => {
            input.classList.toggle(
                "is-filled",
                input.value !== ""
            );
        };


        inputs.forEach(
            (input, index) => {
                input.addEventListener(
                    "input",
                    () => {
                        input.value =
                            input.value
                                .replace(
                                    /\D/g,
                                    ""
                                )
                                .slice(0, 1);

                        updateFilledState(
                            input
                        );

                        updateHiddenOtp();

                        if (
                            input.value
                            && index
                                < inputs.length - 1
                        ) {
                            inputs[
                                index + 1
                            ].focus();
                        }
                    }
                );


                input.addEventListener(
                    "keydown",
                    (event) => {
                        if (
                            event.key
                                === "Backspace"
                            && !input.value
                            && index > 0
                        ) {
                            inputs[
                                index - 1
                            ].focus();
                        }

                        if (
                            event.key
                                === "ArrowLeft"
                            && index > 0
                        ) {
                            event.preventDefault();

                            inputs[
                                index - 1
                            ].focus();
                        }

                        if (
                            event.key
                                === "ArrowRight"
                            && index
                                < inputs.length - 1
                        ) {
                            event.preventDefault();

                            inputs[
                                index + 1
                            ].focus();
                        }
                    }
                );


                input.addEventListener(
                    "paste",
                    (event) => {
                        const pasted =
                            event.clipboardData
                                ?.getData(
                                    "text"
                                )
                                .replace(
                                    /\D/g,
                                    ""
                                )
                                .slice(
                                    0,
                                    inputs.length
                                );

                        if (!pasted) {
                            return;
                        }

                        event.preventDefault();

                        pasted
                            .split("")
                            .forEach(
                                (
                                    digit,
                                    pasteIndex
                                ) => {
                                    if (
                                        inputs[
                                            pasteIndex
                                        ]
                                    ) {
                                        inputs[
                                            pasteIndex
                                        ].value =
                                            digit;

                                        updateFilledState(
                                            inputs[
                                                pasteIndex
                                            ]
                                        );
                                    }
                                }
                            );

                        updateHiddenOtp();

                        const focusIndex =
                            Math.min(
                                pasted.length,
                                inputs.length
                            ) - 1;

                        inputs[
                            focusIndex
                        ]?.focus();
                    }
                );
            }
        );


        form?.addEventListener(
            "submit",
            (event) => {
                updateHiddenOtp();

                if (
                    !hiddenInput
                    || hiddenInput.value.length
                        !== 6
                ) {
                    event.preventDefault();

                    inputs.find(
                        (input) =>
                            !input.value
                    )?.focus();

                    return;
                }

                if (submitButton) {
                    submitButton.disabled =
                        true;

                    submitButton.innerHTML =
                        "Đang xác minh...";
                }
            }
        );


        const expireOtp = () => {
            inputs.forEach(
                (input) => {
                    input.disabled = true;
                }
            );

            if (submitButton) {
                submitButton.disabled =
                    true;
            }

            if (otpCountdown) {
                otpCountdown.textContent =
                    "Đã hết hạn";
            }
        };


        const updateOtpCountdown = () => {
            if (
                !otpCountdown
                || !Number.isFinite(
                    expiresAt
                )
            ) {
                return;
            }

            const remaining =
                Math.max(
                    0,
                    expiresAt
                        - Date.now()
                );

            if (remaining <= 0) {
                expireOtp();
                return;
            }

            const totalSeconds =
                Math.ceil(
                    remaining / 1000
                );

            const minutes =
                Math.floor(
                    totalSeconds / 60
                );

            const seconds =
                totalSeconds % 60;

            otpCountdown.textContent =
                `${String(minutes)
                    .padStart(2, "0")}:`
                + `${String(seconds)
                    .padStart(2, "0")}`;
        };


        const updateResendCountdown =
            () => {
                if (
                    !resendButton
                    || !resendCountdown
                    || !Number.isFinite(
                        resendAvailableAt
                    )
                ) {
                    return;
                }

                const remaining =
                    Math.max(
                        0,
                        resendAvailableAt
                            - Date.now()
                    );

                if (remaining <= 0) {
                    resendButton.disabled =
                        false;

                    resendCountdown
                        .textContent = "";

                    return;
                }

                resendButton.disabled =
                    true;

                resendCountdown.textContent =
                    `(${Math.ceil(
                        remaining / 1000
                    )}s)`;
            };


        updateOtpCountdown();
        updateResendCountdown();

        const timer =
            window.setInterval(
                () => {
                    updateOtpCountdown();
                    updateResendCountdown();

                    if (
                        Number.isFinite(
                            expiresAt
                        )
                        && Date.now()
                            >= expiresAt
                    ) {
                        window.clearInterval(
                            timer
                        );
                    }
                },
                1000
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


        inputs[0]?.focus({
            preventScroll: true
        });
    }
);