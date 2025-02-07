document.addEventListener("DOMContentLoaded", function () {
    const passwordInput = document.getElementById("password-input");
    const savePasswordBtn = document.getElementById("save-password-btn");
    const passwordToggle = document.getElementById("password-toggle");
    const toggleStatus = document.getElementById("toggle-status");

    // Load password protection status from backend
    fetch("/get_protection_status")
        .then(response => response.json())
        .then(data => {
            passwordToggle.checked = data.enabled;
            toggleStatus.textContent = `Password Protection: ${data.enabled ? "ON" : "OFF"}`;
        });

    // Save password
    savePasswordBtn.addEventListener("click", function () {
        const password = passwordInput.value;
        if (!password) {
            Swal.fire("Error", "Password cannot be empty!", "error");
            return;
        }

        fetch("/set_password", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ password })
        })
        .then(response => response.json())
        .then(data => Swal.fire("Success", data.message, "success"))
        .catch(error => Swal.fire("Error", "Failed to save password", "error"));
    });

    // Toggle password protection
    passwordToggle.addEventListener("change", function () {
        if (!passwordToggle.checked) {
            // Ask for password before disabling
            Swal.fire({
                title: "Enter Password to Disable",
                input: "password",
                showCancelButton: true
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
                        } else {
                            passwordToggle.checked = true;
                            Swal.fire("Error", "Incorrect password", "error");
                        }
                    });
                } else {
                    passwordToggle.checked = true; // Prevent accidental disabling
                }
            });
        } else {
            fetch("/enable_protection", { method: "POST" })
            .then(response => response.json())
            .then(data => {
                toggleStatus.textContent = "Password Protection: ON";
            });
        }
    });
});
