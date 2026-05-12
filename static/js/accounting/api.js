export function uploadInvoice(formData, type) {
    let url = type === "invoice_in"
        ? "/accounting/api/upload-invoice-in/"
        : "/accounting/api/upload-invoice-out/";

    return fetch(url, {
        method: "POST",
        body: formData
    }).then(res => res.json());
}


// ================= UPDATE =================
export function updateRow(id, field, value) {
    let row = document.getElementById(`row-${id}`);
    if (!row) return;

    row.classList.add("saving");

    fetch("/accounting/api/update-row/", {
        method: "POST",
        headers: {
            "X-CSRFToken": getCSRF(),
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: new URLSearchParams({
            id: id,
            field: field,
            value: value,
            invoice_type: window.APP_STATE.currentInvoiceType
        })
    })
    .then(res => res.json())
    .then(res => {
        row.classList.remove("saving");

        if (res.status === "ok") {

            // 🔥 update local data
              let r = window.APP_STATE.CURRENT_DATA.find(x => x.id == id);

            if (r) {
                r[field] = value;

                // 🔥 QUAN TRỌNG: chạy lại định khoản
                r.entries = generateEntries(r, window.APP_STATE.currentInvoiceType);
            }

            row.classList.add("saved");
            setTimeout(() => row.classList.remove("saved"), 800);

        } else {
            row.classList.add("table-danger");
            alert("Lưu thất bại");
        }
    })
    .catch(err => {
        row.classList.remove("saving");
        row.classList.add("table-danger");
        console.error("Update error:", err);
    });
}

// ================= UPLOAD PDF =================
export function uploadPDF(id, input) {
    if (!input.files.length) return;

    let row = document.getElementById(`row-${id}`);
    if (!row) return;

    row.classList.add("saving");

    let formData = new FormData();
    formData.append("id", id);
    formData.append("file", input.files[0]);

    fetch("/accounting/api/upload-pdf/", {
        method: "POST",
        headers: {
            "X-CSRFToken": getCSRF(),
        },
        body: formData
    })
    .then(res => res.json())
    .then(res => {
        row.classList.remove("saving");

        if (res.status === "ok") {
            row.classList.add("saved");
            setTimeout(() => row.classList.remove("saved"), 800);
        } else {
            row.classList.add("table-danger");
            alert("Upload PDF thất bại");
        }
    })
    .catch(err => {
        row.classList.remove("saving");
        row.classList.add("table-danger");
        console.error("Upload error:", err);
    });
}