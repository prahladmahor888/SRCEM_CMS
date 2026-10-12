(function() {
    function filterHistory() {
        const filterSelect = document.getElementById('leaveFilter');
        if (!filterSelect) return;

        const filterValue = filterSelect.value;
        const rows = document.querySelectorAll('.history-row');

        rows.forEach(row => {
            const rowStatus = row.getAttribute('data-status');
            if (filterValue === 'all' || rowStatus === filterValue) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    }

    // Expose functions to global scope
    window.filterHistory = filterHistory;
})();
