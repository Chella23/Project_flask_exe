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
