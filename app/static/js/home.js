document.addEventListener(
    "DOMContentLoaded",
    () => {
        const carousel =
            document.querySelector(
                ".home-hero-visual"
            );

        const slides = [
            ...document.querySelectorAll(
                ".home-hero-slide"
            ),
        ];

        const dots = [
            ...document.querySelectorAll(
                ".home-hero-dots button"
            ),
        ];

        const previousButton =
            document.getElementById(
                "heroPrevious"
            );

        const nextButton =
            document.getElementById(
                "heroNext"
            );


        /* =====================================================
           GUARD
           ===================================================== */

        if (slides.length === 0) {
            return;
        }


        let currentSlide = 0;
        let automaticTimer = null;

        const slideInterval = 5000;


        /* =====================================================
           SHOW SLIDE
           ===================================================== */

        const showSlide = (index) => {
            currentSlide =
                (
                    index
                    + slides.length
                )
                % slides.length;


            slides.forEach(
                (slide, slideIndex) => {
                    const isActive =
                        slideIndex
                        === currentSlide;

                    slide.classList.toggle(
                        "is-active",
                        isActive
                    );

                    slide.setAttribute(
                        "aria-hidden",
                        isActive
                            ? "false"
                            : "true"
                    );
                }
            );


            dots.forEach(
                (dot, dotIndex) => {
                    const isActive =
                        dotIndex
                        === currentSlide;

                    dot.classList.toggle(
                        "is-active",
                        isActive
                    );

                    dot.setAttribute(
                        "aria-current",
                        isActive
                            ? "true"
                            : "false"
                    );
                }
            );
        };


        /* =====================================================
           NEXT / PREVIOUS
           ===================================================== */

        const showNextSlide = () => {
            showSlide(
                currentSlide + 1
            );
        };


        const showPreviousSlide = () => {
            showSlide(
                currentSlide - 1
            );
        };


        /* =====================================================
           AUTO PLAY
           ===================================================== */

        const stopAutomaticSlide = () => {
            if (automaticTimer === null) {
                return;
            }

            window.clearInterval(
                automaticTimer
            );

            automaticTimer = null;
        };


        const startAutomaticSlide = () => {
            stopAutomaticSlide();

            if (slides.length <= 1) {
                return;
            }

            automaticTimer =
                window.setInterval(
                    showNextSlide,
                    slideInterval
                );
        };


        const restartAutomaticSlide = () => {
            stopAutomaticSlide();
            startAutomaticSlide();
        };


        /* =====================================================
           ARROW BUTTONS
           ===================================================== */

        previousButton
            ?.addEventListener(
                "click",
                () => {
                    showPreviousSlide();
                    restartAutomaticSlide();
                }
            );


        nextButton
            ?.addEventListener(
                "click",
                () => {
                    showNextSlide();
                    restartAutomaticSlide();
                }
            );


        /* =====================================================
           DOTS
           ===================================================== */

        dots.forEach(
            (dot, dotIndex) => {
                dot.addEventListener(
                    "click",
                    () => {
                        const target =
                            Number(
                                dot.dataset.slide
                            );

                        showSlide(
                            Number.isInteger(target)
                                ? target
                                : dotIndex
                        );

                        restartAutomaticSlide();
                    }
                );
            }
        );



        /* =====================================================
           KEYBOARD
           Chỉ đổi slide khi focus đang ở carousel.
           Không bắt ArrowLeft/Right toàn trang.
           ===================================================== */

        carousel
            ?.addEventListener(
                "keydown",
                (event) => {
                    if (
                        event.key
                        === "ArrowLeft"
                    ) {
                        event.preventDefault();

                        showPreviousSlide();
                        restartAutomaticSlide();
                    }

                    if (
                        event.key
                        === "ArrowRight"
                    ) {
                        event.preventDefault();

                        showNextSlide();
                        restartAutomaticSlide();
                    }
                }
            );


        /* =====================================================
           PAGE VISIBILITY

           Khi chuyển tab thì dừng carousel để tránh timer
           chạy ngầm. Khi quay lại mới chạy tiếp.
           ===================================================== */

        document.addEventListener(
            "visibilitychange",
            () => {
                if (document.hidden) {
                    stopAutomaticSlide();
                } else {
                    restartAutomaticSlide();
                }
            }
        );


        /* =====================================================
           INITIALIZE
           ===================================================== */

        showSlide(0);
        startAutomaticSlide();
    }
);