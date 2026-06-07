(function() {
    document.addEventListener('DOMContentLoaded', () => {
        const entryRadios = document.querySelectorAll('input[name="entryType"]');
        const regularSection = document.getElementById('regularSection');
        const lateralSection = document.getElementById('lateralSection');
        const uploadLabel = document.getElementById('uploadLabel');
        const uploadText = document.getElementById('uploadText');

        if (entryRadios && regularSection && lateralSection) {
            entryRadios.forEach(radio => {
                radio.addEventListener('change', (e) => {
                    const type = e.target.value;

                    if (type === 'lateral') {
                        // Lateral Entry case
                        regularSection.classList.add('hidden');
                        lateralSection.classList.remove('hidden');
                        if (uploadLabel) uploadLabel.innerText = "Diploma / Graduation Marksheet *";
                        if (uploadText) uploadText.innerText = "Upload Diploma Marksheet";
                    } else {
                        // Regular Admission case
                        regularSection.classList.remove('hidden');
                        lateralSection.classList.add('hidden');
                        if (uploadLabel) uploadLabel.innerText = "Class 12th Marksheet *";
                        if (uploadText) uploadText.innerText = "Upload 12th Marksheet";
                    }
                });
            });
        }
    });
})();
