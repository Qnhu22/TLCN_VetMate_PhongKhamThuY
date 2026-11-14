document.addEventListener(
    "DOMContentLoaded",
    () => {

        const loginForm =
            document.getElementById(
                "loginForm"
            );


        const emailInput =
            document.getElementById(
                "loginEmail"
            );


        const passwordInput =
            document.getElementById(
                "loginPassword"
            );


        const showPasswordCheck =
            document.getElementById(
                "showPasswordCheck"
            );


        const mascot =
            document.getElementById(
                "loginMascot"
            );


        const pupilLeft =
            document.getElementById(
                "mascotPupilLeft"
            );


        const pupilRight =
            document.getElementById(
                "mascotPupilRight"
            );


        /* =====================================================
           USERNAME / EMAIL
           ===================================================== */

        function updateMascotEyes() {

            if (
                !emailInput ||
                !pupilLeft ||
                !pupilRight
            ) {
                return;
            }


            const valueLength =
                emailInput.value.length;


            /*
             * Khi mới bắt đầu nhập:
             * nhìn hơi sang trái.
             *
             * Khi nhập dài hơn:
             * mắt từ từ nhìn sang phải.
             */
            const progress =
                Math.min(
                    valueLength / 28,
                    1
                );


            const x =
                -4 +
                progress * 8;


            const y = 3;


            pupilLeft.style.transform =
                `translate(${x}px, ${y}px)`;


            pupilRight.style.transform =
                `translate(${x}px, ${y}px)`;

        }


        function resetMascotEyes() {

            if (pupilLeft) {
                pupilLeft.style.transform =
                    "translate(0, 0)";
            }


            if (pupilRight) {
                pupilRight.style.transform =
                    "translate(0, 0)";
            }

        }


        if (
            emailInput &&
            mascot
        ) {

            emailInput.addEventListener(
                "focus",
                () => {

                    mascot.classList.add(
                        "is-typing"
                    );

                    updateMascotEyes();

                }
            );


            emailInput.addEventListener(
                "input",
                updateMascotEyes
            );


            emailInput.addEventListener(
                "blur",
                () => {

                    mascot.classList.remove(
                        "is-typing"
                    );

                    resetMascotEyes();

                }
            );

        }


        /* =====================================================
           PASSWORD STATE CONTROLLER
           ===================================================== */

        function updatePasswordMascot() {

            if (
                !mascot ||
                !passwordInput
            ) {
                return;
            }


            const passwordFocused =
                document.activeElement ===
                passwordInput;


            const passwordVisible =
                Boolean(
                    showPasswordCheck &&
                    showPasswordCheck.checked
                );


            /*
             * Luôn dựng lại state từ đầu.
             *
             * Đây là phần chống lỗi khi người dùng
             * tick/bỏ tick liên tục.
             */
            mascot.classList.remove(
                "is-covering",
                "is-peeking"
            );


            /*
             * Không ở ô password:
             * tay trở về vị trí ban đầu.
             */
            if (!passwordFocused) {
                return;
            }


            /*
             * Đang nhập password:
             * luôn che mắt.
             */
            mascot.classList.add(
                "is-covering"
            );


            /*
             * Nếu cho hiện password:
             * hé tay phải.
             */
            if (passwordVisible) {

                mascot.classList.add(
                    "is-peeking"
                );

            }

        }


        /* =====================================================
           PASSWORD FOCUS / BLUR
           ===================================================== */

        if (passwordInput) {

            passwordInput.addEventListener(
                "focus",
                updatePasswordMascot
            );


            passwordInput.addEventListener(
                "blur",
                () => {

                    /*
                     * Browser cần một khoảng rất ngắn
                     * để cập nhật activeElement.
                     */
                    window.setTimeout(
                        updatePasswordMascot,
                        80
                    );

                }
            );

        }


        /* =====================================================
           SHOW PASSWORD
           ===================================================== */

        if (
            showPasswordCheck &&
            passwordInput
        ) {

            showPasswordCheck.addEventListener(
                "change",
                () => {

                    const shouldShowPassword =
                        showPasswordCheck.checked;


                    passwordInput.type =
                        shouldShowPassword
                            ? "text"
                            : "password";


                    /*
                     * Sau khi tick checkbox,
                     * đưa focus trở lại password.
                     *
                     * Nhờ vậy mascot vẫn biết người dùng
                     * đang thao tác với mật khẩu.
                     */
                    passwordInput.focus({
                        preventScroll: true
                    });


                    updatePasswordMascot();

                }
            );

        }

    }
);