(function() {
    // Countdown Timer logic for Presentation Date
    function initCountdown() {
        const presentationDateStr = window.presentationDateStr;
        if (presentationDateStr) {
            const presDate = new Date(presentationDateStr);
            const now = new Date();
            const timeDiff = presDate.getTime() - now.getTime();
            const daysDiff = Math.ceil(timeDiff / (1000 * 3600 * 24));
            
            const countText = document.getElementById('presentation-text');
            const countdownSub = document.getElementById('countdown-subtext');
            
            if (countText && countdownSub) {
                if (daysDiff > 0) {
                    countdownSub.innerText = `${daysDiff} Days Remaining`;
                    countdownSub.classList.add('text-warning');
                } else if (daysDiff === 0) {
                    countdownSub.innerText = "TODAY";
                    countdownSub.classList.remove('text-gray-500');
                    countdownSub.classList.add('text-secondary', 'font-black');
                } else {
                    countdownSub.innerText = "Completed / Awaiting Grades";
                    countdownSub.classList.remove('text-gray-500');
                    countdownSub.classList.add('text-success', 'font-bold');
                }
            }
        }
    }

    // Modals handling via dynamic fetching
    function toggleLogModal(show) {
        if (show) {
            const container = document.getElementById('logModalContainer');
            if (!container) return;

            fetch('/student/project/weekly-log-form/')
                .then(response => {
                    if (!response.ok) throw new Error('Failed to load log form');
                    return response.text();
                })
                .then(html => {
                    container.innerHTML = html;
                    const modal = document.getElementById('logModal');
                    if (modal) modal.classList.remove('hidden');
                })
                .catch(error => {
                    console.error('Error fetching weekly log form:', error);
                    alert('Could not load log form. Please try again.');
                });
        } else {
            closeLogModal();
        }
    }

    function closeLogModal() {
        const container = document.getElementById('logModalContainer');
        if (container) {
            container.innerHTML = '';
        }
    }

    function toggleUploadModal(show) {
        if (show) {
            const container = document.getElementById('uploadModalContainer');
            if (!container) return;

            fetch('/student/project/upload-deliverable-form/')
                .then(response => {
                    if (!response.ok) throw new Error('Failed to load upload form');
                    return response.text();
                })
                .then(html => {
                    container.innerHTML = html;
                    const modal = document.getElementById('uploadModal');
                    if (modal) modal.classList.remove('hidden');
                })
                .catch(error => {
                    console.error('Error fetching upload form:', error);
                    alert('Could not load upload form. Please try again.');
                });
        } else {
            closeUploadModal();
        }
    }

    function closeUploadModal() {
        const container = document.getElementById('uploadModalContainer');
        if (container) {
            container.innerHTML = '';
        }
    }

    function updateFileLabel(input) {
        const display = document.getElementById('fileUploadNameDisplay');
        if (display) {
            if (input.files && input.files[0]) {
                display.innerText = input.files[0].name;
                display.classList.add('text-primary');
            } else {
                display.innerText = "Apni file chunein";
                display.classList.remove('text-primary');
            }
        }
    }

    // Interactive Checklist (Persistent via LocalStorage and Project Scope)
    const defaultChecklistItems = [
        "Synopsis Proposal Submission",
        "SRS Documentation Upload",
        "Database Architecture Design",
        "Backend API Endpoints Complete",
        "Frontend Integration UI",
        "Mid-term Review presentation",
        "Final Review & Verification"
    ];

    function loadChecklist() {
        const projectId = window.projectId;
        if (!projectId) return;

        const container = document.getElementById('checklist-items-container');
        if (!container) return;

        // Retrieve from localStorage or set defaults
        let data = localStorage.getItem(`project_${projectId}_checklist`);
        if (!data) {
            data = defaultChecklistItems.map(task => ({ task, completed: false }));
        } else {
            data = JSON.parse(data);
        }

        container.innerHTML = '';
        data.forEach((item, index) => {
            const div = document.createElement('div');
            div.className = 'flex items-center gap-3 py-1.5';
            
            const input = document.createElement('input');
            input.type = 'checkbox';
            input.id = `task-${index}`;
            input.checked = item.completed;
            input.className = 'w-4 h-4 rounded text-primary border-gray-300 dark:border-gray-700 bg-gray-55 focus:ring-primary focus:ring-2 focus:ring-offset-0 cursor-pointer';
            input.addEventListener('change', () => toggleTask(index));

            const label = document.createElement('label');
            label.htmlFor = `task-${index}`;
            label.className = `text-xs cursor-pointer select-none font-medium flex-1 ${item.completed ? 'line-through text-gray-400 dark:text-gray-600' : 'text-gray-700 dark:text-gray-300'}`;
            label.innerText = item.task;

            div.appendChild(input);
            div.appendChild(label);
            container.appendChild(div);
        });

        calculateProgress(data);
    }

    function toggleTask(index) {
        const projectId = window.projectId;
        if (!projectId) return;

        let data = JSON.parse(localStorage.getItem(`project_${projectId}_checklist`));
        if (!data) {
            data = defaultChecklistItems.map(task => ({ task, completed: false }));
        }
        data[index].completed = !data[index].completed;
        localStorage.setItem(`project_${projectId}_checklist`, JSON.stringify(data));
        loadChecklist();
    }

    function calculateProgress(data) {
        const total = data.length;
        const completed = data.filter(item => item.completed).length;
        const percent = total > 0 ? Math.round((completed / total) * 100) : 0;

        const pctText = document.getElementById('checklist-pct');
        const progressFill = document.getElementById('checklist-progress');

        if (pctText) pctText.innerText = `${percent}%`;
        if (progressFill) progressFill.style.width = `${percent}%`;
    }

    // Initialize logic
    document.addEventListener('DOMContentLoaded', () => {
        initCountdown();
        loadChecklist();
    });

    // Expose functions to global scope
    window.toggleLogModal = toggleLogModal;
    window.closeLogModal = closeLogModal;
    window.toggleUploadModal = toggleUploadModal;
    window.closeUploadModal = closeUploadModal;
    window.updateFileLabel = updateFileLabel;
    window.loadChecklist = loadChecklist;
    window.toggleTask = toggleTask;
})();
