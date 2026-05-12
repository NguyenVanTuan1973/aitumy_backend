import re
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from django.utils.formats import number_format

def force_clean_amount(value):
    if value is None:
        return Decimal('0')

    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))

    s = str(value).strip().replace(' ', '')
    if not s:
        return Decimal('0')

    # 👉 Case 1: có cả . và ,
    if ',' in s and '.' in s:
        # Nếu dấu , đứng trước dấu . => format US
        if s.find(',') < s.find('.'):
            # 500,004.00
            s = s.replace(',', '')
        else:
            # 41.827.204,32
            s = s.replace('.', '').replace(',', '.')

    # 👉 Case 2: chỉ có ,
    elif ',' in s:
        parts = s.split(',')
        if len(parts[-1]) <= 2:
            # decimal
            s = s.replace(',', '.')
        else:
            # thousands
            s = s.replace(',', '')

    # 👉 Case 3: chỉ có .
    elif '.' in s:
        parts = s.split('.')
        if len(parts[-1]) > 2:
            # thousands
            s = s.replace('.', '')

    # 👉 clean cuối
    s = re.sub(r'[^0-9.]', '', s)

    try:
        return Decimal(s)
    except:
        return Decimal('0')


def build_so_cai(root_data):
    # Khởi tạo lưu trữ thô để tránh cộng dồn sai vào biến tạm
    storage = defaultdict(lambda: {
        m: {'d': Decimal('0'), 'c': Decimal('0'), 'corr': set()}
        for m in range(1, 13)
    })

    active_accounts = set()

    for row in root_data:

        print("----- ROW -----")
        print("RAW AMOUNT:", row.get("amount"), "| TYPE:", type(row.get("amount")))

        amount = force_clean_amount(row.get("amount", 0))

        print("CLEAN AMOUNT:", amount)

        if amount > 1_000_000_000:
            print("🚨 BIG NUMBER DETECTED:", row.get("amount"), "=>", amount)

        # 1. Ép kiểu số tiền bằng hàm siêu tẩy rửa
        amount = force_clean_amount(row.get("amount", 0))
        if amount == 0: continue

        # 2. Xử lý tháng
        date_val = row.get("date")
        try:
            d_str = str(date_val)
            if "/" in d_str:
                month = int(d_str.split("/")[1])
            elif "-" in d_str:
                month = int(d_str.split("-")[1])
            else:
                month = int(d_str[5:7])
        except:
            continue

        if not (1 <= month <= 12): continue

        d_acc = str(row.get("debit_account") or "").strip()
        c_acc = str(row.get("credit_account") or "").strip()
        if not d_acc or not c_acc: continue

        # 3. Ghi vào storage
        storage[d_acc][month]['d'] += amount
        storage[d_acc][month]['corr'].add(c_acc)

        storage[c_acc][month]['c'] += amount
        storage[c_acc][month]['corr'].add(d_acc)

        active_accounts.add(d_acc)
        active_accounts.add(c_acc)

    # 4. Tính toán số dư
    results = []
    for acc_code in sorted(list(active_accounts)):
        running_balance = Decimal('0')
        months_output = []

        for m_idx in range(1, 13):
            m_data = storage[acc_code][m_idx]

            # Lưu số dư đầu kỳ
            op_d = running_balance if running_balance > 0 else Decimal('0')
            op_c = abs(running_balance) if running_balance < 0 else Decimal('0')

            # Cập nhật số dư cuối kỳ
            running_balance = running_balance + m_data['d'] - m_data['c']

            months_output.append({
                "month": m_idx,
                "opening_debit": op_d,
                "opening_credit": op_c,
                "debit": m_data['d'],
                "credit": m_data['c'],
                "closing_debit": running_balance if running_balance > 0 else Decimal('0'),
                "closing_credit": abs(running_balance) if running_balance < 0 else Decimal('0'),
                "corresponding_accounts": ", ".join(sorted(list(m_data['corr'])))
            })

        results.append({
            "account_name": "Tên tài khoản",
            "code": acc_code,
            "months": months_output,
            "sum_debit": sum(storage[acc_code][m]['d'] for m in range(1, 13)),
            "sum_credit": sum(storage[acc_code][m]['c'] for m in range(1, 13))
        })

    return results



