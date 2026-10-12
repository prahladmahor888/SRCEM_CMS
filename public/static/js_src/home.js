(function() {
    // Hero Auto Slider Logic
    function initHeroSlider() {
        const slides = document.querySelectorAll('.hero-slide');
        const dots = document.querySelectorAll('.slide-dot');
        let currentSlide = 0;
        
        function showSlide(index) {
            slides.forEach(s => { 
                s.classList.remove('opacity-100', 'z-10', 'pointer-events-auto'); 
                s.classList.add('opacity-0', 'z-0', 'pointer-events-none'); 
            });
            dots.forEach(d => { d.classList.remove('opacity-100'); d.classList.add('opacity-40'); });
            
            if (slides[index]) {
                slides[index].classList.remove('opacity-0', 'z-0', 'pointer-events-none');
                slides[index].classList.add('opacity-100', 'z-10', 'pointer-events-auto');
            }
            if(dots.length > index && dots[index]) {
                dots[index].classList.remove('opacity-40');
                dots[index].classList.add('opacity-100');
            }
        }

        if(slides.length > 0) {
            setInterval(() => {
                currentSlide = (currentSlide + 1) % slides.length;
                showSlide(currentSlide);
            }, 5000);

            dots.forEach((dot, index) => {
                dot.addEventListener('click', () => {
                    currentSlide = index;
                    showSlide(currentSlide);
                });
            });
        }
    }

    // Important Alerts Modal
    function initAlertsModal() {
        const modal = document.getElementById('noticeModal');
        const backdrop = document.getElementById('noticeModalBackdrop');
        const content = document.getElementById('noticeModalContent');
        const closeBtn = document.getElementById('closeNoticeModal');

        if (!modal || !backdrop || !content || !closeBtn) return;

        // Show modal on load
        setTimeout(() => {
            modal.classList.remove('hidden');
            // Trigger reflow
            void modal.offsetWidth;
            content.classList.remove('scale-95', 'opacity-0');
            content.classList.add('scale-100', 'opacity-100');
        }, 500);

        function closeModal() {
            content.classList.remove('scale-100', 'opacity-100');
            content.classList.add('scale-95', 'opacity-0');
            setTimeout(() => {
                modal.classList.add('hidden');
            }, 300);
        }

        closeBtn.addEventListener('click', closeModal);
        backdrop.addEventListener('click', closeModal);
    }

    document.addEventListener('DOMContentLoaded', () => {
        initHeroSlider();
        initAlertsModal();
    });
})();
