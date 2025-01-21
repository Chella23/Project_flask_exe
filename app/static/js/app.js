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
