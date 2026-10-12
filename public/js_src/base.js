(function() {
    // Theme Management
    function applyTheme() {
        if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
        updateThemeIcons();
    }

    function updateThemeIcons() {
        const isDark = document.documentElement.classList.contains('dark');
        const icons = document.querySelectorAll('#themeIcon, #themeIconPortal');
        icons.forEach(icon => {
            if (icon) {
                icon.classList.remove('fa-moon', 'fa-sun');
                icon.classList.add(isDark ? 'fa-sun' : 'fa-moon');
            }
        });
    }

    function toggleTheme() {
        document.documentElement.classList.toggle('dark');
        localStorage.theme = document.documentElement.classList.contains('dark') ? 'dark' : 'light';
        updateThemeIcons();
    }

    // Sidebar Management
    function toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebarOverlay');
        if (sidebar && overlay) {
            sidebar.classList.toggle('-translate-x-full');
            overlay.classList.toggle('hidden');
            document.body.classList.toggle('overflow-hidden');
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        applyTheme();
        
        // Listeners for theme toggle
        document.querySelectorAll('#themeToggleBtn, #themeToggleBtnPortal').forEach(btn => {
            btn.addEventListener('click', toggleTheme);
        });

        // Listeners for sidebar toggle
        document.querySelectorAll('#mobileMenuBtn, #openSidebarBtn, #closeSidebarBtn, #sidebarOverlay').forEach(el => {
            el.addEventListener('click', toggleSidebar);
        });

        // Auto-hide messages
        setTimeout(() => {
            document.querySelectorAll('.flash-notification').forEach(el => {
                el.style.opacity = '0';
                setTimeout(() => el.remove(), 500);
            });
        }, 3000);
    });

    // Expose functions globally
    window.applyTheme = applyTheme;
    window.updateThemeIcons = updateThemeIcons;
    window.toggleTheme = toggleTheme;
    window.toggleSidebar = toggleSidebar;
})();
