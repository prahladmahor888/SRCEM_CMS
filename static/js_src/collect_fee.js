(function() {
    document.addEventListener('DOMContentLoaded', function() {
        const dropdownWrapper = document.getElementById('student-dropdown-wrapper');
        const dropdownBtn = document.getElementById('student-dropdown-btn');
        const dropdownMenu = document.getElementById('student-dropdown-menu');
        const dropdownChevron = document.getElementById('dropdown-chevron');
        const searchInput = document.getElementById('student-search-input');
        const idInput = document.getElementById('student-id-input');
        const label = document.getElementById('selected-student-label');
        const options = document.querySelectorAll('.student-option');
        const noResults = document.getElementById('no-students-found');

        if (!dropdownWrapper || !dropdownBtn || !dropdownMenu || !dropdownChevron || !searchInput || !idInput || !label) return;

        let highlightedIndex = -1;

        function getVisibleOptions() {
            return Array.from(options).filter(opt => opt.style.display !== 'none');
        }

        function updateHighlight() {
            const visibleOptions = getVisibleOptions();
            options.forEach(opt => opt.classList.remove('bg-emerald-50/70', 'dark:bg-emerald-950/40', 'ring-1', 'ring-emerald-500/50'));
            
            if (highlightedIndex >= 0 && highlightedIndex < visibleOptions.length) {
                const activeOpt = visibleOptions[highlightedIndex];
                activeOpt.classList.add('bg-emerald-50/70', 'dark:bg-emerald-950/40', 'ring-1', 'ring-emerald-500/50');
                activeOpt.scrollIntoView({ block: 'nearest' });
            }
        }

        function openDropdown() {
            dropdownMenu.classList.remove('hidden');
            dropdownMenu.classList.add('flex');
            dropdownChevron.classList.add('rotate-180');
            highlightedIndex = -1;
            updateHighlight();
            setTimeout(() => searchInput.focus(), 50);
        }

        function closeDropdown() {
            dropdownMenu.classList.remove('flex');
            dropdownMenu.classList.add('hidden');
            dropdownChevron.classList.remove('rotate-180');
        }

        dropdownBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            const isHidden = dropdownMenu.classList.contains('hidden');
            if (isHidden) {
                openDropdown();
            } else {
                closeDropdown();
            }
        });

        // Filter students on input change
        searchInput.addEventListener('input', function() {
            const query = searchInput.value.toLowerCase().trim();
            let anyVisible = false;

            options.forEach(option => {
                const searchText = option.getAttribute('data-search-text') || '';
                if (searchText.includes(query)) {
                    option.style.display = 'flex';
                    anyVisible = true;
                } else {
                    option.style.display = 'none';
                }
            });

            if (anyVisible) {
                if (noResults) noResults.classList.add('hidden');
            } else {
                if (noResults) noResults.classList.remove('hidden');
            }

            highlightedIndex = -1;
            updateHighlight();
        });

        // Click on search input shouldn't close dropdown
        searchInput.addEventListener('click', function(e) {
            e.stopPropagation();
        });

        // Keyboard navigation inside search input
        searchInput.addEventListener('keydown', function(e) {
            const visibleOptions = getVisibleOptions();
            
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (visibleOptions.length > 0) {
                    highlightedIndex = (highlightedIndex + 1) % visibleOptions.length;
                    updateHighlight();
                }
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (visibleOptions.length > 0) {
                    highlightedIndex = (highlightedIndex - 1 + visibleOptions.length) % visibleOptions.length;
                    updateHighlight();
                }
            } else if (e.key === 'Enter') {
                e.preventDefault(); // Prevent form submission
                if (highlightedIndex >= 0 && highlightedIndex < visibleOptions.length) {
                    visibleOptions[highlightedIndex].click();
                }
            } else if (e.key === 'Escape') {
                e.preventDefault();
                closeDropdown();
                dropdownBtn.focus();
            }
        });

        // Select student option
        options.forEach(option => {
            option.addEventListener('click', function(e) {
                e.stopPropagation();
                const studentId = option.getAttribute('data-id');
                const displayName = option.getAttribute('data-display-name');
                const roll = option.getAttribute('data-roll');
                const branch = option.getAttribute('data-branch');

                idInput.value = studentId;
                idInput.dispatchEvent(new Event('change'));

                label.textContent = `${displayName} (${roll} • ${branch})`;
                label.classList.remove('text-gray-400', 'dark:text-gray-500', 'font-medium');
                label.classList.add('text-gray-900', 'dark:text-white', 'font-bold');

                closeDropdown();
                dropdownBtn.focus();
            });
        });

        // Click outside to close
        document.addEventListener('click', function(event) {
            if (!dropdownWrapper.contains(event.target)) {
                closeDropdown();
            }
        });
    });
})();
