document.addEventListener(
    "DOMContentLoaded",
    () => {

        const triggers =
            document.querySelectorAll(
                "[data-user-menu-trigger]"
            );


        let activeMenu = null;
        let activeTrigger = null;
        let originalParent = null;
        let originalNextSibling = null;


        /* =============================================
           RESTORE MENU
           ============================================= */

        const restoreMenu = () => {

            if (
                !activeMenu
                || !originalParent
            ) {
                return;
            }


            if (
                originalNextSibling
                && originalNextSibling.parentNode
                    === originalParent
            ) {

                originalParent.insertBefore(
                    activeMenu,
                    originalNextSibling
                );

            } else {

                originalParent.appendChild(
                    activeMenu
                );

            }


            activeMenu.style.top = "";
            activeMenu.style.left = "";
        };


        /* =============================================
           CLOSE
           ============================================= */

        const closeMenu = () => {

            if (!activeMenu) {
                return;
            }


            activeMenu.hidden = true;


            activeTrigger?.setAttribute(
                "aria-expanded",
                "false"
            );


            restoreMenu();


            activeMenu = null;
            activeTrigger = null;
            originalParent = null;
            originalNextSibling = null;
        };


        /* =============================================
           POSITION
           ============================================= */

        const positionMenu = (
            trigger,
            menu
        ) => {

            const triggerRect =
                trigger.getBoundingClientRect();


            /*
             * Menu phải hiện trước để lấy
             * kích thước thật.
             */

            const menuRect =
                menu.getBoundingClientRect();


            const gap = 7;
            const edge = 12;


            /*
             * Mặc định:
             *
             *       ⋯
             *   ┌─────────┐
             *   │ menu    │
             *   └─────────┘
             */

            let left =
                triggerRect.right
                - menuRect.width;


            let top =
                triggerRect.bottom
                + gap;


            /*
             * Nếu menu vượt cạnh trái.
             */

            if (left < edge) {
                left = edge;
            }


            /*
             * Nếu vượt cạnh phải.
             */

            if (
                left
                + menuRect.width
                > window.innerWidth
                - edge
            ) {

                left =
                    window.innerWidth
                    - menuRect.width
                    - edge;
            }


            /*
             * Nếu phía dưới không đủ chỗ,
             * mở menu lên phía trên nút.
             */

            const spaceBelow =
                window.innerHeight
                - triggerRect.bottom;


            const spaceAbove =
                triggerRect.top;


            if (
                spaceBelow
                    < menuRect.height + gap
                &&
                spaceAbove
                    > menuRect.height + gap
            ) {

                top =
                    triggerRect.top
                    - menuRect.height
                    - gap;
            }


            /*
             * Safety để menu không vượt
             * khỏi màn hình.
             */

            if (top < edge) {
                top = edge;
            }


            if (
                top
                + menuRect.height
                > window.innerHeight
                - edge
            ) {

                top =
                    Math.max(
                        edge,
                        window.innerHeight
                        - menuRect.height
                        - edge
                    );
            }


            menu.style.left =
                `${Math.round(left)}px`;

            menu.style.top =
                `${Math.round(top)}px`;
        };


        /* =============================================
           OPEN
           ============================================= */

        const openMenu = (
            trigger,
            menu
        ) => {

            closeMenu();


            activeMenu = menu;
            activeTrigger = trigger;

            originalParent =
                menu.parentNode;

            originalNextSibling =
                menu.nextSibling;


            /*
             * Đây là phần quan trọng.
             *
             * Đưa dropdown ra khỏi table /
             * scroll container để menu không
             * làm thay đổi kích thước bảng.
             */

            document.body.appendChild(
                menu
            );


            menu.hidden = false;


            trigger.setAttribute(
                "aria-expanded",
                "true"
            );


            positionMenu(
                trigger,
                menu
            );
        };


        /* =============================================
           TRIGGERS
           ============================================= */

        triggers.forEach(
            (trigger) => {

                /*
                * Lưu menu gốc của từng nút.
                *
                * Sau khi mở, menu sẽ được chuyển
                * ra document.body nên không thể
                * query lại từ wrapper nữa.
                */
                const wrapper =
                    trigger.closest(
                        ".user-action-menu"
                    );

                const menu =
                    wrapper?.querySelector(
                        "[data-user-menu]"
                    );


                if (!menu) {
                    return;
                }


                trigger.addEventListener(
                    "click",
                    (event) => {

                        event.preventDefault();
                        event.stopPropagation();


                        /*
                        * Nếu chính menu của nút này
                        * đang mở → bấm ⋯ lần nữa
                        * sẽ đóng.
                        */
                        if (
                            activeTrigger === trigger
                            &&
                            activeMenu === menu
                        ) {

                            closeMenu();

                            return;
                        }


                        /*
                        * Nếu menu khác đang mở,
                        * openMenu() sẽ đóng menu đó
                        * trước rồi mở menu hiện tại.
                        */
                        openMenu(
                            trigger,
                            menu
                        );

                    }
                );

            }
        );


        /* =============================================
           CLICK OUTSIDE
           ============================================= */

        document.addEventListener(
            "click",
            (event) => {

                if (
                    activeMenu
                    &&
                    activeMenu.contains(
                        event.target
                    )
                ) {
                    return;
                }


                closeMenu();
            }
        );


        /* =============================================
           ESC
           ============================================= */

        document.addEventListener(
            "keydown",
            (event) => {

                if (
                    event.key === "Escape"
                    && activeMenu
                ) {

                    const triggerToFocus =
                        activeTrigger;

                    closeMenu();

                    triggerToFocus?.focus();
                }

            }
        );


        /* =============================================
           SCROLL
           ============================================= */

        window.addEventListener(
            "scroll",
            closeMenu,
            true
        );


        /* =============================================
           RESIZE
           ============================================= */

        window.addEventListener(
            "resize",
            closeMenu
        );

    }
);