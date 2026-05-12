// Đảm bảo hàm này nằm ở ĐẦU FILE, trước tất cả các hàm khác
const cleanNumber = (val) => {
    if (val === undefined || val === null || val === "") return 0;
    if (typeof val === 'number') return val;
    let str = val.toString().trim();
    if (str.startsWith('(') && str.endsWith(')')) {
        str = '-' + str.substring(1, str.length - 1);
    }
    let cleaned = str.replace(/\./g, '').replace(',', '.');
    const num = parseFloat(cleaned);
    return isNaN(num) ? 0 : num;
};

// Đưa ra phạm vi toàn cục để chắc chắn không lỗi ReferenceError
window.cleanNumber = cleanNumber;

// ✅ XÓA dòng import CURRENT_DATA vì nó không còn tồn tại trong app.js
import { formatMoney, getCSRF } from "./utils.js";


/**
 * Lấy State tổng của ứng dụng
 */
function getState() {
    return window.APP_STATE;
}


/**
 * Hàm sinh định khoản kế toán
 */
export function generateEntries(row, type) {

    let entries = [];

    // =========================
    // ÉP KIỂU SỐ
    // =========================
    let amount =
        Number(row.amount) || 0;

    let tax =
        Number(row.tax) || 0;

    let discount_total =
        Number(row.discount_total) || 0;

    let fee_total =
        Number(row.fee_total) || 0;

    // Tổng thanh toán
    let total =
        amount
        + tax
        - discount_total
        - fee_total;

    // =========================
    // TK THANH TOÁN
    // =========================
    let paymentAcc = {
        cash: "111",
        bank: "112",
        debt: "331"
    }[row.payment] || "331";

    // =====================================================
    // MUA VÀO
    // =====================================================
    if (type === "invoice_in") {

        // =============================================
        // XÁC ĐỊNH TK CHI PHÍ / HÀNG HÓA
        // =============================================
        let property =
            (row.property || row["tính chất"] || "")
            .toString()
            .trim()
            .toLowerCase();

        // 🔥 FIX:
        // toLowerCase() => phải so "hàng hóa"
        let debitAcc =
            (property === "hàng hóa")
            ? "156"
            : "154";

        // =============================================
        // GIÁ TRỊ HÀNG
        // N154/156 - C331
        // =============================================
        if (amount > 0) {

            entries.push({

                debit: debitAcc,

                credit: paymentAcc,

                amount: amount
            });
        }

        // =============================================
        // THUẾ GTGT
        // N1331 - C331
        // =============================================
        if (tax > 0) {

            entries.push({

                debit: "1331",

                credit: paymentAcc,

                amount: tax
            });
        }
    }

    // =====================================================
    // BÁN RA
    // =====================================================
    else if (type === "invoice_out") {

        // =============================================
        // TK THU TIỀN
        // =============================================
        let debitAcc =
            (paymentAcc === "331")
            ? "131"
            : paymentAcc;

        // =============================================
        // DOANH THU
        // N111/112/131 - C511
        // =============================================
        if (amount > 0) {

            entries.push({

                debit: debitAcc,

                credit: "511",

                amount: amount
            });
        }

        // =============================================
        // THUẾ GTGT
        // N111/112/131 - C33311
        // =============================================
        if (tax > 0) {

            entries.push({

                debit: debitAcc,

                credit: "33311",

                amount: tax
            });
        }
    }

    return entries;
}


/**
 * Hiển thị Modal định khoản
 */
export function showEntries(id) {
    // ✅ Lấy state trực tiếp từ window
    let state = window.APP_STATE;

    if (!state || !state.CURRENT_DATA) {
        console.error("Hệ thống chưa sẵn sàng hoặc dữ liệu rỗng.");
        return;
    }

    // ✅ Tìm dòng dựa trên ID (luôn ép kiểu String để so sánh an toàn)
    let row = state.CURRENT_DATA.find(r => String(r.id) === String(id));

    if (!row) {
        console.warn("Không tìm thấy dòng có ID:", id);
        alert("Không tìm thấy dòng dữ liệu");
        return;
    }

    // Nếu dòng chưa có sẵn entries (do đổi tab hoặc upload lỗi), tính toán lại ngay
    let entries = row.entries || generateEntries(row, state.currentInvoiceType);

    if (!entries || entries.length === 0) {
        alert("Dòng này chưa có dữ liệu định khoản");
        return;
    }

    // Render HTML vào modal
    let html = "";
    entries.forEach(e => {

        // Dòng Nợ
        if (e.debit) {
            html += `
            <tr>
                <td>
                    <span class="badge bg-success">
                        Nợ
                    </span>
                </td>
                <td>${e.debit}</td>
                <td class="text-end">
                    ${formatMoney(e.amount)}
                </td>
            </tr>`;
        }

        // Dòng Có
        if (e.credit) {
            html += `
            <tr>
                <td>
                    <span class="badge bg-danger">
                        Có
                    </span>
                </td>
                <td>${e.credit}</td>
                <td class="text-end">
                    ${formatMoney(e.amount)}
                </td>
            </tr>`;
        }
    });

    const bodyEl = document.getElementById("entry-body");
    if (bodyEl) {
        bodyEl.innerHTML = html;
        // Hiển thị Bootstrap Modal
        const modalEl = document.getElementById("entryModal");
        if (modalEl) {
            const modal = new bootstrap.Modal(modalEl);
            modal.show();
        }
    }
}

/* =========================
   🔥 RENDER NHẬT KÝ CHUNG
========================= */
export function generateJournal() {

    let state = window.APP_STATE;

    if (!state.CURRENT_DATA || state.CURRENT_DATA.length === 0) {
        alert("Không có dữ liệu để tạo sổ!");
        return;
    }

    console.log("🚀 SEND DATA:", state.CURRENT_DATA);

    fetch("/accounting/api/generate-journal/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRF(),
        },
        body: JSON.stringify({
            data: state.CURRENT_DATA
        })
    })
    .then(res => {
        if (!res.ok) {
            throw new Error("Server lỗi: " + res.status);
        }
        return res.json(); // 🔥 BẮT BUỘC
    })
    .then(data => {
        console.log("📥 RESPONSE:", data);

        if (data.success) {
            const container = document.getElementById("report-container");
            container.innerHTML = data.html;

            window.registerData = data.register_data;

            // 🔥 FORMAT TIỀN NGAY SAU KHI RENDER
            container.querySelectorAll(".money").forEach(el => {
                let raw = el.innerText.replace(/[^\d.-]/g, "");
                if (!raw) return;

                el.innerText = formatMoney(raw);
            });

        } else {
            alert("Lỗi: " + (data.error || "Không xác định"));
        }
    })
    .catch(err => {
        console.error("❌ ERROR:", err);
        alert("Không thể kết nối server");
    });
}


/* =========================
   🔥 RENDER SỔ CÁI
========================= */
export function renderJournal(data) {
    const form = document.getElementById("journal-form");
    const tbody = document.getElementById("journal-body");
    const tfoot = document.getElementById("journal-footer");

    if (!form || !tbody) return;

    form.classList.remove("d-none");

    tbody.innerHTML = "";
    tfoot.innerHTML = "";

    let totalNo = 0;
    let totalCo = 0;

    data.forEach((row, index) => {

        let psNo = Number(row.ps_no || 0);
        let psCo = Number(row.ps_co || 0);

        totalNo += psNo;
        totalCo += psCo;

        let isTotal = row.dien_giai === "Cộng";

        const tr = document.createElement("tr");
        if (isTotal) tr.classList.add("row-total");

        tr.innerHTML = `
            <td class="text-center">${index + 1}</td> <!-- 🔥 STT -->
            <td>${row.so_ct || ""}</td>
            <td>${row.ngay_ct || ""}</td>
            <td>${row.dien_giai || ""}</td>
            <td class="text-center">${row.tai_khoan || ""}</td>
            <td class="text-end">${formatMoney(psNo)}</td>
            <td class="text-end">${formatMoney(psCo)}</td>
        `;

        tbody.appendChild(tr);
    });

}


/* =========================
   🔥 RENDER SỔ TIỀN GỬI
========================= */
export async function renderSoTienGui() {
    let state = window.APP_STATE;
    if (!state.CURRENT_DATA || state.CURRENT_DATA.length === 0) {
        alert("Không có dữ liệu!");
        return;
    }

    try {
        const res = await fetch("/accounting/report/so-tien-gui/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCSRF()
            },
            body: JSON.stringify({ data: state.CURRENT_DATA })
        });

        const data = await res.json();

        if (data.success) {
            const container = document.getElementById("report-container");
            container.innerHTML = data.html;

            window.registerData = data.register_data;

            // 🔥 SỬ DỤNG LOGIC GIỐNG SỔ THUẾ (S61)
            container.querySelectorAll(".money").forEach(el => {
                // Xóa các ký tự phân cách cũ (dấu phẩy từ intcomma)
                let raw = el.innerText.replace(/[^\d.-]/g, "");
                if (!raw || raw === "") return;

                // Format lại bằng hàm dùng chung trong utils.js
                el.innerText = formatMoney(raw);
            });

        } else {
            alert("Lỗi: " + (data.error || "Không xác định"));
        }
    } catch (err) {
        console.error("Network error:", err);
    }
}


/* =========================
   🔥 RENDER SỔ THEO DÕI THUẾ GTGT
========================= */
export function generateS61() {

    let state = window.APP_STATE;

    if (!state.CURRENT_DATA || state.CURRENT_DATA.length === 0) {
        alert("Không có dữ liệu!");
        return;
    }

    fetch("/accounting/report/generate-s61/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRF(),
        },
        body: JSON.stringify({
            data: state.CURRENT_DATA
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            const container = document.getElementById("report-container");
            container.innerHTML = data.html;

            window.registerData = data.register_data;

            // format tiền
            container.querySelectorAll(".money").forEach(el => {
                let raw = el.innerText.replace(/[^\d.-]/g, "");
                if (!raw) return;
                el.innerText = formatMoney(raw);
            });

        } else {
            alert(data.error || "Lỗi");
        }
    });
}

/* =========================
   🔥 RENDER SỔ CHI TIẾT VẬT LIỆU, DỤNG CỤ, SP, HH
========================= */
export function generateS10(selectedProduct = "") {

    let state = window.APP_STATE;

    if (!state.CURRENT_DATA || state.CURRENT_DATA.length === 0) {

        alert("Không có dữ liệu để tạo S10!");

        return;
    }

    fetch("/accounting/report/generate-s10/", {

        method: "POST",

        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRF(),
        },

        body: JSON.stringify({

            data: state.CURRENT_DATA,

            // 🔥 HÀNG HÓA USER CHỌN
            product: selectedProduct
        })
    })

    .then(res => {

        if (!res.ok) {

            throw new Error(
                "Server lỗi: " + res.status
            );
        }

        return res.json();
    })

    .then(data => {

        if (!data.success) {

            alert(
                "Lỗi: " +
                (data.error || "Không xác định")
            );

            return;
        }

        // =====================================
        // 🔥 HTML REPORT
        // =====================================
        const container =
            document.getElementById("report-container");

        container.innerHTML = data.html;

        // =====================================
        // 🔥 REGISTER DATA
        // =====================================
        window.registerData = data.register_data;

        // =====================================
        // 🔥 FORMAT MONEY
        // =====================================
        container
            .querySelectorAll(".money")
            .forEach(el => {

                let raw =
                    el.innerText.replace(/[^\d.-]/g, "");

                if (!raw) return;

                el.innerText =
                    Number(raw).toLocaleString("vi-VN");
            });

        // =====================================
        // 🔥 DROPDOWN HÀNG HÓA
        // =====================================
        renderS10ProductFilter(
            data.product_options || [],
            data.selected_product || ""
        );
    })

    .catch(err => {

        console.error("❌ ERROR S10:", err);

        alert("Không thể kết nối server");
    });
}


/**
 * =====================================
 * 🔥 DROPDOWN CHỌN HÀNG HÓA
 * =====================================
 */
function renderS10ProductFilter(
    productOptions = [],
    selectedProduct = ""
) {

    const filterBox =
        document.getElementById("s10-product-filter");

    if (!filterBox) return;

    let html = `
        <label class="form-label fw-bold">
            Chọn hàng hóa
        </label>

        <select
            class="form-select"
            id="s10-product-select"
        >
            <option value="">
                -- Chọn hàng hóa --
            </option>
    `;

    productOptions.forEach(item => {

        html += `
            <option
                value="${item.value}"
                ${
                    item.value === selectedProduct
                    ? "selected"
                    : ""
                }
            >
                ${item.label}
            </option>
        `;
    });

    html += `</select>`;

    filterBox.innerHTML = html;

    // =====================================
    // 🔥 CHANGE EVENT
    // =====================================
    const select =
        document.getElementById("s10-product-select");

    if (select) {

        select.addEventListener("change", function () {

            generateS10(this.value);
        });
    }
}



/* =========================
   🔥 RENDER SỔ TỔNG HỢP VẬT LIỆU, DỤNG CỤ, SP, HH
========================= */
export function generateS11() {

    let state = window.APP_STATE;

    if (!state.CURRENT_DATA || state.CURRENT_DATA.length === 0) {
        alert("Không có dữ liệu!");
        return;
    }

    fetch("/accounting/report/generate-s11/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRF(),
        },
        body: JSON.stringify({
            data: state.CURRENT_DATA
        })
    })
    .then(res => res.json())
    .then(data => {

        if (data.success) {

            const container = document.getElementById("report-container");
            container.innerHTML = data.html;

            window.registerData = data.register_data;

            // format tiền
            container.querySelectorAll(".money").forEach(el => {
                let raw = el.innerText.replace(/[^\d.-]/g, "");
                if (!raw) return;
                el.innerText = formatMoney(raw);
            });

        } else {
            alert(data.error || "Lỗi");
        }

    })
    .catch(err => {
        console.error(err);
        alert("Lỗi kết nối");
    });
}

/* =========================
   🔥 RENDER THẺ KHO (SỔ KHO)
========================= */
export function generateS12(product = null) {

    let state = window.APP_STATE;

    if (!state.CURRENT_DATA || state.CURRENT_DATA.length === 0) {
        alert("Không có dữ liệu!");
        return;
    }

    fetch("/accounting/report/generate-s12/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRF(),
        },
        body: JSON.stringify({
            data: state.CURRENT_DATA,
            product: product
        })
    })
    .then(res => res.json())
    .then(data => {

        if (data.success) {

            const container = document.getElementById("report-container");
            container.innerHTML = data.html;

            window.registerData = data.register_data;

            // format tiền
            container.querySelectorAll(".money").forEach(el => {
                let raw = el.innerText.replace(/[^\d.-]/g, "");
                if (!raw) return;
                el.innerText = formatMoney(raw);
            });

        } else {
            alert(data.error);
        }

    })
    .catch(err => {
        console.error(err);
        alert("Lỗi kết nối");
    });
}

/* =========================
   🔥 RENDER BẢNG CÂN ĐỐI SỐ PHÁT SINH
========================= */
export function generateS06() {

    let state = window.APP_STATE;

    if (!state.CURRENT_DATA || state.CURRENT_DATA.length === 0) {
        alert("Không có dữ liệu!");
        return;
    }

    fetch("/accounting/report/generate-s06/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRF(),
        },
        body: JSON.stringify({
            data: state.CURRENT_DATA
        })
    })
    .then(res => res.json())
    .then(data => {

        if (data.success) {

            const container = document.getElementById("report-container");
            container.innerHTML = data.html;

            window.registerData = data.register_data;

            // format tiền
            container.querySelectorAll(".money").forEach(el => {
                let raw = el.innerText.replace(/[^\d.-]/g, "");
                if (!raw) return;
                el.innerText = formatMoney(raw);
            });

        } else {
            alert(data.error);
        }

    })
    .catch(err => {
        console.error(err);
        alert("Lỗi kết nối");
    });
}

/* =========================
   🔥 RENDER SỔ QUỸ TIỀN MẶT
========================= */
export function generateS07() {

    let state = window.APP_STATE;

    if (!state.CURRENT_DATA || state.CURRENT_DATA.length === 0) {
        alert("Không có dữ liệu!");
        return;
    }

    fetch("/accounting/report/generate-s07/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRF(),
        },
        body: JSON.stringify({
            data: state.CURRENT_DATA
        })
    })
    .then(res => res.json())
    .then(data => {

        if (data.success) {
            const container = document.getElementById("report-container");
            container.innerHTML = data.html;

            // 🔥 THÊM DÒNG NÀY (quan trọng nhất)
            window.registerData = data.register_data;

            // format tiền
            container.querySelectorAll(".money").forEach(el => {
                let raw = el.innerText.replace(/[^\d.-]/g, "");
                if (!raw) return;
                el.innerText = formatMoney(raw);
            });
        } else {
            alert(data.error);
        }

    })
    .catch(err => {
        console.error(err);
        alert("Lỗi kết nối");
    });
}

/* =========================
   🔥 RENDER SỔ KẾ TOÁN CHI TIẾT QUỸ TIỀN MẶT
========================= */
export function generateS07A() {

    let state = window.APP_STATE;

    if (!state.CURRENT_DATA || state.CURRENT_DATA.length === 0) {
        alert("Không có dữ liệu!");
        return;
    }

    fetch("/accounting/report/generate-s07a/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRF(),
        },
        body: JSON.stringify({
            data: state.CURRENT_DATA
        })
    })
    .then(res => res.json())
    .then(data => {

        if (data.success) {
            const container = document.getElementById("report-container");
            container.innerHTML = data.html;

            window.registerData = data.register_data;

            // format tiền
            container.querySelectorAll(".money").forEach(el => {
                let raw = el.innerText.replace(/[^\d.-]/g, "");
                if (!raw) return;
                el.innerText = formatMoney(raw);
            });

        } else {
            alert(data.error);
        }

    })
    .catch(err => {
        console.error(err);
        alert("Lỗi kết nối");
    });
}

/* =========================
   🔥 RENDER SỔ CHI TIẾT THANH TOÁN MUA. BÁN
========================= */
export function generateS31(account = "131") {

    let state = window.APP_STATE;

    if (!state.CURRENT_DATA || state.CURRENT_DATA.length === 0) {
        alert("Không có dữ liệu!");
        return;
    }

    fetch("/accounting/report/generate-s31/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRF(),
        },
        body: JSON.stringify({
            data: state.CURRENT_DATA,
            account: account
        })
    })
    .then(res => res.json())
    .then(data => {

        if (data.success) {

            const container = document.getElementById("report-container");
            container.innerHTML = data.html;

            window.registerData = data.register_data;

            // format tiền
            container.querySelectorAll(".money").forEach(el => {
                let raw = el.innerText.replace(/[^\d.-]/g, "");
                if (!raw) return;
                el.innerText = formatMoney(raw);
            });

        } else {
            alert(data.error);
        }

    })
    .catch(err => {
        console.error(err);
        alert("Lỗi kết nối");
    });
}

/* =========================
   🔥 RENDER SỔ CHI TIẾT TIÈN VAY
========================= */
export function generateS34() {

    let state = window.APP_STATE;

    if (!state.CURRENT_DATA || state.CURRENT_DATA.length === 0) {
        alert("Không có dữ liệu!");
        return;
    }

    fetch("/accounting/report/generate-s34/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRF(),
        },
        body: JSON.stringify({
            data: state.CURRENT_DATA
        })
    })
    .then(res => res.json())
    .then(data => {

        if (data.success) {

            const container = document.getElementById("report-container");
            container.innerHTML = data.html;

            window.registerData = data.register_data;

            // format tiền
            container.querySelectorAll(".money").forEach(el => {
                let raw = el.innerText.replace(/[^\d.-]/g, "");
                if (!raw) return;
                el.innerText = formatMoney(raw);
            });

        } else {
            alert(data.error);
        }

    })
    .catch(err => {
        console.error(err);
        alert("Lỗi kết nối");
    });
}

/* =========================
   🔥 RENDER SỔ CHI TIẾT BÁN HÀNG
========================= */
export function generateS35() {

    let state = window.APP_STATE;

    if (!state.CURRENT_DATA || state.CURRENT_DATA.length === 0) {
        alert("Không có dữ liệu!");
        return;
    }

    fetch("/accounting/report/generate-s35/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRF(),
        },
        body: JSON.stringify({
            data: state.CURRENT_DATA
        })
    })
    .then(res => res.json())
    .then(data => {

        if (data.success) {

            const container = document.getElementById("report-container");
            container.innerHTML = data.html;

            window.registerData = data.register_data;

            // format tiền
            container.querySelectorAll(".money").forEach(el => {
                let raw = el.innerText.replace(/[^\d.-]/g, "");
                if (!raw) return;
                el.innerText = formatMoney(raw);
            });

        } else {
            alert(data.error);
        }

    })
    .catch(err => {
        console.error(err);
        alert("Lỗi kết nối");
    });
}

/* =========================
   🔥 RENDER SỔ CHI PHÍ SẢN XUẤT KINH DOANH
========================= */
export function generateS36() {

    let state = window.APP_STATE;

    if (!state.CURRENT_DATA || state.CURRENT_DATA.length === 0) {
        alert("Không có dữ liệu!");
        return;
    }

    fetch("/accounting/report/generate-s36/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRF(),
        },
        body: JSON.stringify({
            data: state.CURRENT_DATA
        })
    })
    .then(res => res.json())
    .then(data => {

        if (data.success) {

            const container = document.getElementById("report-container");
            container.innerHTML = data.html;

            window.registerData = data.register_data;

            // format tiền
            container.querySelectorAll(".money").forEach(el => {
                let raw = el.innerText.replace(/[^\d.-]/g, "");
                if (!raw) return;
                el.innerText = formatMoney(raw);
            });

        } else {
            alert(data.error);
        }

    })
    .catch(err => {
        console.error(err);
        alert("Lỗi kết nối");
    });
}

/* =========================
   🔥 RENDER NHẬT KÝ SỔ CÁI
========================= */
export function generateS01() {

    let state = window.APP_STATE;

    if (!state.CURRENT_DATA || state.CURRENT_DATA.length === 0) {
        alert("Không có dữ liệu!");
        return;
    }

    fetch("/accounting/report/generate-s01/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRF(),
        },
        body: JSON.stringify({
            data: state.CURRENT_DATA
        })
    })
    .then(res => res.json())
    .then(data => {

        if (data.success) {
            const container = document.getElementById("report-container");
            container.innerHTML = data.html;

            window.registerData = data.register_data;

            // format tiền
            container.querySelectorAll(".money").forEach(el => {
                let raw = el.innerText.replace(/[^\d.-]/g, "");
                if (!raw) return;
                el.innerText = formatMoney(raw);
            });

        } else {
            alert(data.error);
        }

    })
    .catch(err => {
        console.error(err);
        alert("Lỗi kết nối");
    });
}

/* =========================
   🔥 RENDER THẺ TÍNH GIÁ THÀNH SP DV
========================= */
export function generateS37() {

    let state = window.APP_STATE;

    if (!state.CURRENT_DATA || state.CURRENT_DATA.length === 0) {
        alert("Không có dữ liệu!");
        return;
    }

    fetch("/accounting/report/generate-s37/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRF(),
        },
        body: JSON.stringify({
            data: state.CURRENT_DATA
        })
    })
    .then(res => res.json())
    .then(data => {

        if (data.success) {
            const container = document.getElementById("report-container");
            container.innerHTML = data.html;

            window.registerData = data.register_data;

            // format tiền
            container.querySelectorAll(".money").forEach(el => {
                let raw = el.innerText.replace(/[^\d.-]/g, "");
                if (!raw) return;
                el.innerText = formatMoney(raw);
            });

        } else {
            alert(data.error);
        }

    })
    .catch(err => {
        console.error(err);
        alert("Lỗi kết nối");
    });
}

/* =========================
   🔥 RENDER SỔ CHI TIẾT CÁC TÀI KHOẢN
========================= */
export function generateS38() {

    let state = window.APP_STATE;

    if (!state || !state.CURRENT_DATA || state.CURRENT_DATA.length === 0) {
        alert("Không có dữ liệu!");
        return;
    }

    // 🔥 Lấy account nếu có sẵn
    let accountInput = document.getElementById("s38-account");
    let account = accountInput ? accountInput.value.trim() : "";

    // 🔥 Nếu chưa có → hiện input cho user nhập
    if (!account) {
        showAccountInput((acc) => {
            callS38API(acc, state.CURRENT_DATA);
        });
        return;
    }

    // 🔥 Nếu đã có → gọi luôn
    callS38API(account, state.CURRENT_DATA);
}


/* HÀM LẤY CHI TIẾT THEO SỐ TÀI KHOẢN */
function callS38API(account, dataInput) {

    fetch("/accounting/report/generate-s38/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRF(),
        },
        body: JSON.stringify({
            data: dataInput,
            account: account
        })
    })
    .then(res => res.json())
    .then(resData => {

        if (resData.success) {

            const container = document.getElementById("report-container");
            container.innerHTML = resData.html;

              window.registerData = resData.register_data;

            // format tiền
            container.querySelectorAll(".money").forEach(el => {
                let raw = (el.innerText || "").replace(/[^\d.-]/g, "");
                if (!raw) return;
                el.innerText = formatMoney(raw);
            });

        } else {
            alert(resData.error || "Có lỗi xảy ra");
        }

    })
    .catch(err => {
        console.error("S38 ERROR:", err);
        alert("Lỗi kết nối server");
    });
}

/* =========================
   🔥 RENDER SỔ CHI TIẾT THEO DÕIDAAFU TƯ VÀO CTY LIÊN DOANH
========================= */
export function generateS41a() {
    let state = window.APP_STATE;

    if (!state.CURRENT_DATA || state.CURRENT_DATA.length === 0) {
        alert("Không có dữ liệu");
        return;
    }

    // 1. Lấy token từ hàm bạn đã viết
    const token = getCSRF();

    fetch("/accounting/report/generate-s41a/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            // 2. Bắt buộc phải có Header này để Django không trả về lỗi 403
            "X-CSRFToken": token,
        },
        body: JSON.stringify({
            data: state.CURRENT_DATA
        })
    })
    .then(res => {
        // Kiểm tra nếu không phải JSON (thường là trang lỗi HTML)
        const contentType = res.headers.get("content-type");
        if (!res.ok || !contentType || !contentType.includes("application/json")) {
            return res.text().then(text => {
                console.error("Server Response:", text); // Xem lỗi Python tại đây
                throw new Error("Server không trả về JSON hợp lệ. Có thể lỗi logic bên trong View.");
            });
        }
        return res.json();
    })
    .then(data => {
        if (data.success) {
            const container = document.getElementById("report-container");
            if (container) {
                container.innerHTML = data.html;

                window.registerData = data.register_data;

                // format tiền...
                container.querySelectorAll(".money").forEach(el => {
                    let raw = (el.innerText || "").replace(/[^\d.-]/g, "");
                    if (!raw) return;
                    el.innerText = formatMoney(raw);
                });
            }
        } else {
            alert("Lỗi từ Server: " + (data.error || "Không xác định"));
        }
    })
    .catch(err => {
        console.error("ERROR:", err);
        alert(err.message);
    });
}

/* =========================
   🔥 RENDER SỔ CHI TIẾT THEO DÕIDAAFU TƯ VÀO CTY LIÊN KẾT
========================= */
export function generateS42a() {
    let state = window.APP_STATE;

    if (!state.CURRENT_DATA || state.CURRENT_DATA.length === 0) {
        alert("Không có dữ liệu");
        return;
    }

    // 1. Lấy token từ hàm bạn đã viết
    const token = getCSRF();

    fetch("/accounting/report/generate-s42a/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            // 2. Bắt buộc phải có Header này để Django không trả về lỗi 403
            "X-CSRFToken": token,
        },
        body: JSON.stringify({
            data: state.CURRENT_DATA
        })
    })
    .then(res => {
        // Kiểm tra nếu không phải JSON (thường là trang lỗi HTML)
        const contentType = res.headers.get("content-type");
        if (!res.ok || !contentType || !contentType.includes("application/json")) {
            return res.text().then(text => {
                console.error("Server Response:", text); // Xem lỗi Python tại đây
                throw new Error("Server không trả về JSON hợp lệ. Có thể lỗi logic bên trong View.");
            });
        }
        return res.json();
    })
    .then(data => {
        if (data.success) {
            const container = document.getElementById("report-container");
            if (container) {
                container.innerHTML = data.html;

                window.registerData = data.register_data;

                // format tiền...
                container.querySelectorAll(".money").forEach(el => {
                    let raw = (el.innerText || "").replace(/[^\d.-]/g, "");
                    if (!raw) return;
                    el.innerText = formatMoney(raw);
                });
            }
        } else {
            alert("Lỗi từ Server: " + (data.error || "Không xác định"));
        }
    })
    .catch(err => {
        console.error("ERROR:", err);
        alert(err.message);
    });
}


export function closeJournalForm() {
    const journalForm = document.getElementById("report-container");
    if (journalForm) {

         journalForm.innerHTML = "";
    }
};


// Đừng quên expose ra window
window.closeJournalForm = closeJournalForm;

