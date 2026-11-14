document.addEventListener(
    "DOMContentLoaded",
    () => {

        const clearButton =
            document.getElementById(
                "clearCreateUserForm"
            );

        const fullNameInput =
            document.getElementById(
                "fullName"
            );

        const emailInput =
            document.getElementById(
                "email"
            );

        const phoneInput =
            document.getElementById(
                "phone"
            );

        const roleSelect =
            document.getElementById(
                "roleCode"
            );

        const statusSelect =
            document.getElementById(
                "status"
            );

        const form =
            document.getElementById(
                "createUserForm"
            );

        const password =
            document.getElementById(
                "password"
            );

        const confirmPassword =
            document.getElementById(
                "confirmPassword"
            );

        const strengthBar =
            document.getElementById(
                "passwordStrengthBar"
            );

        const strengthText =
            document.getElementById(
                "passwordStrengthText"
            );

        const matchMessage =
            document.getElementById(
                "passwordMatchMessage"
            );


        /* =============================================
           SHOW / HIDE PASSWORD
           ============================================= */

        document
            .querySelectorAll(
                "[data-password-target]"
            )
            .forEach(
                (button) => {

                    button.addEventListener(
                        "click",
                        () => {

                            const targetId =
                                button.dataset
                                    .passwordTarget;

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

                            button.textContent =
                                showing
                                    ? "◉"
                                    : "⊙";

                            button.setAttribute(
                                "aria-label",
                                showing
                                    ? "Hiện mật khẩu"
                                    : "Ẩn mật khẩu"
                            );
                        }
                    );

                }
            );


        /* =============================================
           PASSWORD STRENGTH
           ============================================= */

        const updatePasswordStrength = () => {
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

                strengthBar.style.background =
                    "";

                strengthText.textContent =
                    "Chưa nhập mật khẩu";

                return;
            }


            let score = 0;


            /* Độ dài cơ bản */
            if (value.length >= 8) {
                score++;
            }


            /* Độ dài tốt */
            if (value.length >= 12) {
                score++;
            }


            /* Có chữ thường */
            if (/[a-z]/.test(value)) {
                score++;
            }


            /* Có chữ hoa */
            if (/[A-Z]/.test(value)) {
                score++;
            }


            /* Có số */
            if (/[0-9]/.test(value)) {
                score++;
            }


            /* Có ký tự đặc biệt */
            if (
                /[^A-Za-z0-9]/.test(value)
            ) {
                score++;
            }


            if (score <= 2) {

                strengthBar.style.width =
                    "30%";

                strengthBar.style.background =
                    "var(--dashboard-danger)";

                strengthText.textContent =
                    "Mật khẩu yếu";

            } else if (score === 3) {

                strengthBar.style.width =
                    "60%";

                strengthBar.style.background =
                    "var(--dashboard-warning)";

                strengthText.textContent =
                    "Mật khẩu trung bình";

            } else {

                strengthBar.style.width =
                    "100%";

                strengthBar.style.background =
                    "var(--dashboard-success)";

                strengthText.textContent =
                    "Mật khẩu mạnh";
            }
        };


        /* =============================================
           CONFIRM PASSWORD
           ============================================= */

        const updatePasswordMatch = () => {
            if (
                !password
                || !confirmPassword
                || !matchMessage
            ) {
                return;
            }

            if (
                !confirmPassword.value
            ) {
                matchMessage.textContent =
                    (
                        "Nhập lại chính xác "
                        + "mật khẩu phía bên trái."
                    );

                matchMessage.style.color =
                    "";

                return;
            }

            if (
                password.value
                === confirmPassword.value
            ) {
                matchMessage.textContent =
                    "Mật khẩu đã khớp.";

                matchMessage.style.color =
                    "var(--dashboard-success)";

            } else {
                matchMessage.textContent =
                    "Mật khẩu chưa khớp.";

                matchMessage.style.color =
                    "var(--dashboard-danger)";
            }
        };


        password?.addEventListener(
            "input",
            () => {
                updatePasswordStrength();
                updatePasswordMatch();
            }
        );


        confirmPassword?.addEventListener(
            "input",
            updatePasswordMatch
        );

        /* =============================================
        CLEAR FORM
        ============================================= */

        clearButton?.addEventListener(
            "click",
            () => {

                if (fullNameInput) {
                    fullNameInput.value = "";
                }

                if (emailInput) {
                    emailInput.value = "";
                }

                if (phoneInput) {
                    phoneInput.value = "";
                }

                if (roleSelect) {
                    roleSelect.value = "";
                }

                if (statusSelect) {
                    statusSelect.value =
                        "ACTIVE";
                }

                if (password) {
                    password.value = "";
                    password.type = "password";
                }

                if (confirmPassword) {
                    confirmPassword.value = "";
                    confirmPassword.type =
                        "password";
                }


                /* Reset strength */

                if (strengthBar) {
                    strengthBar.style.width =
                        "0";

                    strengthBar.style.background =
                        "";
                }

                if (strengthText) {
                    strengthText.textContent =
                        "Chưa nhập mật khẩu";
                }


                /* Reset password match */

                if (matchMessage) {
                    matchMessage.textContent =
                        (
                            "Nhập lại chính xác "
                            + "mật khẩu phía bên trái."
                        );

                    matchMessage.style.color =
                        "";
                }


                /* Xóa trạng thái lỗi visual */

                document
                    .querySelectorAll(
                        ".form-control-wrap.has-error"
                    )
                    .forEach(
                        (field) => {
                            field.classList.remove(
                                "has-error"
                            );
                        }
                    );
                
                document
                    .querySelectorAll(
                        ".field-error"
                    )
                    .forEach(
                        (error) => {
                            error.style.display =
                                "none";
                        }
                    );

                /* Focus field đầu tiên */

                fullNameInput?.focus();

            }
        );

        /* =============================================
           FRONTEND VALIDATION
           ============================================= */

        form?.addEventListener(
            "submit",
            (event) => {

                if (
                    !form.checkValidity()
                ) {
                    event.preventDefault();

                    form.reportValidity();

                    return;
                }

                if (
                    password
                    && password.value.length < 8
                ) {
                    event.preventDefault();

                    password.focus();

                    return;
                }

                if (
                    password
                    && confirmPassword
                    && password.value
                        !== confirmPassword.value
                ) {
                    event.preventDefault();

                    confirmPassword.focus();

                    return;
                }

            }
        );

    }
);