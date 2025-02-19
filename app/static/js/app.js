document.addEventListener("DOMContentLoaded", function () {
    const sidebar = document.querySelector(".sidebar");
    const menuToggle = document.getElementById("menu-toggle");

    // Toggle the sidebar visibility on click
    menuToggle.addEventListener("click", function () {
        // Toggle 'hidden' class to show/hide the sidebar
        sidebar.classList.toggle("hidden");

        // Toggle the icon rotation
        menuToggle.classList.toggle("active");
    });
});
document.addEventListener("DOMContentLoaded", function () {
    const blockBtn = document.getElementById("block-btn");
    const unblockBtn = document.getElementById("unblock-btn");

    function isValidURL(url) {
        const regex = /^(https?:\/\/)?(www\.)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}(:\d+)?(\/.*)?$/;
        return regex.test(url);
    }

    async function isPasswordProtected() {
        try {
            const response = await fetch("/get_protection_status");
            const data = await response.json();
            return data.enabled;
        } catch (error) {
            console.error("Error fetching password protection status:", error);
            return false;
        }
    }

    async function requestPassword() {
        const { value: password } = await Swal.fire({
            title: "Enter Password",
            input: "password",
            inputPlaceholder: "Enter your password",
            showCancelButton: true,
            confirmButtonText: "Submit",
            preConfirm: (password) => {
                if (!password) {
                    Swal.showValidationMessage("Password is required");
                }
                return password;
            },
        });
        return password;
    }

    async function isMFAEnabled() {
        try {
            const response = await fetch("/get_mfa_status");
            const data = await response.json();
            return data.mfa_enabled;
        } catch (error) {
            console.error("Error fetching MFA status:", error);
            return false;
        }
    }

    async function sendOTP() {
        const response = await fetch("/get_user_email");
        const data = await response.json();
        if (!data.email) {
            Swal.fire("Error", "Unable to fetch email for OTP.", "error");
            return null;
        }

        await fetch("/send_otp", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: data.email })
        });

        return await askForOTP();
    }

    async function askForOTP() {
        const { value: otp } = await Swal.fire({
            title: "Enter OTP",
            input: "text",
            inputAttributes: { maxlength: 6, pattern: "[0-9]*", inputmode: "numeric" },
            showCancelButton: true,
            confirmButtonText: "Verify"
        });

        if (!otp) return null;

        const response = await fetch("/verify_mfa", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ otp })
        });

        const data = await response.json();
        if (!data.success) {
            Swal.fire("Error", data.error, "error");
            return null;
        }

        return await askForPIN();
    }

    async function askForPIN() {
        const { value: pin } = await Swal.fire({
            title: "Enter 6-Digit PIN",
            input: "password",
            inputAttributes: { maxlength: 6, pattern: "[0-9]*", inputmode: "numeric" },
            showCancelButton: true,
            confirmButtonText: "Verify"
        });

        return pin;
    }

    async function authenticateUser() {
        let password = "", pin = "";

        if (await isPasswordProtected()) {
            password = await requestPassword();
            if (!password) return null;
        }

        if (await isMFAEnabled()) {
            pin = await sendOTP();
            if (!pin) return null;
        }

        return { password, pin };
    }

    async function blockWebsite() {
        const websiteInput = document.getElementById("website-url").value.trim();
        if (!websiteInput) {
            Swal.fire("Error", "Please enter at least one website URL.", "error");
            return;
        }

        const websites = websiteInput.split("\n").map(url => url.trim()).filter(url => isValidURL(url));
        if (websites.length === 0) {
            Swal.fire("Error", "Please enter valid website URLs.", "error");
            return;
        }

        const auth = await authenticateUser();
        if (!auth) return;

        try {
            const response = await fetch("/block", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ websites, ...auth })
            });

            const data = await response.json();
            if (data.success) {
                Swal.fire("Success", "Websites blocked successfully!", "success");
                updateBlockedList();
            } else {
                Swal.fire("Error", data.message, "error");
            }
        } catch (error) {
            console.error("Error blocking websites:", error);
            Swal.fire("Error", "An error occurred while blocking the websites.", "error");
        }
    }

    async function unblockWebsite() {
        const websiteInput = document.getElementById("website-url").value.trim();
        if (!websiteInput) {
            Swal.fire("Error", "Please enter at least one website URL.", "error");
            return;
        }

        const websites = websiteInput.split("\n").map(url => url.trim()).filter(url => isValidURL(url));
        if (websites.length === 0) {
            Swal.fire("Error", "Please enter valid website URLs.", "error");
            return;
        }

        const auth = await authenticateUser();
        if (!auth) return;

        try {
            const response = await fetch("/unblock", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ websites, ...auth })
            });

            const data = await response.json();
            if (data.success) {
                Swal.fire("Success", "Websites unblocked successfully!", "success");
                updateBlockedList();
            } else {
                Swal.fire("Error", data.message, "error");
            }
        } catch (error) {
            console.error("Error unblocking websites:", error);
            Swal.fire("Error", "An error occurred while unblocking the websites.", "error");
        }
    }

    async function updateBlockedList() {
        const blockedList = document.getElementById("blocked-list");
        blockedList.innerHTML = "";

        try {
            const response = await fetch("/blocked_websites");
            const blockedWebsites = await response.json();

            blockedWebsites.forEach(website => {
                const li = document.createElement("li");
                li.textContent = website;
                blockedList.appendChild(li);
            });
        } catch (error) {
            console.error("Error fetching blocked websites:", error);
        }
    }

    blockBtn.addEventListener("click", blockWebsite);
    unblockBtn.addEventListener("click", unblockWebsite);

    updateBlockedList();
});




document.addEventListener("DOMContentLoaded", () => {
    const categories = document.querySelectorAll(".category");

    categories.forEach(category => {
        category.querySelector("h3").addEventListener("click", () => {
            // Collapse all categories first
            categories.forEach(cat => {
                if (cat !== category) {
                    cat.classList.remove("expanded");
                }
            });

            // Toggle only the clicked category
            category.classList.toggle("expanded");
        });
    });
});


// Search Functionality
document.getElementById("search-btn").addEventListener("click", function () {
    const searchQuery = document.getElementById("search-input").value.toLowerCase();
    const categories = document.querySelectorAll(".category");

    categories.forEach(category => {
        const categoryName = category.querySelector("h3 span").textContent.toLowerCase();
        const websites = category.querySelectorAll("li");

        let matchFound = false;

        // Check if category name matches
        if (categoryName.includes(searchQuery)) {
            matchFound = true;
        }

        // Check if any website name matches
        websites.forEach(website => {
            const websiteName = website.textContent.toLowerCase();
            if (websiteName.includes(searchQuery)) {
                matchFound = true;
                website.style.backgroundColor = "rgba(106, 17, 203, 0.2)"; // Highlight matching websites
            } else {
                website.style.backgroundColor = ""; // Reset background for non-matching websites
            }
        });

        // Show/hide categories based on search results
        if (matchFound) {
            category.style.display = "block";
        } else {
            category.style.display = "none";
        }
    });
});