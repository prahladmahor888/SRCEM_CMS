(function() {
    document.addEventListener('DOMContentLoaded', () => {
        // --- Auto-Slider for Hero Section ---
        const slides = document.querySelectorAll('.transport-slide');
        let currentSlide = 0;

        function nextSlide() {
            if(slides.length === 0) return;
            slides[currentSlide].classList.remove('active');
            currentSlide = (currentSlide + 1) % slides.length;
            slides[currentSlide].classList.add('active');
        }

        if(slides.length > 0) {
            setInterval(nextSlide, 5000); 
        }
    });
})();
