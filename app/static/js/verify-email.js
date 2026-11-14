document.addEventListener(
    "DOMContentLoaded",
    () => {

        const form =
            document.getElementById(
                "verifyOtpForm"
            );

        const inputs = [
            ...document.querySelectorAll(
                ".verify-otp-input"
            ),
        ];

        const otpValue =
            document.getElementById(
                "otpValue"
            );

        const otpCountdown =
            document.getElementById(
                "otpCountdown"
            );

        const resendButton =
            document.getElementById(
                "resendOtpButton"
            );

        const resendCountdown =
            document.getElementById(
                "resendCountdown"
            );

        const verifySubmit =
            document.getElementById(
                "verifyOtpSubmit"
            );


        /* =============================================
           AUTO DISMISS ALERTS
           ============================================= */

        const autoDismissAlerts =
            document.querySelectorAll(
                ".js-auto-dismiss"
            );

        autoDismissAlerts.forEach(
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


        /* =============================================
           OTP INPUT
           ============================================= */

        const syncOtp = () => {

            if (!otpValue) {
                return;
            }

            otpValue.value =
                inputs
                    .map(
                        (input) =>
                            input.value
                    )
                    .join("");

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
                                .slice(
                                    0,
                                    1
                                );

                        if (
                            input.value
                            && index
                                < inputs.length - 1
                        ) {
                            inputs[
                                index + 1
                            ].focus();
                        }

                        syncOtp();

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

                    }
                );

            }
        );


        /* =============================================
           PASTE OTP
           ============================================= */

        inputs.forEach(
            (input) => {

                input.addEventListener(
                    "paste",
                    (event) => {

                        const text =
                            (
                                event.clipboardData
                                    ?.getData(
                                        "text"
                                    )
                                ?? ""
                            )
                                .replace(
                                    /\D/g,
                                    ""
                                )
                                .slice(
                                    0,
                                    6
                                );

                        if (!text) {
                            return;
                        }

                        event.preventDefault();

                        inputs.forEach(
                            (
                                otpInput,
                                index
                            ) => {

                                otpInput.value =
                                    text[index]
                                    ?? "";

                            }
                        );

                        syncOtp();

                        const focusIndex =
                            Math.min(
                                text.length,
                                inputs.length
                            ) - 1;

                        if (focusIndex >= 0) {
                            inputs[
                                focusIndex
                            ].focus();
                        }

                    }
                );

            }
        );


        /* =============================================
           SUBMIT
           ============================================= */

        form?.addEventListener(
            "submit",
            (event) => {

                syncOtp();

                if (
                    !/^\d{6}$/.test(
                        otpValue?.value
                        ?? ""
                    )
                ) {
                    event.preventDefault();

                    inputs.find(
                        (input) =>
                            !input.value
                    )?.focus();
                }

            }
        );


        /* =============================================
           OTP EXPIRY
           ============================================= */

        const expiresAt =
            window.VETMATE_OTP_EXPIRES_AT
                ? new Date(
                    window
                        .VETMATE_OTP_EXPIRES_AT
                )
                : null;


        const updateExpiry = () => {

            if (
                !expiresAt
                || !otpCountdown
            ) {
                return;
            }

            const remaining =
                Math.max(
                    0,
                    Math.floor(
                        (
                            expiresAt.getTime()
                            - Date.now()
                        )
                        / 1000
                    )
                );

            const minutes =
                Math.floor(
                    remaining / 60
                );

            const seconds =
                remaining % 60;

            otpCountdown.textContent =
                `${String(minutes)
                    .padStart(2, "0")}:`
                + `${String(seconds)
                    .padStart(2, "0")}`;


            if (remaining <= 0) {

                otpCountdown.textContent =
                    "Đã hết hạn";

                inputs.forEach(
                    (input) => {
                        input.disabled = true;
                    }
                );

                if (verifySubmit) {
                    verifySubmit.disabled =
                        true;
                }

            }

        };


        updateExpiry();

        const expiryTimer =
            window.setInterval(
                () => {

                    updateExpiry();

                    if (
                        expiresAt
                        && Date.now()
                            >= expiresAt.getTime()
                    ) {
                        window.clearInterval(
                            expiryTimer
                        );
                    }

                },
                1000
            );


        /* =============================================
           RESEND COOLDOWN
           ============================================= */

        const resendAvailableAt =
            window
                .VETMATE_RESEND_AVAILABLE_AT
                ? Number(
                    window
                        .VETMATE_RESEND_AVAILABLE_AT
                ) * 1000
                : null;


        const updateResend = () => {

            if (
                !resendButton
                || !resendCountdown
            ) {
                return;
            }

            if (!resendAvailableAt) {

                resendButton.disabled =
                    false;

                resendCountdown.textContent =
                    "";

                return;
            }

            const remaining =
                Math.max(
                    0,
                    Math.ceil(
                        (
                            resendAvailableAt
                            - Date.now()
                        )
                        / 1000
                    )
                );


            if (remaining <= 0) {

                resendButton.disabled =
                    false;

                resendCountdown.textContent =
                    "";

                return;
            }

            resendButton.disabled =
                true;

            resendCountdown.textContent =
                `(${remaining}s)`;

        };


        updateResend();

        const resendTimer =
            window.setInterval(
                () => {

                    updateResend();

                    if (
                        resendAvailableAt
                        && Date.now()
                            >= resendAvailableAt
                    ) {
                        window.clearInterval(
                            resendTimer
                        );
                    }

                },
                1000
            );


        /* =============================================
           INITIAL FOCUS
           ============================================= */

        window.addEventListener(
            "pageshow",
            (event) => {

                if (event.persisted) {
                    window.location.reload();
                }

            }
        );
        if (
            expiresAt
            && expiresAt.getTime()
                > Date.now()
        ) {
            inputs[0]?.focus();
        }

    }
);