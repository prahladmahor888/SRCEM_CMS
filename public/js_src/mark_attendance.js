(function() {
    // --- AJAX Filter Logic ---
    async function updateAttendanceFilters(type) {
        const classBatchSelect = document.querySelector('select[name="class_batch"]');
        const subjectSelect = document.querySelector('select[name="subject"]');
        const dateInput = document.querySelector('input[name="date"]');

        if (!classBatchSelect || !subjectSelect || !dateInput) return;

        const classBatch = classBatchSelect.value;
        const subject = subjectSelect.value;
        const date = dateInput.value;
        
        if (type === 'class' && !classBatch) return;

        // Show loading state
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) overlay.classList.remove('hidden');

        try {
            const url = new URL(window.location.href);
            url.searchParams.set('class_batch', classBatch);
            url.searchParams.set('subject', subject);
            url.searchParams.set('date', date);

            const response = await fetch(url, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) throw new Error('Network response was not ok');
            
            const data = await response.json();

            // 1. Update Subject Dropdown if class changed
            if (type === 'class') {
                const subjectSelectEl = document.getElementById('subjectSelect');
                if (subjectSelectEl) {
                    subjectSelectEl.innerHTML = `<option value="">${classBatch ? '-- Select Subject --' : 'First select class...'}</option>`;
                    data.subjects.forEach(sub => {
                        const opt = document.createElement('option');
                        opt.value = sub.id;
                        opt.textContent = `${sub.name} (${sub.code})`;
                        subjectSelectEl.appendChild(opt);
                    });
                }
            }

            // 2. Update Attendance Sheet Partial
            const container = document.getElementById('attendanceContainer');
            if (container) {
                container.innerHTML = data.html;
                // re-insert the loading overlay which was just overwritten
                const newOverlay = document.createElement('div');
                newOverlay.id = 'loadingOverlay';
                newOverlay.className = 'hidden absolute inset-0 bg-white/50 dark:bg-gray-900/50 backdrop-blur-[2px] z-50 flex items-center justify-center rounded-2xl';
                newOverlay.innerHTML = `<div class="flex flex-col items-center gap-3">
                    <div class="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
                    <span class="text-xs font-black text-primary uppercase tracking-widest">Loading Records...</span>
                </div>`;
                container.appendChild(newOverlay);
            }

            // 3. Re-initialize logic for the new DOM elements
            initAttendanceLogic();

        } catch (error) {
            console.error('Fetch error:', error);
        } finally {
            if (overlay) overlay.classList.add('hidden');
        }
    }

    // --- Core Attendance Logic (Re-initializable) ---
    function initAttendanceLogic() {
        // --- Attendance Counter Logic ---
        const presentCountEl = document.getElementById('presentCount');
        const absentCountEl = document.getElementById('absentCount');
        const radios = document.querySelectorAll('.attendance-radio');
        const markAllPresentBtn = document.getElementById('markAllPresentBtn');

        function updateCounts() {
            let present = 0;
            let absent = 0;
            document.querySelectorAll('.attendance-radio:checked').forEach(radio => {
                if (radio.value === 'P') present++;
                if (radio.value === 'A') absent++;
            });
            
            if(presentCountEl) presentCountEl.textContent = present;
            if(absentCountEl) absentCountEl.textContent = absent;
        }

        radios.forEach(radio => {
            radio.addEventListener('change', updateCounts);
        });

        if(markAllPresentBtn) {
            markAllPresentBtn.addEventListener('click', () => {
                document.querySelectorAll('.attendance-radio[value="P"]').forEach(radio => {
                    radio.checked = true;
                });
                updateCounts();
            });
        }

        // --- Search Student ---
        const studentSearch = document.getElementById('studentSearch');
        const tableRows = document.querySelectorAll('#attendanceTableBody .student-row');

        if(studentSearch) {
            studentSearch.addEventListener('input', function(e) {
                const searchTerm = e.target.value.toLowerCase();
                tableRows.forEach(row => {
                    const name = row.dataset.name ? row.dataset.name.toLowerCase() : '';
                    const roll = row.dataset.roll ? row.dataset.roll.toLowerCase() : '';
                    if(name.includes(searchTerm) || roll.includes(searchTerm)) {
                        row.classList.remove('hidden');
                    } else {
                        row.classList.add('hidden');
                    }
                });
            });
        }

        // Initial count for newly loaded data
        updateCounts();
    }

    // Initial load
    document.addEventListener('DOMContentLoaded', initAttendanceLogic);

    // Expose functions globally
    window.updateAttendanceFilters = updateAttendanceFilters;
    window.initAttendanceLogic = initAttendanceLogic;
})();
