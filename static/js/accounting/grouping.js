// ================= TOGGLE GROUP MODE =================
export function toggleGroupMode() {
    // Thay vì dùng GROUP_MODE, hãy dùng window.APP_STATE.GROUP_MODE
    window.APP_STATE.GROUP_MODE = !window.APP_STATE.GROUP_MODE;

    const btn = document.getElementById("btn-group-mode");
    if (btn) {
        btn.classList.toggle("btn-warning", window.APP_STATE.GROUP_MODE);
        btn.classList.toggle("btn-outline-warning", !window.APP_STATE.GROUP_MODE);
        btn.innerText = window.APP_STATE.GROUP_MODE ? "🔓 Tắt Gom nhóm" : "🔒 Bật Gom nhóm";
    }

    // Gọi lại hàm render bảng để áp dụng chế độ mới
    if (typeof window.renderTable === "function") {
        window.renderTable(window.APP_STATE.CURRENT_DATA);
    }
}

// ================= GROUP ROW =================
export function groupData(data) {
    let result = {};

    data.forEach(row => {
        let buyer = row.buyer_name || "Không rõ KH";
        let number = row.number || "NO_NUMBER";

        if (!result[buyer]) result[buyer] = {};
        if (!result[buyer][number]) result[buyer][number] = [];

        result[buyer][number].push(row);
    });

    return result;
}

export function toggleBuyer(buyer) {
    document.querySelectorAll(`.group-${CSS.escape(buyer)}`)
        .forEach(el => {
            if (el.dataset.hidden === "1") {
                el.style.display = "";
                el.dataset.hidden = "0";
            } else {
                el.style.display = "none";
                el.dataset.hidden = "1";
            }
        });
}

export function toggleInvoice(buyer, number) {
    document.querySelectorAll(`.invoice-${CSS.escape(buyer)}-${CSS.escape(number)}`)
        .forEach(el => {
            if (el.dataset.hidden === "1") {
                el.style.display = "";
                el.dataset.hidden = "0";
            } else {
                el.style.display = "none";
                el.dataset.hidden = "1";
            }
        });
}