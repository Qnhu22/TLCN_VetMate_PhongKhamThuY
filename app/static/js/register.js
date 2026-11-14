document.addEventListener(
    "DOMContentLoaded",
    () => {

        const form =
            document.getElementById(
                "registerForm"
            );

        const fullName =
            document.getElementById(
                "fullName"
            );

        const email =
            document.getElementById(
                "email"
            );

        const phone =
            document.getElementById(
                "phone"
            );

        const password =
            document.getElementById(
                "password"
            );

        const confirmPassword =
            document.getElementById(
                "confirmPassword"
            );

        const termsAccepted =
            document.getElementById(
                "termsAccepted"
            );

        const strengthBar =
            document.querySelector(
                ".register-strength-track span"
            );

        const strengthText =
            document.getElementById(
                "passwordStrengthText"
            );

        const mascot =
            document.querySelector(
                ".register-mascot .vetmate-mascot"
            );

        const mascotMessage =
            document.getElementById(
                "registerMascotMessage"
            );


        const errors = {
            fullName:
                document.getElementById(
                    "fullNameError"
                ),

            email:
                document.getElementById(
                    "emailError"
                ),

            phone:
                document.getElementById(
                    "phoneError"
                ),

            password:
                document.getElementById(
                    "passwordError"
                ),

            confirmPassword:
                document.getElementById(
                    "confirmPasswordError"
                ),

            terms:
                document.getElementById(
                    "termsError"
                ),
        };


        /* =============================================
           FIELD ERROR
           ============================================= */

        const clearError = (
            input,
            errorElement
        ) => {

            input
                ?.closest(
                    ".register-input-shell"
                )
                ?.classList.remove(
                    "has-error"
                );

            if (errorElement) {
                errorElement.hidden = true;
                errorElement.textContent = "";
            }

        };


        const showError = (
            input,
            errorElement,
            message
        ) => {

            input
                ?.closest(
                    ".register-input-shell"
                )
                ?.classList.add(
                    "has-error"
                );

            if (errorElement) {
                errorElement.textContent =
                    message;

                errorElement.hidden =
                    false;
            }

        };


        /* =============================================
           PHONE
           ============================================= */

        phone?.addEventListener(
            "input",
            () => {

                phone.value =
                    phone.value
                        .replace(/\D/g, "")
                        .slice(0, 10);

                clearError(
                    phone,
                    errors.phone
                );

            }
        );


        /* =============================================
           PASSWORD STRENGTH
           ============================================= */

        const updateStrength = () => {

            if (
                !password
                || !strengthBar
                || !strengthText
            ) {
                return;
            }

            const value =
                password.value;

            if (!value) {
                strengthBar.style.width =
                    "0";

                strengthText.textContent =
                    "Chưa nhập mật khẩu";

                return;
            }

            let score = 0;

            if (value.length >= 8) {
                score++;
            }

            if (value.length >= 12) {
                score++;
            }

            if (/[a-z]/.test(value)) {
                score++;
            }

            if (/[A-Z]/.test(value)) {
                score++;
            }

            if (/\d/.test(value)) {
                score++;
            }

            if (
                /[^A-Za-z0-9]/.test(value)
            ) {
                score++;
            }


            if (score <= 2) {

                strengthBar.style.width =
                    "30%";

                strengthBar.style.background =
                    "#b9435c";

                strengthText.textContent =
                    "Mật khẩu yếu";

            } else if (score <= 4) {

                strengthBar.style.width =
                    "65%";

                strengthBar.style.background =
                    "#c68a43";

                strengthText.textContent =
                    "Mật khẩu khá";

            } else {

                strengthBar.style.width =
                    "100%";

                strengthBar.style.background =
                    "#3d8468";

                strengthText.textContent =
                    "Mật khẩu mạnh";
            }

        };


        /* =============================================
           MASCOT PASSWORD STATE
           ============================================= */

        const coverMascotEyes = () => {

            mascot?.classList.add(
                "is-covering"
            );

            if (mascotMessage) {
                mascotMessage.textContent =
                    "Mình không nhìn đâu 🙈";
            }

        };


        const uncoverMascotEyes = () => {

            mascot?.classList.remove(
                "is-covering"
            );

            mascot?.classList.remove(
                "is-peeking"
            );

            if (mascotMessage) {
                mascotMessage.textContent =
                    "Mình sẽ đồng hành cùng bạn!";
            }

        };


        password?.addEventListener(
            "focus",
            coverMascotEyes
        );

        confirmPassword?.addEventListener(
            "focus",
            coverMascotEyes
        );


        password?.addEventListener(
            "blur",
            () => {

                window.setTimeout(
                    () => {

                        if (
                            document.activeElement
                            !== confirmPassword
                        ) {
                            uncoverMascotEyes();
                        }

                    },
                    80
                );

            }
        );


        confirmPassword?.addEventListener(
            "blur",
            () => {

                window.setTimeout(
                    () => {

                        if (
                            document.activeElement
                            !== password
                        ) {
                            uncoverMascotEyes();
                        }

                    },
                    80
                );

            }
        );


        /* =============================================
           PASSWORD TOGGLE
           ============================================= */

        document
            .querySelectorAll(
                "[data-password-toggle]"
            )
            .forEach(
                (button) => {

                    button.addEventListener(
                        "mousedown",
                        (event) => {
                            event.preventDefault();
                        }
                    );

                    button.addEventListener(
                        "click",
                        () => {

                            const targetId =
                                button.dataset
                                    .passwordToggle;

                            const input =
                                document.getElementById(
                                    targetId
                                );

                            if (!input) {
                                return;
                            }

                            const showing =
                                input.type
                                === "text";

                            input.type =
                                showing
                                    ? "password"
                                    : "text";

                            button.setAttribute(
                                "aria-label",
                                showing
                                    ? "Hiện mật khẩu"
                                    : "Ẩn mật khẩu"
                            );

                            mascot
                                ?.classList.toggle(
                                    "is-peeking",
                                    !showing
                                );

                        }
                    );

                }
            );


        /* =============================================
           CLEAR ERROR ON INPUT
           ============================================= */

        fullName?.addEventListener(
            "input",
            () => clearError(
                fullName,
                errors.fullName
            )
        );

        email?.addEventListener(
            "input",
            () => clearError(
                email,
                errors.email
            )
        );

        password?.addEventListener(
            "input",
            () => {

                clearError(
                    password,
                    errors.password
                );

                updateStrength();

                if (
                    confirmPassword?.value
                ) {
                    clearError(
                        confirmPassword,
                        errors.confirmPassword
                    );
                }

            }
        );

        confirmPassword?.addEventListener(
            "input",
            () => clearError(
                confirmPassword,
                errors.confirmPassword
            )
        );

        termsAccepted?.addEventListener(
            "change",
            () => {

                if (errors.terms) {
                    errors.terms.hidden =
                        true;

                    errors.terms.textContent =
                        "";
                }

            }
        );


        /* =============================================
           VALIDATE
           ============================================= */

        const validate = () => {

            let valid = true;

            const fullNameValue =
                fullName?.value.trim()
                ?? "";

            const emailValue =
                email?.value.trim()
                    .toLowerCase()
                ?? "";

            const phoneValue =
                phone?.value.trim()
                ?? "";

            const passwordValue =
                password?.value
                ?? "";

            const confirmValue =
                confirmPassword?.value
                ?? "";


            if (
                fullNameValue.length < 2
            ) {

                showError(
                    fullName,
                    errors.fullName,
                    "Họ và tên phải có ít nhất 2 ký tự."
                );

                valid = false;

            } else if (
                fullNameValue.length > 150
            ) {

                showError(
                    fullName,
                    errors.fullName,
                    "Họ và tên không được vượt quá 150 ký tự."
                );

                valid = false;
            }


            const emailPattern =
                /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

            if (!emailPattern.test(
                emailValue
            )) {

                showError(
                    email,
                    errors.email,
                    "Vui lòng nhập email hợp lệ."
                );

                valid = false;
            }


            if (
                !/^0\d{9}$/.test(
                    phoneValue
                )
            ) {

                showError(
                    phone,
                    errors.phone,
                    "Số điện thoại phải gồm 10 số và bắt đầu bằng 0."
                );

                valid = false;
            }


            if (
                passwordValue.length < 8
            ) {

                showError(
                    password,
                    errors.password,
                    "Mật khẩu phải có ít nhất 8 ký tự."
                );

                valid = false;
            }


            if (
                confirmValue
                !== passwordValue
            ) {

                showError(
                    confirmPassword,
                    errors.confirmPassword,
                    "Mật khẩu xác nhận không khớp."
                );

                valid = false;
            }


            if (
                !termsAccepted?.checked
            ) {

                if (errors.terms) {

                    errors.terms.textContent =
                        "Bạn cần đồng ý với điều khoản để tiếp tục.";

                    errors.terms.hidden =
                        false;
                }

                valid = false;
            }


            if (!valid) {

                if (mascotMessage) {
                    mascotMessage.textContent =
                        "Kiểm tra lại một chút nhé!";
                }

                const firstError =
                    form?.querySelector(
                        ".has-error input"
                    );

                firstError?.focus();

            }


            return valid;
        };


        /* =============================================
           SUBMIT
           ============================================= */

        form?.addEventListener(
            "submit",
            (event) => {

                if (!validate()) {
                    event.preventDefault();
                    return;
                }

                if (mascotMessage) {
                    mascotMessage.textContent =
                        "Đang tạo tài khoản... ✨";
                }

            }
        );


        updateStrength();

    }
);