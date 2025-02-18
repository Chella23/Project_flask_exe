document.addEventListener("DOMContentLoaded", function () {
    fetchMFAStatus();
});

function fetchMFAStatus() {
    fetch('/get_mfa_status', { method: 'GET' })
        .then(response => response.json())
        .then(data => {
            const mfaToggle = document.getElementById('mfaToggle');
            mfaToggle.checked = data.mfa_enabled;

            if (data.mfa_enabled) {
                document.getElementById('mfaStatus').innerText = "MFA is Enabled";
            } else {
                document.getElementById('mfaStatus').innerText = "MFA is Disabled";
            }
        })
        .catch(error => console.error("Error fetching MFA status:", error));
}

function toggleMFA() {
    let isEnabled = document.getElementById("mfaToggle").checked;

    if (isEnabled) {
        // Check if user has completed MFA setup
        checkMFASetup();
    } else {
        // Disable MFA
        disableMFA();
    }
}

function checkMFASetup() {
    fetch('/get_user_email', { method: 'GET' })
        .then(response => response.json())
        .then(data => {
            // Check if the user has MFA and PIN setup already
            if (data.email) {
                Swal.fire({
                    title: "Setup MFA",
                    html: `<p>Registered Email: <b>${data.email}</b></p>
                           <button id="sendOTPBtn" class="swal2-confirm">Send OTP</button>`,
                    showCancelButton: true,
                    showConfirmButton: false
                });

                document.getElementById('sendOTPBtn').addEventListener("click", function () {
                    sendOTP(data.email, "enable");
                });
            }
        });
}

function sendOTP(email, action) {
    fetch('/send_otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            askForOTP(action);
        } else {
            Swal.fire("Error", data.error, "error");
        }
    });
}

function askForOTP(action) {
    Swal.fire({
        title: "Enter OTP",
        input: "text",
        inputAttributes: { autocapitalize: "off" },
        showCancelButton: true,
        confirmButtonText: "Verify",
        preConfirm: (otp) => {
            if (action === "enable") {
                return verifyOTP(otp);
            } else {
                return verifyOTPForDisable(otp);
            }
        }
    });
}

function verifyOTP(otp) {
    return fetch('/verify_mfa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ otp })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (data.message.includes("OTP verified. Please set your 6-digit PIN.")) {
                setupPIN();
            } else {
                Swal.fire("Success", "MFA verification successful!", "success");
            }
        } else {
            Swal.fire("Error", data.error, "error");
        }
    });
}

function setupPIN() {
    Swal.fire({
        title: "Set Your 6-Digit PIN",
        input: "password",
        inputAttributes: { maxlength: 6, pattern: "[0-9]*", inputmode: "numeric" },
        showCancelButton: true,
        confirmButtonText: "Save",
        preConfirm: (pin) => savePIN(pin)
    });
}

function savePIN(pin) {
    fetch('/set_pin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pin })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            Swal.fire("Success", "MFA is now enabled!", "success");
            fetchMFAStatus(); // Refresh MFA status
        } else {
            Swal.fire("Error", data.error, "error");
        }
    });
}

function disableMFA() {
    fetch('/get_user_email', { method: 'GET' })
    .then(response => response.json())
    .then(data => {
        Swal.fire({
            title: "Disable MFA",
            html: `<p>Registered Email: <b>${data.email}</b></p><button id="sendOTPBtn" class="swal2-confirm">Send OTP</button>`,
            showCancelButton: true,
            showConfirmButton: false
        });

        document.getElementById('sendOTPBtn').addEventListener("click", function () {
            sendOTP(data.email, "disable");
        });
    });
}

function verifyOTPForDisable(otp) {
    return fetch('/verify_mfa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ otp })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            askForPINToDisable();
        } else {
            Swal.fire("Error", data.error, "error");
        }
    });
}

function askForPINToDisable() {
    Swal.fire({
        title: "Enter 6-Digit PIN",
        input: "password",
        showCancelButton: true,
        confirmButtonText: "Verify",
        preConfirm: (pin) => verifyPINForDisable(pin)
    });
}

function verifyPINForDisable(pin) {
    fetch('/disable_mfa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pin })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            Swal.fire("Success", "MFA has been disabled!", "success");
            fetchMFAStatus(); // Refresh MFA status
        } else {
            Swal.fire("Error", data.error, "error");
        }
    });
}
