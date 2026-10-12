(function() {
    function switchDay(dayId, dayName) {
        // Toggle Panels
        document.querySelectorAll('.day-panel').forEach(p => p.classList.add('hidden'));
        const panel = document.getElementById('panel-' + dayId);
        if (panel) {
            panel.classList.remove('hidden');
        }

        // Toggle Tabs
        document.querySelectorAll('.day-tab').forEach(t => {
            t.classList.remove('active', 'text-primary', 'dark:text-blue-400', 'bg-blue-50/50', 'dark:bg-blue-900/10', 'border-primary', 'dark:border-blue-400');
            t.classList.add('border-transparent', 'hover:bg-gray-50', 'dark:hover:bg-gray-700/50');
        });
        
        const activeTab = document.getElementById('tab-' + dayId);
        if (activeTab) {
            activeTab.classList.remove('border-transparent', 'hover:bg-gray-50', 'dark:hover:bg-gray-700/50');
            activeTab.classList.add('active', 'text-primary', 'dark:text-blue-400', 'bg-blue-50/50', 'dark:bg-blue-900/20', 'border-primary', 'dark:border-blue-400');
        }

        // Update Text
        const selectedDayText = document.getElementById('selectedDayText');
        if (selectedDayText) {
            selectedDayText.innerText = dayName;
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        // Initialize with current day or first day
        const activeTab = document.querySelector('.day-tab.active');
        if (activeTab) {
            const dayName = activeTab.innerText.split('\n')[0].trim();
            const selectedDayText = document.getElementById('selectedDayText');
            if (selectedDayText) {
                selectedDayText.innerText = dayName;
            }
        } else {
            // Default to Monday
            switchDay(1, 'Monday');
        }
    });

    // Expose globally
    window.switchDay = switchDay;
})();
