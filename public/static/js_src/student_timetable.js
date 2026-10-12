(function() {
    // --- Day Switch Logic ---
    function switchDay(dayId, dayName) {
        // Toggle Panels
        document.querySelectorAll('.day-panel').forEach(p => p.classList.add('hidden'));
        const panel = document.getElementById('panel-' + dayId);
        if (panel) {
            panel.classList.remove('hidden');
            // Update class count tag
            const countTag = document.getElementById('classCountTag');
            if (countTag) {
                const count = panel.getAttribute('data-count') || '0';
                countTag.innerText = count + ' Classes';
            }
        }

        // Toggle Tabs
        document.querySelectorAll('.day-tab').forEach(t => {
            t.classList.remove('active', 'text-primary', 'dark:text-blue-400', 'border-primary', 'dark:border-blue-400', 'bg-gray-50', 'dark:bg-gray-800/50');
            t.classList.add('border-transparent');
        });
        
        const activeTab = document.getElementById('tab-' + dayId);
        if (activeTab) {
            activeTab.classList.remove('border-transparent');
            activeTab.classList.add('active', 'text-primary', 'dark:text-blue-400', 'border-primary', 'dark:border-blue-400', 'bg-gray-50', 'dark:bg-gray-800/50');
        }

        // Update Text
        const selectedDayText = document.getElementById('selectedDayText');
        if (selectedDayText) {
            selectedDayText.innerText = dayName;
        }
    }

    document.addEventListener('DOMContentLoaded', () => {
        // --- View Toggle Logic (Class vs Exam) ---
        const btnClassView = document.getElementById('btnClassView');
        const btnExamView = document.getElementById('btnExamView');
        const classScheduleView = document.getElementById('classScheduleView');
        const examScheduleView = document.getElementById('examScheduleView');

        if (btnClassView && btnExamView && classScheduleView && examScheduleView) {
            btnClassView.addEventListener('click', () => {
                classScheduleView.classList.remove('hidden');
                examScheduleView.classList.add('hidden');
                
                btnClassView.className = "flex-1 sm:flex-none px-6 py-3 bg-primary text-white font-bold text-sm rounded-xl transition-colors shadow-sm";
                btnExamView.className = "flex-1 sm:flex-none px-6 py-3 bg-white dark:bg-darkSidebar text-gray-600 dark:text-gray-300 hover:text-primary dark:hover:text-blue-400 font-bold text-sm rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm transition-colors";
            });

            btnExamView.addEventListener('click', () => {
                examScheduleView.classList.remove('hidden');
                classScheduleView.classList.add('hidden');
                
                btnExamView.className = "flex-1 sm:flex-none px-6 py-3 bg-primary text-white font-bold text-sm rounded-xl transition-colors shadow-sm";
                btnClassView.className = "flex-1 sm:flex-none px-6 py-3 bg-white dark:bg-darkSidebar text-gray-600 dark:text-gray-300 hover:text-primary dark:hover:text-blue-400 font-bold text-sm rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm transition-colors";
            });
        }

        // Initialize active tab
        const activeTab = document.querySelector('.day-tab.active');
        if (activeTab) {
            const dayId = activeTab.id.split('-')[1];
            const dayName = activeTab.innerText.trim();
            switchDay(dayId, dayName);
        } else {
            // Default to Monday (1)
            switchDay(1, 'Monday');
        }
    });

    // Expose globally
    window.switchDay = switchDay;
})();
