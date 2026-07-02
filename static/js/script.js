

document.addEventListener("DOMContentLoaded", function () {
    const deleteButtons = document.querySelectorAll(".delete-modal-btn");
    const deleteForm = document.getElementById("deleteForm");
    const deleteProductName = document.getElementById("deleteProductName");

    deleteButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            const deleteUrl = button.getAttribute("data-delete-url");
            const productName = button.getAttribute("data-product-name");

            deleteForm.action = deleteUrl;
            deleteProductName.textContent = productName;
        });
    });

    const productForm = document.getElementById("productForm");
    const confirmSaveBtn = document.getElementById("confirmSaveBtn");

    if (productForm && confirmSaveBtn) {
        confirmSaveBtn.addEventListener("click", function () {
            productForm.submit();
        });
    }
});

document.addEventListener("DOMContentLoaded", function () {
    if (window.jQuery && window.jQuery.fn && window.jQuery.fn.select2) {
        $(".searchable-select").each(function () {
            const selectElement = $(this);
            const placeholderText = selectElement.data("placeholder") || "Search and select";

            if (selectElement.hasClass("select2-hidden-accessible")) {
                selectElement.select2("destroy");
            }

            selectElement.next(".select2-container").remove();

            selectElement.select2({
                width: "100%",
                placeholder: placeholderText,
                allowClear: true
            });

            selectElement.css({
                position: "absolute",
                width: "1px",
                height: "1px",
                opacity: "0",
                pointerEvents: "none"
            });
        });
    }
});

/* ===== Active Sidebar Script ===== */
document.addEventListener("DOMContentLoaded", function () {
    const sidebar = document.querySelector(".app-sidebar");

    if (!sidebar) {
        return;
    }

    const currentPath = window.location.pathname.replace(/\/+$/, "/");
    const sidebarLinks = sidebar.querySelectorAll("a[href]");
    let bestMatch = null;
    let bestLength = 0;

    sidebarLinks.forEach(function (link) {
        const rawHref = link.getAttribute("href");

        if (!rawHref || rawHref === "#" || rawHref.startsWith("javascript:")) {
            return;
        }

        const linkPath = new URL(link.href, window.location.origin).pathname.replace(/\/+$/, "/");

        if (
            currentPath === linkPath ||
            (linkPath !== "/" && currentPath.startsWith(linkPath))
        ) {
            if (linkPath.length > bestLength) {
                bestMatch = link;
                bestLength = linkPath.length;
            }
        }
    });

    if (!bestMatch) {
        return;
    }

    bestMatch.classList.add("active");

    const submenu = bestMatch.closest(".sidebar-submenu");

    if (submenu) {
        submenu.classList.add("show");

        const toggle = sidebar.querySelector('[href="#' + submenu.id + '"]');

        if (toggle) {
            toggle.classList.add("active");
        }
    }
});
/* ===== End Active Sidebar Script ===== */

/* ===== Collapsible Sidebar Script ===== */
document.addEventListener("DOMContentLoaded", function () {
    const toggle = document.getElementById("sidebarCollapseToggle");

    if (!toggle) {
        return;
    }

    const savedState = localStorage.getItem("coffeeSidebarCollapsed");

    if (savedState === "yes") {
        document.body.classList.add("sidebar-collapsed");
    }

    toggle.addEventListener("click", function () {
        document.body.classList.toggle("sidebar-collapsed");

        if (document.body.classList.contains("sidebar-collapsed")) {
            localStorage.setItem("coffeeSidebarCollapsed", "yes");
        } else {
            localStorage.setItem("coffeeSidebarCollapsed", "no");
        }
    });
});
/* ===== End Collapsible Sidebar Script ===== */
