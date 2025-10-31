import openpyxl
from io import BytesIO

def copy_excel_template_and_insert_data(original_file_stream, group_df, template_end_row, data_start_row):
    original_file_stream.seek(0)
    workbook = openpyxl.load_workbook(original_file_stream)
    ws_original = workbook.active

    wb_new = openpyxl.Workbook()
    ws_new = wb_new.active

    # Copy cấu trúc cột
    for col_dim in ws_original.column_dimensions:
        ws_new.column_dimensions[col_dim] = ws_original.column_dimensions[col_dim]

    # Copy template
    for row_idx in range(1, template_end_row + 1):
        for col_idx in range(1, ws_original.max_column + 1):
            cell_o = ws_original.cell(row=row_idx, column=col_idx)
            cell_n = ws_new.cell(row=row_idx, column=col_idx, value=cell_o.value)
            if cell_o.has_style:
                cell_n.font = cell_o.font.copy()
                cell_n.border = cell_o.border.copy()
                cell_n.fill = cell_o.fill.copy()
                cell_n.number_format = cell_o.number_format
                cell_n.protection = cell_o.protection.copy()
                cell_n.alignment = cell_o.alignment.copy()

    # Ghi dữ liệu
    for r_idx, row in group_df.iterrows():
        excel_row_index = data_start_row + r_idx
        for c_idx, value in enumerate(row):
            ws_new.cell(row=excel_row_index, column=c_idx + 1, value=value)

    buffer = BytesIO()
    wb_new.save(buffer)
    buffer.seek(0)
    return buffer
