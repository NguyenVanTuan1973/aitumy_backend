export function initColumnSelector() {
    let panel = document.getElementById("column-panel");
    panel.innerHTML = "";

    document.querySelectorAll("thead th").forEach((th, index) => {
        let key = th.dataset.col;
        if (!key) return;

        let checked = localStorage.getItem("col_" + key) !== "0";

        panel.innerHTML += `
            <label style="display:block">
                <input type="checkbox"
                    ${checked ? "checked" : ""}
                    onchange="toggleColumn(${index}, this.checked, '${key}')">
                ${th.innerText}
            </label>
        `;

        toggleColumn(index, checked, key, false);
    });
}

export function toggleColumn(index, show, key, save = true) {
    let table = document.querySelector("table");

    for (let row of table.rows) {
        if (row.cells[index]) {
            row.cells[index].style.display = show ? "" : "none";
        }
    }

    if (save) {
        localStorage.setItem("col_" + key, show ? "1" : "0");
    }
}

export function toggleColumnPanel() {
    let panel = document.getElementById("column-panel");
    panel.style.display = panel.style.display === "none" ? "block" : "none";
}