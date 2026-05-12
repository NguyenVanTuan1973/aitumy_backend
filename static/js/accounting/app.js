
import {
    generateEntries,
    showEntries,
    generateJournal,
    renderSoTienGui,
    closeJournalForm,
    generateS01,
    generateS61,
    generateS10,
    generateS11,
    generateS12,
    generateS06,
    generateS07,
    generateS07A,
    generateS31,
    generateS34,
    generateS35,
    generateS36,
    generateS37,
    generateS38,
    generateS41a,
    generateS42a


} from "./accounting.js"; // ✅ Gộp chung các hàm từ accounting.js
import { toggleGroupMode, groupData, toggleBuyer, toggleInvoice } from "./grouping.js";
import { updateRow, uploadPDF, uploadInvoice } from "./api.js";

import {
    formatMoney,
    getCSRF,
    exportExcel
} from "./utils.js";


import { initColumnSelector, toggleColumnPanel, toggleColumn } from "./columns.js";
import { renderTable} from "./table.js";

// ✅ 1. KHỞI TẠO STATE
if (!window.APP_STATE) {
    window.APP_STATE = {
        CURRENT_DATA: [],
        currentFile: null,
        currentInvoiceType: 'invoice_out',
        GROUP_MODE: false,
        isProcessing: false,
        activeView: 'table' // Mặc định là xem bảng hóa đơn
    };
}

// ✅ 2. EXPOSE CÁC HÀM RA WINDOW (Bắt buộc để HTML onclick chạy được)
// accounting
window.showEntries = showEntries;
window.generateJournal = generateJournal;
window.renderSoTienGui = renderSoTienGui;
window.closeJournalForm = closeJournalForm;
window.generateS01 = generateS01;
window.generateS61 = generateS61;
window.generateS10 = generateS10;
window.generateS11 = generateS11;
window.generateS12 = generateS12;
window.generateS06 = generateS06;
window.generateS07 = generateS07;
window.generateS07A = generateS07A;
window.generateS31 = generateS31;
window.generateS34 = generateS34;
window.generateS35 = generateS35;
window.generateS36 = generateS36;
window.generateS37 = generateS37;
window.generateS38 = generateS38;
window.generateS41a = generateS41a;
window.generateS41a = generateS42a;


window.toggleGroupMode = toggleGroupMode;
window.renderTable = renderTable;
window.toggleBuyer = toggleBuyer;
window.toggleInvoice = toggleInvoice;

window.updateRow = updateRow;
window.uploadPDF = uploadPDF;
window.loadTab = loadTab;

window.exportExcel = exportExcel;

//✅ 3. EXPOSE CÁC HÀM RA WINDOW
window.toggleColumnPanel = toggleColumnPanel;
window.toggleColumn = toggleColumn;
window.initColumnSelector = initColumnSelector;

// Expose tất cả ra window
window.groupData = groupData;
window.showAccountInput = showAccountInput;

// ================= UPLOAD EXCEL =================
const form = document.getElementById("upload-form");

if (form) {
    form.addEventListener("submit", function(e) {
        e.preventDefault();

        let formData = new FormData(this);
        let btn = form.querySelector("button");

        // UI Feedback
        btn.disabled = true;
        btn.innerHTML = `<span class="spinner-border spinner-border-sm"></span> Đang xử lý...`;

        fetch("/accounting/api/upload-invoice/", {
            method: "POST",
            headers: {
                "X-CSRFToken": getCSRF(),
            },
            body: formData
        })
        .then(res => res.json())
        .then(res => {
            btn.disabled = false;
            btn.innerText = "🚀 Upload & Xử lý";

            if (res.status === "success") {

                window.APP_STATE.CURRENT_DATA = res.data
                    .map((row, index) => {

                        // 🔥 bỏ dòng lỗi
                        if (row.error) return null;

                        // 🔥 bỏ invoice không xác định
                        if (!row.invoice_type || row.invoice_type === "unknown") return null;

                        return {
                            ...row,
                            id: row.id || (index + 1),

                            // 🔥 ĐỊNH KHOẢN NGAY TẠI ĐÂY
                            entries: generateEntries(row, row.invoice_type)
                        };
                    })
                    .filter(Boolean); // 🔥 loại null

                console.log("✅ Dữ liệu OK:", window.APP_STATE.CURRENT_DATA);

                renderTable(window.APP_STATE.CURRENT_DATA);

            } else {
                alert("Lỗi: " + (res.message || "Không xác định"));
            }
        })
        .catch(err => {
            btn.disabled = false;
            btn.innerText = "🚀 Upload & Xử lý";
            console.error("Lỗi Fetch:", err);
            alert("Lỗi kết nối Server");
        });
    });
}

window.formatAllMoneyInTable = function(parent) {
    // Quét tất cả các ô td có class là debit hoặc credit
    const cells = parent.querySelectorAll('.debit, .credit');

    cells.forEach(cell => {
        let rawValue = cell.innerText.trim();

        // Nếu ô trống hoặc là số 0 thì có thể để nguyên hoặc format
        if (rawValue === "" || rawValue === "0") {
            cell.innerText = "-"; // Hoặc "0" tùy bạn
            return;
        }

        // Chuyển đổi về số và format
        // Xóa các ký tự không phải số (trừ dấu chấm thập phân nếu có) trước khi format
        const num = parseFloat(rawValue.replace(/[^0-9.-]+/g, ""));

        if (!isNaN(num)) {
            cell.innerText = formatMoney(num);
            cell.style.textAlign = "right"; // Căn lề phải cho đẹp chuẩn kế toán
        }
    });
};

/* HÀM HIỂN THỊ INPUT ĐỂ NHẬP SỐ TÀI KHOẢN */
function showAccountInput(callback) {

    // Nếu đã tồn tại rồi thì không tạo lại
    let existing = document.getElementById("s38-account-box");
    if (existing) return;

    const container = document.getElementById("report-container");

    const div = document.createElement("div");
    div.id = "s38-account-box";
    div.className = "card p-3 mb-3";

    div.innerHTML = `
        <div class="d-flex align-items-center gap-2">
            <label><b>Nhập tài khoản:</b></label>
            <input id="s38-account" class="form-control" style="width:150px" placeholder="VD: 154" />
            <button class="btn btn-primary btn-sm" id="btn-load-s38">Xem sổ</button>
        </div>
    `;

    container.prepend(div);

    // 🔥 Gắn sự kiện
    document.getElementById("btn-load-s38").onclick = function () {
        const acc = document.getElementById("s38-account").value.trim();

        if (!acc) {
            alert("Vui lòng nhập tài khoản!");
            return;
        }

        callback(acc);
    };
}

document.getElementById("filter-invoice-type").addEventListener("change", function () {

    let type = this.value;
    let data = window.APP_STATE.CURRENT_DATA;

    if (type !== "all") {
        data = data.filter(r => r.invoice_type === type);
    }

    renderTable(data);
});

// ================= LOAD TAB (CHUYỂN MUA VÀO/BÁN RA) =================
function loadTab(type, btn) {
    // 1. Ép kiểu chuẩn cho logic kế toán
    const fullType = (type === 'in' || type === 'invoice_in') ? 'invoice_in' : 'invoice_out';

    // 2. Cập nhật State
    window.APP_STATE.currentInvoiceType = fullType;

    // 3. UI Tab: Cập nhật trạng thái active cho nút bấm
    document.querySelectorAll(".nav-link").forEach(el => el.classList.remove("active"));
    btn.classList.add("active");

    // 4. ẨN FORM NHẬT KÝ (Nếu đang mở): Để tránh nhầm lẫn dữ liệu khi chuyển tab
    const journalForm = document.getElementById("journal-form");
    if (journalForm) journalForm.classList.add("d-none");

    // 5. Nếu chưa có dữ liệu thì dừng lại ở đây
    if (!window.APP_STATE.CURRENT_DATA || window.APP_STATE.CURRENT_DATA.length === 0) return;

    // 6. ✅ TÍNH LẠI ĐỊNH KHOẢN THEO LOẠI HÓA ĐƠN MỚI
    // Việc này đảm bảo khi chuyển sang Mua vào, các TK Nợ/Có sẽ tự động đổi theo logic đầu vào
    window.APP_STATE.CURRENT_DATA.forEach(row => {
        row.entries = generateEntries(row, fullType);
    });

    // 7. Render lại bảng với định khoản mới
    console.log(`Đã chuyển sang tab: ${fullType}, tính lại định khoản cho ${window.APP_STATE.CURRENT_DATA.length} dòng.`);
    renderTable(window.APP_STATE.CURRENT_DATA);
}


// ✅ EXPOSE hàm loadReport (Sổ S05-DN)
window.loadReport = function(type) {
    const container = document.getElementById("report-container");

    if (!window.APP_STATE.CURRENT_DATA || !window.APP_STATE.CURRENT_DATA.length) {
        container.innerHTML = "<p style='color:red'>Chưa có dữ liệu</p>";
        return;
    }

    container.innerHTML = "Đang tải...";

    // 🔥 ĐỊNH NGHĨA cleanedData TẠI ĐÂY (Làm sạch trước khi gửi lên Backend)
    const cleanedData = window.APP_STATE.CURRENT_DATA.map(row => {
         // 🔥 LUÔN generate entries nếu chưa có
        const entries = row.entries && row.entries.length > 0
            ? row.entries
            : generateEntries(row, window.APP_STATE.currentInvoiceType);

        return {
            create_date: row.create_date || row.date || "",
            entries: (row.entries || []).map(entry => ({
                debit: entry.debit || null,
                credit: entry.credit || null,
                // Chú ý dùng hàm cleanNumber hoặc parseFloat ở đây
                amount: parseFloat(entry.amount) || 0
            }))
        };
    }).filter(row => row.entries.length > 0);

    // Gửi lên server
    fetch(`/accounting/report/${type}/`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRF()
        },
        body: JSON.stringify({
            data: cleanedData // Bây giờ cleanedData đã được định nghĩa
        })
    })
    .then(res => {
        if (!res.ok) throw new Error("Lỗi Server");
        return res.text();
    })
    .then(html => {
        container.innerHTML = html;

        // Gọi hàm định dạng tiền sau khi bảng hiện ra (tùy chọn)
        if (window.formatAllMoneyInTable) {
            window.formatAllMoneyInTable(container);
        }
    })
    .catch(err => {
        console.error(err);
        container.innerHTML = "<p style='color:red'>Lỗi khi tạo báo cáo</p>";
    });
};

window.loadTab = loadTab;