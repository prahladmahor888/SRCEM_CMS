(function() {
    function openPaymentModal() {
        const container = document.getElementById('paymentModalContainer');
        if (!container) return;

        fetch('/my-fees/payment-form/')
            .then(response => {
                if (!response.ok) throw new Error('Failed to load payment form');
                return response.text();
            })
            .then(html => {
                container.innerHTML = html;
            })
            .catch(error => {
                console.error('Error fetching payment form:', error);
                alert('Could not load payment form. Please try again.');
            });
    }

    function closePaymentModal() {
        const container = document.getElementById('paymentModalContainer');
        if (container) {
            container.innerHTML = '';
        }
    }

    // Close modal when clicking outside of it
    window.onclick = function(event) {
        const modal = document.getElementById('payment-modal');
        if (event.target === modal) {
            closePaymentModal();
        }
    };

    // Expose functions to global scope
    window.openPaymentModal = openPaymentModal;
    window.closePaymentModal = closePaymentModal;
})();
