
export function formatMoney(val) {
    if (val === 0 || val === "0") return "0";
    if (!val) return "0";

    // Nếu val là string (ví dụ "540,000" từ Django), ta làm sạch nó
    let cleanVal = val;
    if (typeof val === "string") {
        // Loại bỏ tất cả ký tự không phải số, dấu chấm thập phân hoặc dấu trừ
        cleanVal = val.replace(/,/g, "");
    }

    const num = Number(cleanVal);

    if (isNaN(num)) return "0";

    return num.toLocaleString("vi-VN");
}


 export function cleanNumber(val) {
    if (val === undefined || val === null || val === "") return 0;

    // ✅ Nếu đã là number → giữ nguyên
    if (typeof val === 'number') return val;

    let str = val.toString().trim();
    if (!str) return 0;

    // ✅ Xử lý số âm dạng kế toán: (100) -> -100
    if (str.startsWith('(') && str.endsWith(')')) {
        str = '-' + str.slice(1, -1);
    }

    // ✅ Nếu KHÔNG có dấu phẩy → coi là format chuẩn (backend)
    if (!str.includes(',')) {
        const num = parseFloat(str);
        return isNaN(num) ? 0 : num;
    }

    // ✅ Có cả . và , → phân biệt US vs VN
    if (str.includes('.') && str.includes(',')) {
        // Nếu , đứng trước . → US: 1,234.56
        if (str.indexOf(',') < str.indexOf('.')) {
            str = str.replace(/,/g, '');
        }
        // Ngược lại → VN: 1.234,56
        else {
            str = str.replace(/\./g, '').replace(',', '.');
        }
    }
    // ✅ Chỉ có dấu phẩy
    else if (str.includes(',')) {
        const parts = str.split(',');
        if (parts[1] && parts[1].length <= 2) {
            // decimal
            str = str.replace(',', '.');
        } else {
            // thousands
            str = str.replace(/,/g, '');
        }
    }

    const num = parseFloat(str);
    return isNaN(num) ? 0 : num;
}


export function getCSRF() {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Kiểm tra tên cookie mặc định của Django là csrftoken
            if (cookie.substring(0, 10) === ('csrftoken' + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(10));
                break;
            }
        }
    }
    return cookieValue;
}


export function safeFormat(val) {
    const num = cleanNumber(val);
    return formatMoney(num);
}

export function exportExcel(registerData) {

    if (!registerData || !registerData.headers || !registerData.rows) {
        console.error("Invalid register data", registerData);
        return;
    }

    function doExport() {
        const { headers, rows, report_name } = registerData;

        // header label
        const headerRow = headers.map(h => h.label);

        // data theo key
        const dataRows = rows.map(row =>
            headers.map(h => row[h.key] ?? "")
        );

        const sheetData = [
            [report_name || "SỔ KẾ TOÁN"],
            [],
            headerRow,
            ...dataRows
        ];

        const ws = XLSX.utils.aoa_to_sheet(sheetData);

        ws["!cols"] = headers.map(h => ({
            wch: Math.max(h.label.length, 12)
        }));

        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, "Sheet1");

        XLSX.writeFile(wb, (report_name || "so_ke_toan") + ".xlsx");
    }

    if (typeof XLSX === "undefined") {
        const script = document.createElement("script");
        script.src = "https://cdn.jsdelivr.net/npm/xlsx/dist/xlsx.full.min.js";
        script.onload = doExport;
        document.body.appendChild(script);
    } else {
        doExport();
    }
}


// 3. Hàm Đóng form
export function closeJournalForm() {
    const container = document.getElementById("report-container");
    if (container) {
        container.innerHTML = ""; // Xóa trắng nội dung
        // Hoặc ẩn đi nếu bạn dùng modal/overlay
        // container.style.display = "none";
    }
}
