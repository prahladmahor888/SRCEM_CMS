(function() {
    document.addEventListener('DOMContentLoaded', function() {
        const classBatchSelect = document.getElementById('classBatchSelect');
        const subjectSelect = document.getElementById('subjectSelect');

        // Dynamic Subject Fetching when Class Selection changes
        if (classBatchSelect && subjectSelect) {
            classBatchSelect.addEventListener('change', async function() {
                const classBatch = this.value;
                if (!classBatch) {
                    subjectSelect.innerHTML = '<option value="">First select class...</option>';
                    return;
                }

                try {
                    const response = await fetch(`?class_batch=${classBatch}`, {
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    });
                    if (!response.ok) throw new Error('Network response was not ok');
                    const data = await response.json();
                    
                    subjectSelect.innerHTML = '<option value="">-- Select Subject --</option>';
                    data.subjects.forEach(sub => {
                        const opt = document.createElement('option');
                        opt.value = sub.id;
                        opt.textContent = `${sub.name} (${sub.code})`;
                        subjectSelect.appendChild(opt);
                    });
                } catch (error) {
                    console.error('Fetch error:', error);
                }
            });
        }

        // --- Search Student ---
        const studentSearch = document.getElementById('studentSearch');
        const tableRows = document.querySelectorAll('.student-row');

        if (studentSearch) {
            studentSearch.addEventListener('input', function(e) {
                const searchTerm = e.target.value.toLowerCase();
                tableRows.forEach(row => {
                    const rollCol = row.querySelector('.roll-col');
                    const nameCol = row.querySelector('.name-col');
                    if (!rollCol || !nameCol) return;
                    
                    const rollNo = rollCol.textContent.toLowerCase();
                    const name = nameCol.textContent.toLowerCase();
                    
                    if (rollNo.includes(searchTerm) || name.includes(searchTerm)) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                });
            });
        }

        // --- Auto-Calculate Grading Logic ---
        const maxMarksInput = document.getElementById('maxMarks');
        const postMaxMarks = document.getElementById('postMaxMarks');
        const subHeaderMaxMarks = document.getElementById('subHeaderMaxMarks');
        const subHeaderPassMarks = document.getElementById('subHeaderPassMarks');
        const markInputs = document.querySelectorAll('.mark-input');

        function updatePassMarks(maxVal) {
            const passVal = Math.ceil((maxVal * 40) / 100);
            if (subHeaderPassMarks) {
                subHeaderPassMarks.textContent = `${passVal} (40%)`;
            }
            if (subHeaderMaxMarks) {
                subHeaderMaxMarks.textContent = maxVal;
            }
            if (postMaxMarks) {
                postMaxMarks.value = maxVal;
            }
            // update max attributes on all mark inputs
            markInputs.forEach(input => {
                input.setAttribute('max', maxVal);
            });
        }

        function calculateGrade(marks, max) {
            if (marks === '' || marks === null || isNaN(marks)) {
                return { grade: '--', status: 'Absent', pass: false };
            }
            
            const numMarks = parseFloat(marks);
            const numMax = parseFloat(max);
            
            if (numMarks > numMax) return { grade: 'ERR', status: 'Invalid', pass: false };
            if (numMarks < 0) return { grade: 'ERR', status: 'Invalid', pass: false };

            const percentage = (numMarks / numMax) * 100;
            
            let grade = 'F';
            let pass = false;

            if (percentage >= 90) { grade = 'A+'; pass = true; }
            else if (percentage >= 80) { grade = 'A'; pass = true; }
            else if (percentage >= 70) { grade = 'B+'; pass = true; }
            else if (percentage >= 60) { grade = 'B'; pass = true; }
            else if (percentage >= 50) { grade = 'C+'; pass = true; }
            else if (percentage >= 40) { grade = 'C'; pass = true; }
            else { grade = 'F'; pass = false; }

            return { grade, status: pass ? 'Pass' : 'Fail', pass };
        }

        function updateRowLogic(inputEl) {
            const row = inputEl.closest('tr');
            if (!row) return;
            const gradeCol = row.querySelector('.grade-col');
            const statusCol = row.querySelector('.status-col');
            const maxVal = parseFloat(maxMarksInput ? maxMarksInput.value : 30) || 30;

            // Clear red border error styling
            inputEl.classList.remove('border-red-500', 'focus:border-red-500', 'focus:ring-red-500', 'text-red-600');

            const result = calculateGrade(inputEl.value, maxVal);

            // Update Grade Text & Color
            if (gradeCol) {
                gradeCol.textContent = result.grade;
                gradeCol.className = 'p-4 text-center font-extrabold grade-col text-lg ';
                
                if (result.grade === 'ERR') {
                    gradeCol.classList.add('text-secondary');
                    inputEl.classList.add('border-red-500', 'focus:border-red-500', 'focus:ring-red-500', 'text-red-600');
                } else if (result.grade === '--') {
                    gradeCol.classList.add('text-gray-400');
                    inputEl.classList.add('border-gray-300', 'dark:border-gray-700');
                } else if (result.grade === 'F') {
                    gradeCol.classList.add('text-secondary');
                } else {
                    gradeCol.classList.add('text-primary', 'dark:text-blue-400');
                }
            }

            // Update Status Badge
            if (statusCol) {
                if (result.status === 'Pass') {
                    statusCol.innerHTML = '<span class="inline-block px-2 py-1 bg-green-500/10 text-green-700 dark:text-green-400 border border-green-500/20 text-[10px] font-bold rounded-2xl uppercase tracking-wider">Pass</span>';
                } else if (result.status === 'Fail') {
                    statusCol.innerHTML = '<span class="inline-block px-2 py-1 bg-red-500/10 text-red-700 dark:text-red-400 border border-red-500/20 text-[10px] font-bold rounded-2xl uppercase tracking-wider">Fail</span>';
                } else if (result.status === 'Absent') {
                    statusCol.innerHTML = '<span class="inline-block px-2 py-1 bg-gray-100 text-gray-600 border border-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600 text-[10px] font-bold rounded-2xl uppercase tracking-wider">Absent</span>';
                } else {
                    statusCol.innerHTML = '<span class="inline-block px-2 py-1 bg-red-500/10 text-red-700 dark:text-red-400 border border-red-500/20 text-[10px] font-bold rounded-2xl uppercase tracking-wider">Invalid</span>';
                }
            }
        }

        markInputs.forEach(input => {
            input.addEventListener('input', function() {
                const max = parseFloat(maxMarksInput ? maxMarksInput.value : 30) || 30;
                if (parseFloat(this.value) > max) {
                    this.value = max;
                }
                updateRowLogic(this);
            });
            // Initial calculation call
            updateRowLogic(input);
        });

        if (maxMarksInput) {
            maxMarksInput.addEventListener('input', () => {
                const maxVal = parseFloat(maxMarksInput.value) || 30;
                updatePassMarks(maxVal);
                markInputs.forEach(input => {
                    const max = parseFloat(maxMarksInput.value) || 30;
                    if (parseFloat(input.value) > max) {
                        input.value = max;
                    }
                    updateRowLogic(input);
                });
            });
            // Run initially to set passing marks text
            const initialMax = parseFloat(maxMarksInput.value) || 30;
            updatePassMarks(initialMax);
        }
    });
})();
