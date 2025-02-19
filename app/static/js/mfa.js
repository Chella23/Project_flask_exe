document.addEventListener("DOMContentLoaded", function () {
    loadMFAStatus();
});

async function loadMFAStatus() {
    try {
        const response = await fetch('/get_mfa_status');
        const data = await response.json();
        const mfaToggle = document.getElementById('mfaToggle');
        mfaToggle.checked = data.mfa_enabled;
        document.getElementById('mfaStatus').innerText = data.mfa_enabled ? "MFA is Enabled" : "MFA is Disabled";
    } catch (error) {
        console.error("Error fetching MFA status:", error);
    }
}

// Handle toggle changes
document.getElementById("mfaToggle").addEventListener("change", function () {
    if (this.checked) {
        // When turning ON, if MFA is not set up, prompt for OTP then PIN.
        checkMFASetup();
    } else {
        // When turning OFF, prompt for OTP (and PIN verification) before disabling.
        promptDisableMFA();
    }
});

function checkMFASetup() {
    // First, get the registered email
    fetch('/get_user_email')
        .then(response => response.json())
        .then(data => {
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

function promptDisableMFA() {
    fetch('/get_user_email')
        .then(response => response.json())
        .then(data => {
            Swal.fire({
                title: "Disable MFA",
                html: `<p>Registered Email: <b>${data.email}</b></p>
                       <button id="sendOTPBtn" class="swal2-confirm">Send OTP</button>`,
                showCancelButton: true,
                showConfirmButton: false
            });
            document.getElementById('sendOTPBtn').addEventListener("click", function () {
                sendOTP(data.email, "disable");
            });
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
        preConfirm: (otp) => verifyOTP(otp, action)
    }).then((result) => {
        if (result.dismiss === Swal.DismissReason.cancel) {
            loadMFAStatus();  // Revert toggle if user cancels
        }
    });
}

function verifyOTP(otp, action) {
    return fetch('/verify_mfa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ otp })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (action === "enable" && data.message.includes("set your 6-digit PIN")) {
                setupPIN();
            } else if (action === "disable") {
                promptPINForDisable();  // Prompt for PIN after OTP verification
            } else {
                Swal.fire("Success", data.message, "success");
                loadMFAStatus();
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
    }).then((result) => {
        if (result.dismiss === Swal.DismissReason.cancel) {
            loadMFAStatus();  // Revert toggle if user cancels
        }
    });
}


function savePIN(pin) {
    // Call the /set_pin endpoint to create/update the MFA record.
    fetch('/set_pin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pin })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            Swal.fire("Success", "MFA is now enabled!", "success");
            loadMFAStatus();
        } else {
            Swal.fire("Error", data.error, "error");
        }
    });
}
function promptPINForDisable() {
    Swal.fire({
        title: "Enter 6-Digit PIN",
        input: "password",
        inputAttributes: { maxlength: 6, pattern: "[0-9]*", inputmode: "numeric" },
        showCancelButton: true,
        confirmButtonText: "Verify",
        preConfirm: (pin) => verifyPINForDisable(pin)
    }).then((result) => {
        if (result.dismiss === Swal.DismissReason.cancel) {
            loadMFAStatus();  // Revert toggle if user cancels
        }
    });
}


function verifyPINForDisable(pin) {
    fetch('/disable_mfa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pin })  // Send PIN for verification
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            Swal.fire("Success", "MFA has been disabled!", "success");
            loadMFAStatus();
        } else {
            Swal.fire("Error", data.error, "error");
            loadMFAStatus(); // Keep MFA enabled if PIN verification fails
        }
    });
}
