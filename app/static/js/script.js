document.addEventListener("DOMContentLoaded", () => {
    const websiteInput = document.getElementById("website");
    const blockBtn = document.getElementById("blockBtn");
    const blockedWebsitesList = document.getElementById("blockedWebsitesList");

    // Load blocked websites on page load
    const loadBlockedWebsites = () => {
        fetch("/list")
            .then((response) => response.json())
            .then((data) => {
                blockedWebsitesList.innerHTML = "";
                data.forEach((website) => {
                    const li = document.createElement("li");
                    li.textContent = website;

                    // Create a delete button
                    const deleteBtn = document.createElement("button");
                    deleteBtn.textContent = "🗑️";
                    deleteBtn.style.marginLeft = "10px";
                    deleteBtn.style.cursor = "pointer";
                    deleteBtn.onclick = () => {
                        deleteWebsite(website);
                    };

                    li.appendChild(deleteBtn);
                    blockedWebsitesList.appendChild(li);
                });
            });
    };

    // Add website to the block list
    blockBtn.addEventListener("click", () => {
        const website = websiteInput.value.trim();
        if (!website) {
            alert("Please enter a website.");
            return;
        }

        fetch("/block", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ website }),
        })
            .then((response) => response.json())
            .then((data) => {
                alert(data.success || data.error);
                loadBlockedWebsites();
                websiteInput.value = "";
            });
    });

    // Delete website from the block list
    const deleteWebsite = (website) => {
        fetch("/unblock", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ website }),
        })
            .then((response) => response.json())
            .then((data) => {
                alert(data.success || data.error);
                loadBlockedWebsites();
            });
    };

    // Load blocked websites on page load
    loadBlockedWebsites();
});
