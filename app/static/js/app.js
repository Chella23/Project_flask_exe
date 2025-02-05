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
document.getElementById('block-btn').addEventListener('click', async () => {
    const websiteUrl = document.getElementById('website-url').value.trim();

    if (!websiteUrl) {
        alert("Please enter a website URL.");
        return;
    }

    try {
        const response = await fetch('/block', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ website_url: websiteUrl }),
        });

        const result = await response.json();
        alert(result.message);
    } catch (error) {
        console.error('Error blocking the website:', error);
        alert('An error occurred. Please try again.');
    }
});

document.getElementById('unblock-btn').addEventListener('click', async () => {
    const websiteUrl = document.getElementById('website-url').value.trim();

    if (!websiteUrl) {
        alert("Please enter a website URL.");
        return;
    }

    try {
        const response = await fetch('/unblock', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ website_url: websiteUrl }),
        });

        const result = await response.json();
        alert(result.message);
    } catch (error) {
        console.error('Error unblocking the website:', error);
        alert('An error occurred. Please try again.');
    }
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