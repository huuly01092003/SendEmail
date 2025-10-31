import os
import smtplib
import pandas as pd
from datetime import datetime
from io import BytesIO
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import ssl

def send_emails(
    gmail_user,
    gmail_password,
    sender_name,
    excel_folder,
    email_file_path,
    ma_npp_col,
    ten_npp_col=None,
    email_npp_col=None,
    email_cc_col=None,
    selected_col_for_match=None,
    subject_template="",
    body_template="",
    start_row=2,
    end_row=99999,
    progress_callback=None
):
    """
    Gửi email qua Gmail SMTP kèm file Excel cho từng NPP.
    Tối ưu cho Railway/Fly.io (không bị chặn SMTP).
    """

    df_email = pd.read_excel(email_file_path)
    df_email = df_email.iloc[start_row-1:end_row]

    logs = []
    files = [f for f in os.listdir(excel_folder) if f.endswith(".xlsx")]
    total_files = len(files)
    print(f"🔍 Tìm thấy {total_files} file để gửi mail...\n")

    # ✅ Tạo SSL context an toàn
    context = ssl.create_default_context()

    # ✅ MỞ KẾT NỐI SMTP 1 LẦN và giữ kết nối
    try:
        # Thử port 587 trước (TLS)
        print("📧 Đang kết nối Gmail SMTP (port 587)...")
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=60)
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(gmail_user, gmail_password)
        print("✅ Đã kết nối Gmail SMTP thành công\n")
    except Exception as e:
        print(f"❌ Lỗi port 587: {str(e)}")
        # Thử port 465 (SSL) nếu 587 fail
        try:
            print("📧 Thử kết nối qua port 465 (SSL)...")
            server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60, context=context)
            server.login(gmail_user, gmail_password)
            print("✅ Đã kết nối Gmail SMTP (SSL) thành công\n")
        except Exception as e2:
            print(f"❌ Lỗi kết nối Gmail SMTP: {str(e2)}")
            # Trả về log rỗng nếu không kết nối được
            df_log = pd.DataFrame(logs, columns=[
                "Thời gian", "Mã NPP", "Tên NPP", "Email chính", "Email CC", "Trạng thái", "Lỗi"
            ])
            output = BytesIO()
            df_log.to_csv(output, index=False, encoding="utf-8-sig")
            output.seek(0)
            return output

    current = 0
    for file in files:
        current += 1
        
        # Update progress
        if progress_callback:
            progress_callback(current, total_files)
        
        npp_code = os.path.splitext(file)[0]
        matched = df_email[df_email[selected_col_for_match].astype(str) == str(npp_code)]

        if matched.empty:
            logs.append([datetime.now(), npp_code, "", "", "", "Bỏ qua", "Không tìm thấy mã NPP trong danh sách email"])
            continue

        email_to = matched[email_npp_col].values[0] if email_npp_col in matched.columns else None
        email_cc = matched[email_cc_col].values[0] if email_cc_col and email_cc_col in matched.columns else None
        ten_npp = matched[ten_npp_col].values[0] if ten_npp_col and ten_npp_col in matched.columns else ""

        if not pd.notna(email_to) or str(email_to).strip() == "":
            logs.append([datetime.now(), npp_code, ten_npp, "", "", "Bỏ qua", "Không có email để gửi"])
            continue

        msg = MIMEMultipart()
        msg["From"] = f"{sender_name} <{gmail_user}>"
        msg["To"] = email_to
        if email_cc and pd.notna(email_cc) and str(email_cc).strip() != "":
            msg["Cc"] = email_cc

        subject = subject_template.replace("{ma_npp}", npp_code).replace("{ten_npp}", str(ten_npp))
        body = body_template.replace("{ma_npp}", npp_code).replace("{ten_npp}", str(ten_npp))
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        attachment_path = os.path.join(excel_folder, file)
        with open(attachment_path, "rb") as f:
            part = MIMEApplication(f.read(), Name=file)
        part["Content-Disposition"] = f'attachment; filename="{file}"'
        msg.attach(part)

        try:
            # Sử dụng kết nối đã mở
            server.send_message(msg)
            logs.append([datetime.now(), npp_code, ten_npp, email_to, email_cc, "Thành công", ""])
            print(f"✅ [{current}/{total_files}] Gửi thành công cho {email_to} ({npp_code} - {ten_npp})")

        except Exception as e:
            err = str(e)
            logs.append([datetime.now(), npp_code, ten_npp, email_to, email_cc, "Thất bại", err])
            print(f"❌ [{current}/{total_files}] Lỗi gửi {email_to} ({npp_code}): {err}")

    # ✅ ĐÓNG KẾT NỐI SAU KHI GỬI XONG TẤT CẢ
    try:
        server.quit()
        print("\n✅ Đã đóng kết nối SMTP")
    except:
        pass

    # Ghi log ra bộ nhớ RAM
    df_log = pd.DataFrame(logs, columns=[
        "Thời gian", "Mã NPP", "Tên NPP", "Email chính", "Email CC", "Trạng thái", "Lỗi"
    ])
    output = BytesIO()
    df_log.to_csv(output, index=False, encoding="utf-8-sig")
    output.seek(0)

    print("✅ Hoàn tất quá trình gửi mail.\n")

    return output