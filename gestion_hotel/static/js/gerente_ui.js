document.addEventListener("DOMContentLoaded", function () {
    const sidebar = document.getElementById("sidebar");
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebarClose = document.getElementById("sidebarClose");
    const mainContent = document.getElementById("mainContent");
    const userToggle = document.getElementById("userToggle");
    const userDropdown = document.getElementById("userDropdown");

    if (sidebarToggle && sidebar && mainContent) {
        sidebarToggle.addEventListener("click", function () {
            sidebar.classList.toggle("activo");
            mainContent.classList.toggle("sidebar-open");
        });
    }

    if (sidebarClose && sidebar && mainContent) {
        sidebarClose.addEventListener("click", function () {
            sidebar.classList.remove("activo");
            mainContent.classList.remove("sidebar-open");
        });
    }

    if (userToggle && userDropdown) {
        userToggle.addEventListener("click", function (event) {
            event.stopPropagation();
            userDropdown.classList.toggle("activo");
        });

        document.addEventListener("click", function (event) {
            if (!event.target.closest(".user-menu-gerente")) {
                userDropdown.classList.remove("activo");
            }
        });
    }

    const toasts = document.querySelectorAll(".toast-gerente");
    toasts.forEach(function (toast) {
        setTimeout(function () {
            toast.style.opacity = "0";
            toast.style.transform = "translateY(-10px)";
            setTimeout(function () {
                toast.remove();
            }, 300);
        }, 4500);
    });
});
