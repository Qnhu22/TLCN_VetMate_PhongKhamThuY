document.addEventListener(
    "DOMContentLoaded",
    () => {

        const avatarModal =
            document.getElementById(
                "accountAvatarModal"
            );

        const avatarForm =
            document.getElementById(
                "accountAvatarForm"
            );

        const avatarSource =
            document.getElementById(
                "avatarSource"
            );

        const presetAvatar =
            document.getElementById(
                "presetAvatar"
            );

        const avatarFile =
            document.getElementById(
                "avatarFile"
            );

        const avatarPreviewImage =
            document.getElementById(
                "avatarPreviewImage"
            );

        const avatarUploadZone =
            document.getElementById(
                "avatarUploadZone"
            );

        const avatarUploadFileName =
            document.getElementById(
                "avatarUploadFileName"
            );

        const avatarUploadError =
            document.getElementById(
                "avatarUploadError"
            );

        const saveAvatarButton =
            document.getElementById(
                "saveAvatarButton"
            );

        const avatarPresetOptions =
            document.querySelectorAll(
                "[data-avatar-preset]"
            );

        const currentPasswordError =
            document.getElementById(
                "currentPasswordError"
            );

        const passwordButton =
            document.getElementById(
                "openPasswordManager"
            );

        const passwordModal =
            document.getElementById(
                "accountPasswordModal"
            );

        const passwordForm =
            document.getElementById(
                "accountPasswordForm"
            );

        const currentPassword =
            document.getElementById(
                "currentPassword"
            );

        const newPassword =
            document.getElementById(
                "newPassword"
            );

        const confirmPassword =
            document.getElementById(
                "confirmPassword"
            );

        const passwordSubmit =
            document.getElementById(
                "confirmPasswordUpdate"
            );

        const passwordStrengthBar =
            document.getElementById(
                "passwordStrengthBar"
            );

        const passwordStrengthText =
            document.getElementById(
                "passwordStrengthText"
            );

        const passwordMatchMessage =
            document.getElementById(
                "passwordMatchMessage"
            );

        const newPasswordError =
            document.getElementById(
                "newPasswordError"
            );

        const roleButton =
            document.getElementById(
                "manageAccountRoles"
            );

        const roleModal =
            document.getElementById(
                "accountRoleModal"
            );
        
        const statusButton =
            document.getElementById(
                "manageAccountStatus"
            );

        const statusModal =
            document.getElementById(
                "accountStatusModal"
            );

        const statusForm =
            document.getElementById(
                "accountStatusForm"
            );

        const statusInputs =
            document.querySelectorAll(
                '#accountStatusForm input[name="status"]'
            );

        const statusSubmit =
            document.getElementById(
                "confirmAccountStatus"
            );

        const statusNote =
            document.getElementById(
                "accountStatusConfirmNote"
            );

        const statusNoteText =
            document.getElementById(
                "accountStatusConfirmText"
            );

        const page =
            document.getElementById(
                "accountDetailPage"
            );

        const form =
            document.getElementById(
                "accountDetailForm"
            );

        if (!page || !form) {
            return;
        }


        const editButton =
            document.getElementById(
                "toggleAccountEdit"
            );

        const cancelButton =
            document.getElementById(
                "cancelAccountEdit"
            );

        const editBanner =
            document.getElementById(
                "accountEditBanner"
            );

        const avatarButton =
            document.getElementById(
                "changeAvatarButton"
            );

        const fullName =
            document.getElementById(
                "fullName"
            );

        const phone =
            document.getElementById(
                "phone"
            );

        const fullNameError =
            document.getElementById(
                "fullNameError"
            );

        const phoneError =
            document.getElementById(
                "phoneError"
            );

        const editableFields =
            document.querySelectorAll(
                "[data-account-editable]"
            );

        const locks =
            document.querySelectorAll(
                "[data-edit-lock]"
            );

        const editOnly =
            document.querySelectorAll(
                ".account-edit-only"
            );

        const discardModal =
            document.getElementById(
                "discardAccountChangesModal"
            );

        const confirmDiscard =
            document.getElementById(
                "confirmDiscardAccountChanges"
            );

        const validateAvatarFile = (
            file
        ) => {

            const allowedTypes = [
                "image/jpeg",
                "image/png",
                "image/webp",
            ];

            const maxSize =
                5 * 1024 * 1024;

            if (
                !allowedTypes.includes(
                    file.type
                )
            ) {
                return (
                    "Chỉ hỗ trợ ảnh JPG, PNG hoặc WEBP."
                );
            }

            if (file.size > maxSize) {
                return (
                    "Dung lượng ảnh không được vượt quá 5 MB."
                );
            }

            return "";
        };


        const useUploadedAvatar = (
            file
        ) => {

            if (!file) {
                return;
            }

            const error =
                validateAvatarFile(file);

            if (error) {

                if (avatarUploadError) {
                    avatarUploadError.textContent =
                        error;

                    avatarUploadError.hidden =
                        false;
                }

                if (avatarFile) {
                    avatarFile.value = "";
                }

                if (saveAvatarButton) {
                    saveAvatarButton.disabled =
                        true;
                }

                return;
            }


            if (avatarUploadError) {
                avatarUploadError.hidden = true;
                avatarUploadError.textContent = "";
            }


            avatarPresetOptions.forEach(
                (option) => {
                    option.classList.remove(
                        "is-selected"
                    );
                }
            );


            if (avatarSource) {
                avatarSource.value = "upload";
            }

            if (presetAvatar) {
                presetAvatar.value = "";
            }

            if (avatarUploadFileName) {
                avatarUploadFileName.textContent =
                    file.name;
            }


            const objectUrl =
                URL.createObjectURL(file);

            if (avatarPreviewImage) {
                avatarPreviewImage.src =
                    objectUrl;

                avatarPreviewImage.onload =
                    () => {
                        URL.revokeObjectURL(
                            objectUrl
                        );
                    };
            }


            if (saveAvatarButton) {
                saveAvatarButton.disabled =
                    false;
            }

        };

        const originalAvatarSrc =
            avatarPreviewImage?.src ?? "";


        const resetAvatarModal = () => {

            if (avatarSource) {
                avatarSource.value = "";
            }

            if (presetAvatar) {
                presetAvatar.value = "";
            }

            if (avatarFile) {
                avatarFile.value = "";
            }

            if (avatarPreviewImage) {
                avatarPreviewImage.src =
                    originalAvatarSrc;
            }

            if (avatarUploadFileName) {
                avatarUploadFileName.textContent =
                    "Chưa có ảnh được chọn";
            }

            if (avatarUploadError) {
                avatarUploadError.hidden = true;
                avatarUploadError.textContent = "";
            }

            avatarPresetOptions.forEach(
                (option) => {
                    option.classList.remove(
                        "is-selected"
                    );
                }
            );

            if (saveAvatarButton) {
                saveAvatarButton.disabled = true;
            }

        };


        const openAvatarModal = () => {

            if (!avatarModal) {
                return;
            }

            resetAvatarModal();

            avatarModal.hidden = false;

            document.body.classList.add(
                "modal-open"
            );

        };


        const closeAvatarModal = () => {

            if (!avatarModal) {
                return;
            }

            avatarModal.hidden = true;

            resetAvatarModal();

            document.body.classList.remove(
                "modal-open"
            );

        };

        let editing =
            page.dataset.editing
                === "true";

        let original = {};


        const captureOriginal = () => {

            original = {
                fullName:
                    fullName?.value ?? "",

                phone:
                    phone?.value ?? "",
            };

        };

        const hasChanges = () => {

            return (
                (
                    fullName?.value ?? ""
                ) !== original.fullName
                ||
                (
                    phone?.value ?? ""
                ) !== original.phone
            );

        };

        const updateSubmitState = () => {

            if (!editButton) {
                return;
            }


            /*
            * Khi chưa ở Edit Mode thì đây là
            * nút "Chỉnh sửa", luôn phải bấm được.
            */
            if (!editing) {

                editButton.disabled = false;

                return;
            }


            /*
            * Khi đang Edit Mode, chỉ bật
            * "Cập nhật" nếu dữ liệu thật sự đổi.
            */
            editButton.disabled =
                !hasChanges();

        };


        const clearFieldError = (
            input,
            errorElement
        ) => {

            input
                ?.closest(
                    ".account-input-shell"
                )
                ?.classList.remove(
                    "has-error"
                );

            if (errorElement) {
                errorElement.hidden = true;
                errorElement.textContent = "";
            }

        };


        const showFieldError = (
            input,
            errorElement,
            message
        ) => {

            input
                ?.closest(
                    ".account-input-shell"
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


        const clearValidation = () => {

            clearFieldError(
                fullName,
                fullNameError
            );

            clearFieldError(
                phone,
                phoneError
            );

        };


        const setEditing = (
            enabled
        ) => {

            editing = enabled;

            page.dataset.editing =
                enabled
                    ? "true"
                    : "false";


            editableFields.forEach(
                (field) => {

                    field.readOnly =
                        !enabled;


                    const shell =
                        field.closest(
                            ".account-input-shell"
                        );


                    shell?.classList.toggle(
                        "is-editable",
                        enabled
                    );

                }
            );

            locks.forEach(
                (lock) => {

                    lock.hidden =
                        enabled;

                }
            );


            editOnly.forEach(
                (element) => {

                    element.hidden =
                        !enabled;

                }
            );


            if (avatarButton) {
                avatarButton.hidden =
                    !enabled;
            }


            if (editBanner) {
                editBanner.hidden =
                    !enabled;
            }


            if (cancelButton) {
                cancelButton.hidden =
                    !enabled;
            }


            if (editButton) {

                editButton.textContent =
                    enabled
                        ? "Cập nhật"
                        : "Chỉnh sửa";

            }
            updateSubmitState();

        };


        const restoreOriginal = () => {

            if (fullName) {
                fullName.value =
                    original.fullName;
            }

            if (phone) {
                phone.value =
                    original.phone;
            }

            clearValidation();
            updateSubmitState();

        };


        const validate = () => {

            clearValidation();

            let valid = true;


            const fullNameValue =
                fullName?.value.trim()
                ?? "";

            const phoneValue =
                phone?.value.trim()
                ?? "";


            if (!fullNameValue) {

                showFieldError(
                    fullName,
                    fullNameError,
                    "Họ và tên không được để trống."
                );

                valid = false;

            } else if (
                fullNameValue.length < 2
            ) {

                showFieldError(
                    fullName,
                    fullNameError,
                    "Họ và tên phải có ít nhất 2 ký tự."
                );

                valid = false;

            } else if (
                fullNameValue.length > 150
            ) {

                showFieldError(
                    fullName,
                    fullNameError,
                    "Họ và tên không được vượt quá 150 ký tự."
                );

                valid = false;
            }


            if (
                phoneValue
                &&
                !/^\d{10}$/.test(
                    phoneValue
                )
            ) {

                showFieldError(
                    phone,
                    phoneError,
                    "Số điện thoại phải gồm đúng 10 chữ số."
                );

                valid = false;
            }


            return valid;
        };


        const openDiscardModal = () => {

            if (!discardModal) {
                return;
            }

            discardModal.hidden =
                false;

            document.body.classList.add(
                "modal-open"
            );

        };


        const closeDiscardModal = () => {

            if (!discardModal) {
                return;
            }

            discardModal.hidden =
                true;

            document.body.classList.remove(
                "modal-open"
            );

        };


        /* PHONE */

        phone?.addEventListener(
            "input",
            () => {

                phone.value =
                    phone.value
                        .replace(
                            /\D/g,
                            ""
                        )
                        .slice(
                            0,
                            10
                        );

                clearFieldError(
                    phone,
                    phoneError
                );
                updateSubmitState();
            }
        );


        fullName?.addEventListener(
            "input",
            () => {

                clearFieldError(
                    fullName,
                    fullNameError
                );

                updateSubmitState();

            }
        );


        /* EDIT / UPDATE */

        editButton?.addEventListener(
            "click",
            () => {

                if (!editing) {

                    captureOriginal();

                    setEditing(true);

                    return;
                }


                if (!validate()) {
                    return;
                }


                form.submit();

            }
        );


        /* CANCEL */

        cancelButton?.addEventListener(
            "click",
            () => {

                if (hasChanges()) {

                    openDiscardModal();

                    return;
                }


                restoreOriginal();

                setEditing(false);

            }
        );


        confirmDiscard?.addEventListener(
            "click",
            () => {

                restoreOriginal();

                closeDiscardModal();

                setEditing(false);

            }
        );


        document
            .querySelectorAll(
                "[data-discard-close]"
            )
            .forEach(
                (element) => {

                    element.addEventListener(
                        "click",
                        closeDiscardModal
                    );

                }
            );
        
        const openRoleModal = () => {

            if (!roleModal) {
                return;
            }

            roleModal.hidden = false;

            document.body.classList.add(
                "modal-open"
            );

        };


        const closeRoleModal = () => {

            if (!roleModal) {
                return;
            }

            roleModal.hidden = true;

            document.body.classList.remove(
                "modal-open"
            );

        };

        roleButton?.addEventListener(
            "click",
            () => {
                openRoleModal();
            }
        );


        document
            .querySelectorAll(
                "[data-role-modal-close]"
            )
            .forEach(
                (element) => {

                    element.addEventListener(
                        "click",
                        closeRoleModal
                    );

                }
            );

        const resetStatusModal = () => {

            statusInputs.forEach(
                (input) => {

                    input.checked = false;

                }
            );


            if (statusSubmit) {
                statusSubmit.disabled = true;
            }


            if (statusNote) {
                statusNote.hidden = true;
            }


            if (statusNoteText) {
                statusNoteText.textContent = "";
            }

        };


        const openStatusModal = () => {

            if (!statusModal) {
                return;
            }


            resetStatusModal();


            statusModal.hidden = false;


            document.body.classList.add(
                "modal-open"
            );

        };


        const closeStatusModal = () => {

            if (!statusModal) {
                return;
            }


            statusModal.hidden = true;


            resetStatusModal();


            document.body.classList.remove(
                "modal-open"
            );

        };

        statusButton?.addEventListener(
            "click",
            () => {

                openStatusModal();

            }
        );


        document
            .querySelectorAll(
                "[data-status-modal-close]"
            )
            .forEach(
                (element) => {

                    element.addEventListener(
                        "click",
                        closeStatusModal
                    );

                }
            );

        const statusMessages = {

            ACTIVE:
                "Tài khoản sẽ được phép đăng nhập "
                + "và sử dụng hệ thống trở lại.",

            LOCKED:
                "Tài khoản sẽ không thể đăng nhập "
                + "cho đến khi được mở khóa.",

            INACTIVE:
                "Tài khoản sẽ được đánh dấu ngừng "
                + "hoạt động và không thể đăng nhập.",

        };


        statusInputs.forEach(
            (input) => {

                input.addEventListener(
                    "change",
                    () => {

                        if (!input.checked) {
                            return;
                        }


                        if (statusSubmit) {
                            statusSubmit.disabled =
                                false;
                        }


                        if (
                            statusNote
                            &&
                            statusNoteText
                        ) {

                            statusNoteText.textContent =
                                statusMessages[
                                    input.value
                                ] ?? "";

                            statusNote.hidden = false;

                        }

                    }
                );

            }
        );

        const resetPasswordModal = () => {

            if (currentPassword) {
                currentPassword.value = "";
                currentPassword.type = "password";
            }

            if (newPassword) {
                newPassword.value = "";
                newPassword.type = "password";
            }

            if (confirmPassword) {
                confirmPassword.value = "";
                confirmPassword.type = "password";
            }


            if (passwordStrengthBar) {
                passwordStrengthBar.style.width = "0";
                passwordStrengthBar.style.background = "";
            }


            if (passwordStrengthText) {
                passwordStrengthText.textContent =
                    "Chưa nhập mật khẩu";
            }


            if (passwordMatchMessage) {
                passwordMatchMessage.textContent =
                    "Nhập lại chính xác mật khẩu mới.";

                passwordMatchMessage.style.color = "";
            }


            if (newPasswordError) {
                newPasswordError.hidden = true;
                newPasswordError.textContent = "";
            }

            if (currentPasswordError) {
                currentPasswordError.hidden = true;
                currentPasswordError.textContent = "";
            }

            newPassword
                ?.closest(
                    ".password-modal-input"
                )
                ?.classList.remove(
                    "has-error"
                );


            if (passwordSubmit) {
                passwordSubmit.disabled = true;
            }

        };


        const openPasswordModal = () => {

            if (!passwordModal) {
                return;
            }


            resetPasswordModal();


            passwordModal.hidden = false;


            document.body.classList.add(
                "modal-open"
            );

        };


        const closePasswordModal = () => {

            if (!passwordModal) {
                return;
            }


            passwordModal.hidden = true;


            resetPasswordModal();


            document.body.classList.remove(
                "modal-open"
            );

        };

        const updatePasswordStrength = () => {

            if (
                !newPassword
                ||
                !passwordStrengthBar
                ||
                !passwordStrengthText
            ) {
                return;
            }


            const value =
                newPassword.value;


            if (!value) {

                passwordStrengthBar.style.width =
                    "0";

                passwordStrengthBar.style.background =
                    "";

                passwordStrengthText.textContent =
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

            if (/[0-9]/.test(value)) {
                score++;
            }

            if (/[^A-Za-z0-9]/.test(value)) {
                score++;
            }


            if (score <= 2) {

                passwordStrengthBar.style.width =
                    "30%";

                passwordStrengthBar.style.background =
                    "var(--dashboard-danger)";

                passwordStrengthText.textContent =
                    "Mật khẩu yếu";

            } else if (score === 3) {

                passwordStrengthBar.style.width =
                    "60%";

                passwordStrengthBar.style.background =
                    "var(--dashboard-warning)";

                passwordStrengthText.textContent =
                    "Mật khẩu trung bình";

            } else {

                passwordStrengthBar.style.width =
                    "100%";

                passwordStrengthBar.style.background =
                    "var(--dashboard-success)";

                passwordStrengthText.textContent =
                    "Mật khẩu mạnh";

            }

        };

        const validatePasswordModal = () => {

            let valid = true;


            const newValue =
                newPassword?.value ?? "";

            const confirmValue =
                confirmPassword?.value ?? "";

            const currentValue =
                currentPassword?.value ?? "";


            newPassword
                ?.closest(
                    ".password-modal-input"
                )
                ?.classList.remove(
                    "has-error"
                );


            if (newPasswordError) {
                newPasswordError.hidden = true;
                newPasswordError.textContent = "";
            }


            if (newValue.length < 8) {

                newPassword
                    ?.closest(
                        ".password-modal-input"
                    )
                    ?.classList.add(
                        "has-error"
                    );


                if (newPasswordError) {
                    newPasswordError.textContent =
                        "Mật khẩu phải có ít nhất 8 ký tự.";

                    newPasswordError.hidden =
                        false;
                }

                valid = false;
            }


            if (
                confirmValue
                !== newValue
            ) {

                if (passwordMatchMessage) {
                    passwordMatchMessage.textContent =
                        "Mật khẩu xác nhận chưa khớp.";

                    passwordMatchMessage.style.color =
                        "var(--dashboard-danger)";
                }

                valid = false;

            } else if (
                confirmValue
                &&
                newValue
            ) {

                if (passwordMatchMessage) {
                    passwordMatchMessage.textContent =
                        "Mật khẩu xác nhận đã khớp.";

                    passwordMatchMessage.style.color =
                        "var(--dashboard-success)";
                }

            } else {

                if (passwordMatchMessage) {
                    passwordMatchMessage.textContent =
                        "Nhập lại chính xác mật khẩu mới.";

                    passwordMatchMessage.style.color =
                        "";
                }

                valid = false;
            }


            /*
            * Nếu currentPassword tồn tại
            * nghĩa là đang đổi password
            * của chính admin.
            */
            if (
                currentPassword
                &&
                !currentValue
            ) {
                valid = false;
            }


            if (passwordSubmit) {
                passwordSubmit.disabled =
                    !valid;
            }


            return valid;
        };

        newPassword?.addEventListener(
            "input",
            () => {

                updatePasswordStrength();
                validatePasswordModal();

            }
        );


        confirmPassword?.addEventListener(
            "input",
            validatePasswordModal
        );


        currentPassword?.addEventListener(
            "input",
            () => {

                if (currentPasswordError) {
                    currentPasswordError.hidden = true;
                    currentPasswordError.textContent = "";
                }

                currentPassword
                    .closest(
                        ".password-modal-input"
                    )
                    ?.classList.remove(
                        "has-error"
                    );

                validatePasswordModal();

            }
        );

        document
            .querySelectorAll(
                "[data-password-toggle]"
            )
            .forEach(
                (button) => {

                    button.addEventListener(
                        "click",
                        () => {

                            const targetId =
                                button.dataset.passwordToggle;

                            const input =
                                document.getElementById(
                                    targetId
                                );


                            if (!input) {
                                return;
                            }


                            const showing =
                                input.type === "text";


                            input.type =
                                showing
                                    ? "password"
                                    : "text";


                            button.textContent =
                                showing
                                    ? "👁"
                                    : "◉";

                        }
                    );

                }
            );

        passwordButton?.addEventListener(
            "click",
            openPasswordModal
        );


        document
            .querySelectorAll(
                "[data-password-modal-close]"
            )
            .forEach(
                (element) => {

                    element.addEventListener(
                        "click",
                        closePasswordModal
                    );

                }
            );

        passwordForm?.addEventListener(
            "submit",
            (event) => {

                if (
                    !validatePasswordModal()
                ) {

                    event.preventDefault();

                }

            }
        );

        avatarPresetOptions.forEach(
            (option) => {

                option.addEventListener(
                    "click",
                    () => {

                        const value =
                            option.dataset.avatarPreset;

                        if (!value) {
                            return;
                        }

                        avatarPresetOptions.forEach(
                            (item) => {
                                item.classList.remove(
                                    "is-selected"
                                );
                            }
                        );

                        option.classList.add(
                            "is-selected"
                        );

                        if (avatarSource) {
                            avatarSource.value =
                                "preset";
                        }

                        if (presetAvatar) {
                            presetAvatar.value =
                                value;
                        }

                        if (avatarFile) {
                            avatarFile.value = "";
                        }

                        if (avatarUploadFileName) {
                            avatarUploadFileName.textContent =
                                "Chưa có ảnh được chọn";
                        }

                        const image =
                            option.querySelector("img");

                        if (
                            image
                            &&
                            avatarPreviewImage
                        ) {
                            avatarPreviewImage.src =
                                image.src;
                        }

                        if (saveAvatarButton) {
                            saveAvatarButton.disabled =
                                false;
                        }

                    }
                );

            }
        );

        avatarFile?.addEventListener(
            "change",
            () => {

                const file =
                    avatarFile.files?.[0];

                if (file) {
                    useUploadedAvatar(file);
                }

            }
        );

        avatarUploadZone?.addEventListener(
            "dragover",
            (event) => {

                event.preventDefault();

                avatarUploadZone.classList.add(
                    "is-dragging"
                );

            }
        );


        avatarUploadZone?.addEventListener(
            "dragleave",
            () => {

                avatarUploadZone.classList.remove(
                    "is-dragging"
                );

            }
        );


        avatarUploadZone?.addEventListener(
            "drop",
            (event) => {

                event.preventDefault();

                avatarUploadZone.classList.remove(
                    "is-dragging"
                );

                const file =
                    event.dataTransfer
                        ?.files?.[0];

                if (!file) {
                    return;
                }

                const transfer =
                    new DataTransfer();

                transfer.items.add(file);

                avatarFile.files =
                    transfer.files;

                useUploadedAvatar(file);

            }
        );

        avatarButton?.addEventListener(
            "click",
            openAvatarModal
        );


        document
            .querySelectorAll(
                "[data-avatar-modal-close]"
            )
            .forEach(
                (element) => {

                    element.addEventListener(
                        "click",
                        closeAvatarModal
                    );

                }
            );

        document.addEventListener(
            "paste",
            (event) => {

                if (
                    !avatarModal
                    || avatarModal.hidden
                ) {
                    return;
                }

                const items =
                    event.clipboardData?.items;

                if (!items) {
                    return;
                }

                const imageItem =
                    Array.from(items).find(
                        (item) =>
                            item.type.startsWith(
                                "image/"
                            )
                    );

                if (!imageItem) {
                    return;
                }

                const blob =
                    imageItem.getAsFile();

                if (!blob) {
                    return;
                }

                const extensionMap = {
                    "image/jpeg": "jpg",
                    "image/png": "png",
                    "image/webp": "webp",
                };

                const extension =
                    extensionMap[blob.type];

                if (!extension) {
                    return;
                }

                const file =
                    new File(
                        [blob],
                        `avatar-pasted.${extension}`,
                        {
                            type: blob.type,
                        }
                    );

                const transfer =
                    new DataTransfer();

                transfer.items.add(file);

                if (avatarFile) {
                    avatarFile.files =
                        transfer.files;
                }

                useUploadedAvatar(file);

                event.preventDefault();
            }
        );

        /* ESC */

        document.addEventListener(
            "keydown",
            (event) => {

                if (
                    event.key !== "Escape"
                ) {
                    return;
                }


                if (
                    discardModal
                    &&
                    !discardModal.hidden
                ) {

                    closeDiscardModal();

                    return;
                }

                if (
                    roleModal
                    &&
                    !roleModal.hidden
                ) {

                    closeRoleModal();

                    return;
                }

                if (
                    statusModal
                    &&
                    !statusModal.hidden
                ) {

                    closeStatusModal();

                    return;
                }

                if (
                    passwordModal
                    &&
                    !passwordModal.hidden
                ) {

                    closePasswordModal();

                    return;
                }

                if (
                    avatarModal
                    &&
                    !avatarModal.hidden
                ) {
                    closeAvatarModal();
                    return;
                }

                if (!editing) {
                    return;
                }


                if (hasChanges()) {

                    openDiscardModal();

                } else {

                    setEditing(false);

                }

            }
        );


        captureOriginal();
        setEditing(editing);
        if (
            passwordModal
            &&
            passwordModal.dataset.openOnLoad
                === "true"
        ) {

            passwordModal.hidden = false;

            document.body.classList.add(
                "modal-open"
            );

        }
    }
);