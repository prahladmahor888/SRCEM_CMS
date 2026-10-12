(function() {
    document.addEventListener('DOMContentLoaded', function() {
        const branchSelect = document.getElementById('id_branch');
        const semesterSelect = document.getElementById('id_semester');
        const allotmentSelect = document.getElementById('id_allotment');
 
        function updateAllotments() {
            if (!branchSelect || !semesterSelect || !allotmentSelect) return;

            const branchId = branchSelect.value;
            const semester = semesterSelect.value;
            
            if (!branchId && !semester) return;

            allotmentSelect.innerHTML = '<option value="">--- Loading Allotments ---</option>';
            
            const baseUrl = window.filterAllotmentsUrl || '/filter-allotments/';
            const url = `${baseUrl}?branch=${branchId}&semester=${semester}`;
            
            fetch(url)
                .then(response => {
                    if (!response.ok) throw new Error('Network response was not ok');
                    return response.json();
                })
                .then(data => {
                    allotmentSelect.innerHTML = '<option value="">--- Select Subject/Faculty ---</option>';
                    data.allotments.forEach(item => {
                        const option = document.createElement('option');
                        option.value = item.id;
                        option.textContent = item.label;
                        allotmentSelect.appendChild(option);
                    });
                })
                .catch(err => {
                    console.error('Error fetching allotments:', err);
                    allotmentSelect.innerHTML = '<option value="">--- Error Loading Data ---</option>';
                });
        }
 
        if (branchSelect && semesterSelect && allotmentSelect) {
            branchSelect.addEventListener('change', updateAllotments);
            semesterSelect.addEventListener('change', updateAllotments);
        }
    });
})();
