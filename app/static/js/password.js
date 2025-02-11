document.addEventListener("DOMContentLoaded", async function () {
    const passwordInput = document.getElementById("password-input");
    const savePasswordBtn = document.getElementById("save-password-btn");
    const passwordToggle = document.getElementById("password-toggle");
    const toggleStatus = document.getElementById("toggle-status");
    const forgotPasswordLink = document.getElementById("forgot-password");

    let isPasswordSet = false; // Whether a password is already saved
    let failedAttempts = 0;
    const MAX_ATTEMPTS = 3;
    const LOCKOUT_TIME = 30 * 1000; // 30 seconds cooldown

    // Load protection status from the backend
    async function loadProtectionStatus() {
        try {
            const response = await fetch("/get_protection_status");
            const data = await response.json();
            passwordToggle.checked = data.enabled;
            toggleStatus.textContent = `Password Protection: ${data.enabled ? "ON" : "OFF"}`;
            isPasswordSet = data.password_set; // Assumes backend returns a flag "password_set"
            if (isPasswordSet) {
                passwordInput.value = "";
                passwordInput.placeholder = "Password Already Set";
                passwordInput.disabled = true;
                savePasswordBtn.disabled = true;
            } else {
                passwordInput.disabled = false;
                savePasswordBtn.disabled = false;
                passwordInput.placeholder = "Enter password";
            }
        } catch (error) {
            console.error("Failed to load password status:", error);
        }
    }

    await loadProtectionStatus();

    // Validate password strength: at least 8 characters, one lowercase, one uppercase, one digit, and one special character.
    function validatePasswordStrength(password) {
        const regex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[\W_]).{8,}$/;
        return regex.test(password);
    }

    // Show a visual indicator of password strength
    function showPasswordStrengthIndicator(password) {
        const strengthBar = document.getElementById("password-strength");
        const strengthText = document.getElementById("password-strength-text");

        let strength = 0;
        if (password.length >= 8) strength++;
        if (/[A-Z]/.test(password)) strength++;
        if (/[a-z]/.test(password)) strength++;
        if (/\d/.test(password)) strength++;
        if (/[\W_]/.test(password)) strength++;

        const percentage = (strength / 5) * 100;
        strengthBar.style.width = `${percentage}%`;

        if (strength <= 2) {
            strengthText.textContent = "Weak";
            strengthBar.style.backgroundColor = "red";
        } else if (strength === 3) {
            strengthText.textContent = "Moderate";
            strengthBar.style.backgroundColor = "orange";
        } else if (strength === 4) {
            strengthText.textContent = "Strong";
            strengthBar.style.backgroundColor = "yellowgreen";
        } else if (strength === 5) {
            strengthText.textContent = "Very Strong";
            strengthBar.style.backgroundColor = "green";
        }
    }

    // Monitor input changes for real‑time feedback on password strength
    passwordInput.addEventListener("input", function () {
        showPasswordStrengthIndicator(passwordInput.value);
    });

    function lockout() {
        passwordToggle.disabled = true;
        setTimeout(() => {
            passwordToggle.disabled = false;
            failedAttempts = 0;
        }, LOCKOUT_TIME);
    }

    // Save password when the save button is clicked
    savePasswordBtn.addEventListener("click", async function () {
        const password = passwordInput.value.trim();
        if (!password) {
            Swal.fire("Error", "Password cannot be empty!", "error");
            return;
        }
        if (!validatePasswordStrength(password)) {
            Swal.fire(
                "Error",
                "Password must be at least 8 characters long, contain at least one uppercase letter, one lowercase letter, one digit, and one special character.",
                "error"
            );
            return;
        }
        try {
            const response = await fetch("/set_password", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ password })
            });
            const data = await response.json();
            if (data.success) {
                Swal.fire("Success", "Password saved successfully!", "success");
                // Do not clear the saved password from the backend when saving.
                passwordInput.value = "";
                passwordInput.placeholder = "Password Already Set";
                passwordInput.disabled = true;
                savePasswordBtn.disabled = true;
                isPasswordSet = true;
            } else {
                Swal.fire("Error", data.message, "error");
            }
        } catch (error) {
            Swal.fire("Error", "Failed to save password", "error");
        }
    });

    // Toggle password protection
    passwordToggle.addEventListener("change", function () {
        if (!passwordToggle.checked) {
            // When turning OFF protection:
            if (isPasswordSet) {
                if (failedAttempts >= MAX_ATTEMPTS) {
                    Swal.fire("Too Many Attempts", "Please try again later.", "error");
                    lockout();
                    return;
                }
                Swal.fire({
                    title: "Enter Password to Disable",
                    input: "password",
                    showCancelButton: true,
                    inputAttributes: { autocapitalize: "off" }
                }).then(result => {
                    if (result.value) {
                        fetch("/disable_protection", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ password: result.value })
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                toggleStatus.textContent = "Password Protection: OFF";
                                // Delete the stored password so that enabling protection later will require a new password.
                                isPasswordSet = false;
                                passwordInput.disabled = false;
                                savePasswordBtn.disabled = false;
                                passwordInput.placeholder = "Enter password";
                                passwordToggle.checked = false;
                            } else {
                                failedAttempts++;
                                passwordToggle.checked = true;
                                Swal.fire("Error", "Incorrect password", "error");
                                if (failedAttempts >= MAX_ATTEMPTS) lockout();
                            }
                        });
                    } else {
                        passwordToggle.checked = true;
                    }
                });
            } else {
                // If no password is set, disable protection directly (should normally not occur because protection is off)
                fetch("/disable_protection", { method: "POST" })
                    .then(response => response.json())
                    .then(() => {
                        toggleStatus.textContent = "Password Protection: OFF";
                        passwordToggle.checked = false;
                    });
            }
        } else {
            // Enabling protection: if no password is set, prompt to set one.
            if (!isPasswordSet) {
                Swal.fire({
                    title: "Set a Password to Enable Protection",
                    input: "password",
                    showCancelButton: true,
                    inputAttributes: { autocapitalize: "off" },
                    preConfirm: (password) => {
                        if (!validatePasswordStrength(password)) {
                            Swal.showValidationMessage(
                                "Password must be at least 8 characters long, contain at least one uppercase letter, one lowercase letter, one digit, and one special character."
                            );
                        }
                        return password;
                    }
                }).then(result => {
                    if (result.value) {
                        fetch("/set_password", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ password: result.value })
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                Swal.fire("Success", "Password saved! Protection enabled.", "success");
                                isPasswordSet = true;
                                toggleStatus.textContent = "Password Protection: ON";
                                fetch("/enable_protection", { method: "POST" });
                                passwordToggle.checked = true;
                                // Disable the password input since a password is now set.
                                passwordInput.disabled = true;
                                savePasswordBtn.disabled = true;
                                passwordInput.placeholder = "Password Already Set";
                            } else {
                                Swal.fire("Error", data.message, "error");
                                passwordToggle.checked = false;
                            }
                        });
                    } else {
                        passwordToggle.checked = false;
                    }
                });
            } else {
                // If a password already exists, simply enable protection.
                fetch("/enable_protection", { method: "POST" }).then(() => {
                    toggleStatus.textContent = "Password Protection: ON";
                    passwordToggle.checked = true;
                });
            }
        }
    });

    // "Forgot Password?" functionality (stub: can be extended)
    forgotPasswordLink?.addEventListener("click", function () {
        Swal.fire("Forgot Password", "Please contact support to reset your password.", "info");
    });
});
