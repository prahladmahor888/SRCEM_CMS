(function() {
    // --- Modal Logic ---
    function toggleSubmitModal(assignmentId) {
        if (!assignmentId) {
            closeSubmitModal();
            return;
        }
        const container = document.getElementById('submitModalContainer');
        if (!container) return;

        // Fetch dynamic form snippet from server
        fetch(`/assignment-submit-form/${assignmentId}/`)
            .then(response => {
                if (!response.ok) throw new Error('Failed to load submission form');
                return response.text();
            })
            .then(html => {
                container.innerHTML = html;
                const modal = document.getElementById('submitModal');
                if (modal) {
                    modal.classList.remove('hidden');
                }
            })
            .catch(error => {
                console.error('Error fetching submission form:', error);
                alert('Could not load assignment submission form. Please try again.');
            });
    }

    function closeSubmitModal() {
        const container = document.getElementById('submitModalContainer');
        if (container) {
            container.innerHTML = '';
        }
    }

    function updateFileName(input) {
        const display = document.getElementById('fileNameDisplay');
        if (input.files && input.files[0] && display) {
            display.innerText = input.files[0].name;
            display.classList.add('text-primary');
        }
    }

    // --- Tab Filtering Logic ---
    function switchTaskTab(status, btn) {
        // Update UI buttons
        document.querySelectorAll('.tab-btn').forEach(b => {
            b.classList.remove('tab-active');
            b.classList.add('tab-inactive');
        });
        btn.classList.add('tab-active');
        btn.classList.remove('tab-inactive');

        searchAssignments(); // Trigger update with existing search/subject filters
    }

    // --- Unified Search and Filter Logic ---
    function searchAssignments() {
        const searchInput = document.getElementById('assignmentSearch');
        const subjectSelect = document.getElementById('subjectFilter');
        const activeTabBtn = document.querySelector('.tab-btn.tab-active');

        if (!searchInput || !subjectSelect || !activeTabBtn) return;

        const searchQuery = searchInput.value.toLowerCase();
        const subjectQuery = subjectSelect.value;
        const activeTab = activeTabBtn.getAttribute('data-filter');
        const cards = document.querySelectorAll('.assignment-card');

        cards.forEach(card => {
            const h3 = card.querySelector('h3');
            if (!h3) return;
            const title = h3.innerText.toLowerCase();
            const subject = card.getAttribute('data-subject');
            const status = card.getAttribute('data-status');

            const matchesSearch = title.includes(searchQuery);
            const matchesSubject = !subjectQuery || subject === subjectQuery;
            const matchesStatus = activeTab === 'all' || status === activeTab;

            if (matchesSearch && matchesSubject && matchesStatus) {
                card.style.display = 'flex';
            } else {
                card.style.display = 'none';
            }
        });
    }

    function filterByTab(status) {
        const btn = document.querySelector(`.tab-btn[data-filter="${status}"]`);
        if (btn) switchTaskTab(status, btn);
    }

    // Expose functions to global window scope so HTML onclick events can trigger them
    window.toggleSubmitModal = toggleSubmitModal;
    window.closeSubmitModal = closeSubmitModal;
    window.updateFileName = updateFileName;
    window.switchTaskTab = switchTaskTab;
    window.searchAssignments = searchAssignments;
    window.filterByTab = filterByTab;
})();
