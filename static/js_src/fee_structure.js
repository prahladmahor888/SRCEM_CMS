(function() {
    document.addEventListener('DOMContentLoaded', () => {
        const input = document.getElementById("structureSearch");
        if (!input) return;

        input.addEventListener('keyup', () => {
            const filter = input.value.toUpperCase();
            const table = document.getElementById("feeTable");
            if (!table) return;
            const rows = table.getElementsByClassName("fee-row");

            for (let i = 0; i < rows.length; i++) {
                const cells = rows[i].getElementsByTagName("td");
                let rowText = "";
                for (let j = 0; j < cells.length; j++) {
                    rowText += cells[j].textContent || cells[j].innerText;
                }
                if (rowText.toUpperCase().indexOf(filter) > -1) {
                    rows[i].style.display = "";
                } else {
                    rows[i].style.display = "none";
                }
            }
        });
    });
})();
