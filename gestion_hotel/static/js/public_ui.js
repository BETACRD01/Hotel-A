document.addEventListener("DOMContentLoaded", function () {
    const botonMenu = document.getElementById("botonMenu");
    const menuPublico = document.getElementById("menuPublico");

    if (botonMenu && menuPublico) {
        botonMenu.addEventListener("click", function () {
            menuPublico.classList.toggle("activo");
        });
    }

    const userMenuToggle = document.querySelector(".user-menu-toggle");
    const userDropdown = document.querySelector(".user-dropdown");
    const openProfileConfig = document.getElementById("openProfileConfig");
    const profileModal = document.getElementById("profileModal");
    const closeProfileModal = document.getElementById("closeProfileModal");
    const closeProfileOverlay = document.getElementById("closeProfileOverlay");

    if (userMenuToggle && userDropdown) {
        userMenuToggle.addEventListener("click", function (event) {
            event.stopPropagation();
            const isOpen = userDropdown.classList.toggle("activo");
            this.setAttribute("aria-expanded", isOpen);
        });

        document.addEventListener("click", function (event) {
            if (!event.target.closest(".user-menu")) {
                userDropdown.classList.remove("activo");
                userMenuToggle.setAttribute("aria-expanded", "false");
            }
        });
    }

    if (openProfileConfig && profileModal) {
        openProfileConfig.addEventListener("click", function () {
            profileModal.classList.add("activo");
            if (userDropdown) {
                userDropdown.classList.remove("activo");
            }
        });
    }

    if (closeProfileModal && profileModal) {
        closeProfileModal.addEventListener("click", function () {
            profileModal.classList.remove("activo");
        });
    }

    if (closeProfileOverlay && profileModal) {
        closeProfileOverlay.addEventListener("click", function () {
            profileModal.classList.remove("activo");
        });
    }

    setTimeout(function () {
        const toasts = document.querySelectorAll(".toast-mensaje");
        toasts.forEach(function (toast) {
            toast.style.opacity = "0";
            toast.style.transform = "translateY(-10px)";
            setTimeout(function () {
                toast.remove();
            }, 300);
        });
    }, 4500);
});
