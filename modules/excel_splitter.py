from flask import request, send_file
import pandas as pd
import zipfile
from io import BytesIO
from .utils import copy_excel_template_and_insert_data

def split_excel():
    # 🧩 1️⃣ Kiểm tra file upload
    file = request.files.get('file')
    if not file:
        return "⚠️ Vui lòng chọn file Excel!", 400

    # 🧭 2️⃣ Lấy thông tin từ form
    start_row = int(request.form.get('start_row'))
    end_row = int(request.form.get('end_row'))
    template_end_row = int(request.form.get('template_end_row'))
    split_column_name_raw = request.form.get('column_name', '').strip()

    # Đọc file Excel từ bộ nhớ (không ghi ra ổ đĩa)
    file_bytes = file.read()
    original_file_stream = BytesIO(file_bytes)

    # Đọc dữ liệu trong phạm vi được chọn
    df_range = pd.read_excel(original_file_stream, header=None,
                             skiprows=start_row - 1, nrows=end_row - start_row + 1)
    original_file_stream.seek(0)

    # 🔍 3️⃣ Tìm dòng chứa tên cột cần chia
    header_idx = None
    for i, row in df_range.iterrows():
        if any(split_column_name_raw.lower() == str(cell).strip().lower() for cell in row):
            header_idx = i
            break

    if header_idx is None:
        return f"❌ Không tìm thấy '{split_column_name_raw}' trong file!", 400

    # Gán tên cột
    df_range.columns = df_range.iloc[header_idx].astype(str).str.strip()
    df_data = df_range.iloc[header_idx + 1:].copy().reset_index(drop=True)

    # 4️⃣ Kiểm tra cột cần chia
    split_col_final = next((c for c in df_data.columns if c.strip().lower() == split_column_name_raw.lower()), None)
    if not split_col_final:
        return f"❌ Không tìm thấy cột '{split_column_name_raw}'!", 400

    # Lọc các giá trị hợp lệ
    df_data = df_data[df_data[split_col_final].notna() & (df_data[split_col_final].astype(str).str.strip() != "")]

    # 📦 5️⃣ Tạo ZIP trong bộ nhớ (không ghi ra file thật)
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for val, group in df_data.groupby(split_col_final):
            name = str(val).strip().replace("/", "_").replace("\\", "_") or "khong_ten"

            # Sao chép template & chèn dữ liệu (trả về BytesIO)
            buf = copy_excel_template_and_insert_data(
                BytesIO(file_bytes), group.reset_index(drop=True),
                template_end_row, template_end_row + 1
            )

            # Ghi từng file Excel vào ZIP
            zipf.writestr(f"{name}.xlsx", buf.read())

    # 🔁 Quay lại đầu bộ nhớ
    zip_buffer.seek(0)

    # 🚀 6️⃣ Gửi file ZIP trực tiếp về trình duyệt (không lưu ở thư mục code)
    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name=f"tach_theo_{split_column_name_raw}.zip",
        mimetype='application/zip'
    )
