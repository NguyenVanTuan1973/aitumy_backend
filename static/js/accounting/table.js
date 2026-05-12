import { groupData } from "./grouping.js";
import { cleanNumber, formatMoney, safeFormat } from "./utils.js";
import { initColumnSelector, toggleColumn, toggleColumnPanel } from "./columns.js";


/**
 * Hàm render bảng chính
 */
export function renderTable(data) {
    const tbody = document.getElementById("table-body");
    const tfoot = document.getElementById("table-footer");

    if (!tbody || !tfoot) return console.error("Missing table elements");

    // 1. Kiểm tra dữ liệu rỗng
    if (!data || data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="41" class="text-center">Không có dữ liệu</td></tr>`;
        tfoot.innerHTML = "";
        return;
    }

    // 2. Tính toán tổng số (Summary)
    const summary = data.reduce((acc, row) => {
        acc.discount += cleanNumber(row.discount);
        acc.amount += cleanNumber(row.amount);
        acc.tax += cleanNumber(row.tax);
        acc.discount_total += cleanNumber(row.discount_total);
        acc.fee_total += cleanNumber(row.fee_total);
        acc.payment_total += cleanNumber(row.payment_total);
        return acc;
    }, { discount: 0, amount: 0, tax: 0, discount_total: 0, fee_total: 0, payment_total: 0 });

    // 3. Xử lý Render Body theo chế độ Group hoặc List
    let bodyHtml = "";
    const isGroupMode = window.APP_STATE?.GROUP_MODE;

    if (!isGroupMode) {
        bodyHtml = data.map(row => renderRow(row)).join('');
    } else {
        const grouped = groupData(data);
        Object.entries(grouped).forEach(([buyer, invoices]) => {
            let buyerTotal = 0;
            let groupRowsHtml = "";

            Object.entries(invoices).forEach(([number, rows]) => {
                const invoiceTotal = rows.reduce((s, r) => s + cleanNumber(r.payment_total), 0);
                buyerTotal += invoiceTotal;

                // Header Hóa đơn
                groupRowsHtml += `
                    <tr class="table-primary group-invoice group-${buyer}" onclick="toggleInvoice('${buyer}', '${number}')" style="cursor:pointer">
                        <td colspan="41">▶ HĐ: <b>${number}</b> | Tổng: ${safeFormat(invoiceTotal)} (${rows.length} dòng)</td>
                    </tr>`;

                // Các dòng chi tiết
                groupRowsHtml += rows.map(row =>
                    renderRow(row).replace('<tr', `<tr class="group-${buyer} invoice-${number}"`)
                ).join('');
            });

            // Header Khách hàng
            bodyHtml += `
                <tr class="table-dark group-buyer" onclick="toggleBuyer('${buyer}')" style="cursor:pointer">
                    <td colspan="41">👤 ${buyer} | Tổng: <b>${safeFormat(buyerTotal)}</b></td>
                </tr>` + groupRowsHtml;
        });
    }

    // 4. Cập nhật DOM (Body & Footer)
    tbody.innerHTML = bodyHtml;

    // Đoạn mã thay thế cho mục 4 trong renderTable của bạn

    // Tổng số cột thực tế của table
    const totalColumns = 43;

    // Các cột tiền bắt đầu từ cột số 31
    const amountColumnIndex = 31;

    // Đã dùng 3 cột đầu
    const usedColumnsBeforeAmount = 3;

    // Số cột trống trước cột amount
    const emptyBeforeTotals =
        amountColumnIndex - usedColumnsBeforeAmount - 1;

    // Có 5 cột tổng tiền
    const totalValueColumns = 5;

    // Số cột còn lại phía sau
    const emptyAfterTotals =
        totalColumns
        - usedColumnsBeforeAmount
        - emptyBeforeTotals
        - totalValueColumns;

    tfoot.innerHTML = `
    <tr class="sticky-bottom-custom bg-light fw-bold">

        <td class="text-center">TỔNG</td>
        <td></td>
        <td>${data.length} dòng</td>

        ${'<td></td>'.repeat(emptyBeforeTotals)}

        <td class="total-number text-primary text-end">
            ${safeFormat(summary.amount)}
        </td>

        <td class="total-number text-primary text-end">
            ${safeFormat(summary.tax)}
        </td>

        <td class="total-number text-primary text-end">
            ${safeFormat(summary.discount_total)}
        </td>

        <td class="total-number text-primary text-end">
            ${safeFormat(summary.fee_total)}
        </td>

        <td class="total-number text-danger text-end">
            ${safeFormat(summary.payment_total)}
        </td>

        ${'<td></td>'.repeat(emptyAfterTotals)}

    </tr>
    `;

    // 5. Chạy các tiến trình phụ (Select columns, v.v.)
    setTimeout(() => {
        if (typeof initColumnSelector === "function") initColumnSelector();
    }, 100);
}

function renderRow(row) {
    return `
    <tr id="row-${row.id}">

        <td>${row.invoice_type === "invoice_in" ? "Mua" : "Bán"}</td>
        <td>${row.number || ""}</td>
        <td>${row.create_date || ""}</td>

        <td>${row.template || ""}</td>
        <td>${row.symbol || ""}</td>

        <td>${row.signing_date || ""}</td>
        <td>${row.mccqt || ""}</td>
        <td>${row.cqt_signing_date || ""}</td>

        <td>${row.currency || "VND"}</td>
        <td>${row.exchange || 1}</td>

        <td>${row.seller_name || ""}</td>
        <td>${row.seller_tax_code || ""}</td>
        <td>${row.seller_address || ""}</td>

        <td>${row.buyer_name || ""}</td>
        <td>${row.buyer_address || ""}</td>

        <td>${row.delivery_address || ""}</td>
        <td>${row.license_plate || ""}</td>
        <td>${row.customer_code || ""}</td>
        <td>${row.id_card || ""}</td>

        <td>
            <select class="form-select form-select-sm"
                onchange="updateRow(${row.id}, 'payment', this.value)">
                <option value="cash" ${row.payment=="cash"?"selected":""}>Tiền mặt</option>
                <option value="bank" ${row.payment=="bank"?"selected":""}>Ngân hàng</option>
                <option value="debt" ${!row.payment || row.payment=="debt"?"selected":""}>Công nợ</option>
            </select>
        </td>

        <td>${row.property || ""}</td>
        <td>${row.material_code || ""}</td>
        <td>${row.material_series || ""}</td>
        <td>${row.expiration_date || ""}</td>

        <td>${row.product_name || ""}</td>
        <td>${row.product_unit || ""}</td>
        <td>${row.quantity || 0}</td>
        <td>${formatMoney(row.unit_price)}</td>
        <td>${formatMoney(row.discount)}</td>
        <td>${row.tax_rate || 0}%</td>

        <td>${formatMoney(row.amount)}</td>
        <td>${formatMoney(row.tax)}</td>
        <td>${formatMoney(row.discount_total)}</td>
        <td>${formatMoney(row.fee_total)}</td>
        <td>${formatMoney(row.payment_total)}</td>

        <td>${row.invoice_status || ""}</td>
        <td>${row.associated_invoice_status || ""}</td>
        <td>${row.invoice_check_result || ""}</td>
        <td>${row.lookup_link || ""}</td>
        <td>${row.lookup_code || ""}</td>

        <td class="text-center">
            <input type="checkbox"
                ${row.posted ? "checked":""}
                onchange="updateRow(${row.id}, 'posted', this.checked)">
        </td>

        <td>
            <button class="btn btn-sm btn-success"
                onclick="showEntries('${row.id}')"> 📘 Xem
            </button>
        </td>

        <td>
            <input type="file"
                class="form-control form-control-sm"
                onchange="uploadPDF(${row.id}, this)">
        </td>
    </tr>
    `;
}


