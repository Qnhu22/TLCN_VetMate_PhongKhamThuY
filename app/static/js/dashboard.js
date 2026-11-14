document.addEventListener("DOMContentLoaded", () => {

    /* =====================================================
       ELEMENTS
       ===================================================== */

    const root = document.documentElement;

    const sidebar = document.getElementById(
        "dashboardSidebar"
    );

    // Desktop: thu gọn / mở rộng sidebar.
    const sidebarToggle = document.getElementById(
        "sidebarToggle"
    );

    // Tablet/mobile: mở sidebar dạng drawer.
    const sidebarOpen = document.getElementById(
        "sidebarOpen"
    );

    const sidebarClose = document.getElementById(
        "sidebarClose"
    );

    const overlay = document.getElementById(
        "dashboardOverlay"
    );

    const themeToggle = document.getElementById(
        "themeToggle"
    );

    const profileTrigger = document.getElementById(
        "profileTrigger"
    );

    const profileDropdown = document.getElementById(
        "profileDropdown"
    );

    const searchInput = document.querySelector(
        ".topbar-search input"
    );

    const welcomeMascot = document.querySelector(
        ".dashboard-welcome-mascot"
    );

    const mascotMessage = document.querySelector(
        ".mascot-message"
    );


    /* =====================================================
       SIDEBAR
       ===================================================== */

    const openSidebar = () => {
        if (!sidebar) {
            return;
        }

        sidebar.classList.add(
            "is-open"
        );

        overlay?.classList.add(
            "is-visible"
        );

        document.body.classList.add(
            "sidebar-open"
        );
    };


    const closeSidebar = () => {
        if (!sidebar) {
            return;
        }

        sidebar.classList.remove(
            "is-open"
        );

        overlay?.classList.remove(
            "is-visible"
        );

        document.body.classList.remove(
            "sidebar-open"
        );
    };


    /* Desktop sidebar collapse */

    sidebarToggle?.addEventListener(
        "click",
        () => {
            document.body.classList.toggle(
                "sidebar-collapsed"
            );
        }
    );


    /* Tablet / mobile sidebar drawer */

    sidebarOpen?.addEventListener(
        "click",
        openSidebar
    );

    sidebarClose?.addEventListener(
        "click",
        closeSidebar
    );

    overlay?.addEventListener(
        "click",
        closeSidebar
    );


    /* =====================================================
       PROFILE DROPDOWN
       ===================================================== */

    const closeProfileDropdown = () => {
        if (
            !profileDropdown
            || !profileTrigger
        ) {
            return;
        }

        profileDropdown.hidden = true;

        profileTrigger.setAttribute(
            "aria-expanded",
            "false"
        );
    };


    const toggleProfileDropdown = () => {
        if (
            !profileDropdown
            || !profileTrigger
        ) {
            return;
        }

        const willOpen =
            profileDropdown.hidden;

        profileDropdown.hidden =
            !willOpen;

        profileTrigger.setAttribute(
            "aria-expanded",
            String(willOpen)
        );
    };


    profileTrigger?.addEventListener(
        "click",
        (event) => {
            event.stopPropagation();

            toggleProfileDropdown();
        }
    );


    profileDropdown?.addEventListener(
        "click",
        (event) => {
            event.stopPropagation();
        }
    );


    document.addEventListener(
        "click",
        closeProfileDropdown
    );


    /* =====================================================
       MASCOT MESSAGE
       ===================================================== */

    let mascotTimer = null;


    function showMascotMessage(
        message,
        duration = 2400
    ) {
        if (!mascotMessage) {
            return;
        }

        clearTimeout(
            mascotTimer
        );

        mascotMessage.textContent =
            message;

        mascotMessage.classList.add(
            "is-visible"
        );

        mascotTimer = setTimeout(
            () => {
                mascotMessage.classList.remove(
                    "is-visible"
                );
            },
            duration
        );
    }


    /* =====================================================
       MASCOT WELCOME
       ===================================================== */

    const userName =
        welcomeMascot?.dataset.userName
        || "bạn";


    setTimeout(
        () => {
            showMascotMessage(
                `Xin chào ${userName}! Chúc bạn làm việc hiệu quả ✨`,
                3500
            );
        },
        450
    );


    /* =====================================================
       THEME
       default → light → dark
       ===================================================== */

    const THEME_KEY =
        "vetmate-theme";

    const themes = [
        "default",
        "light",
        "dark",
    ];


    const getSavedTheme = () => {
        const savedTheme =
            localStorage.getItem(
                THEME_KEY
            );

        if (
            savedTheme
            && themes.includes(
                savedTheme
            )
        ) {
            return savedTheme;
        }

        return "default";
    };


    const getThemeMessage = (
        theme
    ) => {
        if (theme === "dark") {
            return "Tối rồi, dịu mắt hơn nha! 🌙";
        }

        if (theme === "light") {
            return "Sáng sủa hơn rồi đó! ✨";
        }

        return "Về màu VetMate quen thuộc rồi!";
    };


    const updateThemeButton = (
        theme
    ) => {
        if (!themeToggle) {
            return;
        }

        if (theme === "dark") {
            themeToggle.textContent = "☾";
            themeToggle.title =
                "Giao diện tối";
            return;
        }

        if (theme === "light") {
            themeToggle.textContent = "◒";
            themeToggle.title =
                "Giao diện sáng";
            return;
        }

        themeToggle.textContent = "☀";
        themeToggle.title =
            "Giao diện mặc định";
    };


    const applyTheme = (
        theme,
        showMessage = false
    ) => {
        root.dataset.theme =
            theme;

        localStorage.setItem(
            THEME_KEY,
            theme
        );

        updateThemeButton(
            theme
        );

        if (showMessage) {
            showMascotMessage(
                getThemeMessage(
                    theme
                )
            );
        }
    };


    applyTheme(
        getSavedTheme()
    );


    themeToggle?.addEventListener(
        "click",
        () => {
            const currentTheme =
                root.dataset.theme
                || "default";

            const currentIndex =
                themes.indexOf(
                    currentTheme
                );

            const nextTheme =
                themes[
                    (
                        currentIndex + 1
                    )
                    % themes.length
                ];

            applyTheme(
                nextTheme,
                true
            );
        }
    );


    /* =====================================================
       CTRL + K SEARCH
       ===================================================== */

    document.addEventListener(
        "keydown",
        (event) => {

            const isSearchShortcut =
                event.ctrlKey
                && event.key
                    .toLowerCase()
                    === "k";

            if (
                isSearchShortcut
                && searchInput
            ) {
                event.preventDefault();

                searchInput.focus();
                searchInput.select();
            }


            if (
                event.key === "Escape"
            ) {
                closeSidebar();

                closeProfileDropdown();

                searchInput?.blur();
            }
        }
    );


    /* =====================================================
       MASCOT REACTIONS
       ===================================================== */

    document
        .querySelectorAll(
            ".dashboard-primary-button"
        )
        .forEach(
            (button) => {
                button.addEventListener(
                    "mouseenter",
                    () => {
                        showMascotMessage(
                            "Tạo tài khoản mới hả? Mình phụ nhé! 🐾"
                        );
                    }
                );
            }
        );


    document
        .querySelectorAll(
            ".sidebar-logout, .profile-dropdown-logout"
        )
        .forEach(
            (button) => {
                button.addEventListener(
                    "mouseenter",
                    () => {
                        showMascotMessage(
                            "Xong việc rồi hả? Hẹn gặp lại nha! 👋"
                        );
                    }
                );
            }
        );


    document
        .querySelectorAll(
            ".stat-card"
        )
        .forEach(
            (card) => {

                card.addEventListener(
                    "mouseenter",
                    () => {
                        card.classList.add(
                            "is-highlighted"
                        );
                    }
                );

                card.addEventListener(
                    "mouseleave",
                    () => {
                        card.classList.remove(
                            "is-highlighted"
                        );
                    }
                );

            }
        );


    /* =====================================================
        DASHBOARD TOASTS
        ===================================================== */

        const dashboardToasts =
            document.querySelectorAll(
                "[data-dashboard-toast]"
            );


        const closeToast = (
            toast
        ) => {
            if (!toast) {
                return;
            }

            toast.classList.add(
                "is-leaving"
            );

            setTimeout(
                () => {
                    toast.remove();
                },
                180
            );
        };


        dashboardToasts.forEach(
            (toast) => {

                const closeButton =
                    toast.querySelector(
                        ".dashboard-toast-close"
                    );

                closeButton?.addEventListener(
                    "click",
                    () => {
                        closeToast(
                            toast
                        );
                    }
                );


                setTimeout(
                    () => {
                        closeToast(
                            toast
                        );
                    },
                    4500
                );

            }
        );

    /* =====================================================
       RESPONSIVE SAFETY
       ===================================================== */

    window.addEventListener(
        "resize",
        () => {

            if (
                window.innerWidth > 1024
            ) {
                closeSidebar();
            }

            if (
                window.innerWidth <= 1024
            ) {
                document.body.classList.remove(
                    "sidebar-collapsed"
                );
            }

        }
    );

});