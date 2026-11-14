document.addEventListener(
    "DOMContentLoaded",
    () => {

        /* =====================================================
           MOBILE NAVIGATION
           ===================================================== */

        const navToggle =
            document.getElementById("navToggle");

        const mainNav =
            document.getElementById("mainNav");


        const closeNavigation = () => {
            if (!mainNav || !navToggle) {
                return;
            }

            mainNav.classList.remove("is-open");

            navToggle.setAttribute(
                "aria-expanded",
                "false"
            );
        };


        if (navToggle && mainNav) {

            navToggle.addEventListener(
                "click",
                () => {

                    const isOpen =
                        mainNav.classList.toggle(
                            "is-open"
                        );

                    navToggle.setAttribute(
                        "aria-expanded",
                        String(isOpen)
                    );

                }
            );


            window.addEventListener(
                "resize",
                () => {

                    if (window.innerWidth > 900) {
                        closeNavigation();
                    }

                }
            );


            mainNav
                .querySelectorAll("a")
                .forEach((link) => {

                    link.addEventListener(
                        "click",
                        closeNavigation
                    );

                });

        }


        /* =====================================================
           SEARCH
           ===================================================== */

        const searchToggle =
            document.getElementById("searchToggle");

        const siteSearch =
            document.getElementById("siteSearch");

        const siteSearchInput =
            document.getElementById(
                "siteSearchInput"
            );


        const closeSearch = () => {

            if (!siteSearch || !searchToggle) {
                return;
            }

            siteSearch.classList.remove(
                "is-open"
            );

            searchToggle.setAttribute(
                "aria-expanded",
                "false"
            );

        };


        if (searchToggle && siteSearch) {

            searchToggle.addEventListener(
                "click",
                (event) => {

                    event.stopPropagation();

                    const isOpen =
                        siteSearch.classList.toggle(
                            "is-open"
                        );

                    searchToggle.setAttribute(
                        "aria-expanded",
                        String(isOpen)
                    );


                    if (
                        isOpen &&
                        siteSearchInput
                    ) {

                        window.setTimeout(
                            () => {
                                siteSearchInput.focus();
                            },
                            80
                        );

                    }

                }
            );


            siteSearch.addEventListener(
                "click",
                (event) => {
                    event.stopPropagation();
                }
            );


            siteSearch.addEventListener(
                "submit",
                (event) => {

                    event.preventDefault();

                    const query =
                        siteSearchInput
                            ?.value
                            .trim();

                    if (!query) {
                        return;
                    }

                    /*
                     * Search thật sẽ được nối backend
                     * ở module tìm kiếm sau.
                     */

                    console.log(
                        "VetMate search:",
                        query
                    );

                }
            );

        }


        /* =====================================================
        THEME
        ===================================================== */

        const themeToggle =
            document.getElementById("themeToggle");

        const themeMenu =
            document.getElementById("themeMenu");

        const themeIcon =
            document.getElementById("themeIcon");

        const themeOptions =
            document.querySelectorAll(
                ".theme-option"
            );


        const getPreferredTheme = () => {

            const savedTheme =
                localStorage.getItem(
                    "vetmate-theme"
                );


            if (
                savedTheme === "default" ||
                savedTheme === "light" ||
                savedTheme === "dark"
            ) {
                return savedTheme;
            }


            return "default";

        };


        const applyTheme = (theme) => {

            document.documentElement
                .setAttribute(
                    "data-theme",
                    theme
                );


            themeOptions.forEach(
                (option) => {

                    const isActive =
                        option.dataset.themeValue
                        === theme;


                    option.classList.toggle(
                        "is-active",
                        isActive
                    );

                }
            );


                if (!themeIcon) {
                    return;
                }


                if (theme === "light") {

                    themeIcon.className =
                        "bi bi-sunrise-fill";

                } else if (
                    theme === "dark"
                ) {

                    themeIcon.className =
                        "bi bi-moon-stars-fill";

                } else {

                    themeIcon.className =
                        "bi bi-sun-fill";

                }

            };


        const closeThemeMenu = () => {

            if (!themeMenu || !themeToggle) {
                return;
            }


            themeMenu.classList.remove(
                "is-open"
            );


            themeToggle.setAttribute(
                "aria-expanded",
                "false"
            );

        };


        applyTheme(
            getPreferredTheme()
        );


        if (themeToggle && themeMenu) {

            themeToggle.addEventListener(
                "click",
                (event) => {

                    event.stopPropagation();


                    const isOpen =
                        themeMenu.classList.toggle(
                            "is-open"
                        );


                    themeToggle.setAttribute(
                        "aria-expanded",
                        String(isOpen)
                    );

                }
            );


            themeMenu.addEventListener(
                "click",
                (event) => {

                    event.stopPropagation();

                }
            );

        }


        themeOptions.forEach(
            (option) => {

                option.addEventListener(
                    "click",
                    () => {

                        const selectedTheme =
                            option.dataset.themeValue;


                        localStorage.setItem(
                            "vetmate-theme",
                            selectedTheme
                        );


                        applyTheme(
                            selectedTheme
                        );


                        closeThemeMenu();

                    }
                );

            }
        );


        /*Submit*/
        const footerSubscribe =
            document.querySelector(
                ".footer-subscribe"
            );


        if (footerSubscribe) {

            footerSubscribe.addEventListener(
                "submit",
                (event) => {
                    event.preventDefault();
                }
            );

        }

        
        /* =====================================================
           ACCOUNT DROPDOWN
           ===================================================== */

        const accountToggle =
            document.getElementById("accountToggle");

        const accountMenu =
            document.getElementById("accountMenu");

        const closeAccountMenu = () => {
            if (!accountToggle || !accountMenu) {
                return;
            }

            accountMenu.hidden = true;

            accountToggle.setAttribute(
                "aria-expanded",
                "false"
            );
        };

        if (accountToggle && accountMenu) {

            accountToggle.addEventListener(
                "click",
                (event) => {
                    event.stopPropagation();

                    const shouldOpen = accountMenu.hidden;

                    closeSearch();
                    closeThemeMenu();
                    closeNavigation();

                    accountMenu.hidden = !shouldOpen;

                    accountToggle.setAttribute(
                        "aria-expanded",
                        String(shouldOpen)
                    );
                }
            );

            accountMenu.addEventListener(
                "click",
                (event) => {
                    event.stopPropagation();
                }
            );

            accountMenu
                .querySelectorAll(
                    "[data-account-placeholder]"
                )
                .forEach((button) => {
                    button.addEventListener(
                        "click",
                        () => {
                            closeAccountMenu();

                            window.alert(
                                "Chức năng này đang được phát triển."
                            );
                        }
                    );
                });
        }

        /* =====================================================
           CLICK OUTSIDE
           ===================================================== */

        document.addEventListener(
            "click",
            (event) => {

                const clickedInsideNav =
                    mainNav?.contains(
                        event.target
                    );

                const clickedNavToggle =
                    navToggle?.contains(
                        event.target
                    );


                if (
                    !clickedInsideNav &&
                    !clickedNavToggle
                ) {
                    closeNavigation();
                }


                const clickedInsideSearch =
                    siteSearch?.contains(
                        event.target
                    );

                const clickedSearchToggle =
                    searchToggle?.contains(
                        event.target
                    );


                if (
                    !clickedInsideSearch &&
                    !clickedSearchToggle
                ) {
                    closeSearch();
                }

                const clickedInsideTheme =
                    themeMenu?.contains(
                        event.target
                    );

                const clickedThemeToggle =
                    themeToggle?.contains(
                        event.target
                    );


                if (
                    !clickedInsideTheme &&
                    !clickedThemeToggle
                ) {
                    closeThemeMenu();
                }
                
                const clickedInsideAccount =
                    accountMenu?.contains(event.target);

                const clickedAccountToggle =
                    accountToggle?.contains(event.target);

                if (
                    !clickedInsideAccount &&
                    !clickedAccountToggle
                ) {
                    closeAccountMenu();
                }

            }
        );


        /* =====================================================
           ESC KEY
           ===================================================== */

        document.addEventListener(
            "keydown",
            (event) => {

                if (event.key !== "Escape") {
                    return;
                }

                closeNavigation();
                closeSearch();
                closeThemeMenu();
                closeAccountMenu();
            }
        );

    }
);