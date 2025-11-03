import os
import pandas as pd
from datetime import datetime
from io import BytesIO
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
import base64

# Hàm phụ trợ mới: Extract cả Mã và Tên từ tên file
def extract_parts_from_filename(filename):
    """
    Extracts parts from filename
    Ví dụ: 'S12731-Công ty TNHH ABC.xlsx' -> ('S12731', 'Công ty TNHH ABC')
    Ví dụ: 'S12731.xlsx' -> ('S12731', None)
    """
    basename = os.path.splitext(filename)[0]
    if '-' in basename:
        # Tách ở dấu - đầu tiên
        parts = basename.split('-', 1) 
        code = parts[0].strip()
        name = parts[1].strip()
        
        # Xử lý trường hợp file là 'S123-.xlsx'
        if name == "":
            return code, None
            
        return code, name
    
    # Nếu không có dấu -
    return basename.strip(), None

def refresh_access_token_if_needed(credentials):
    """Làm mới access token nếu hết hạn"""
    if credentials.expired and credentials.refresh_token:
        print("⚠️ Access token expired - Refreshing...")
        credentials.refresh(Request())
        print("✅ Access token refreshed")
    return credentials

def create_message(sender, to, subject, body, file_bytes=None, filename=None, cc=None):
    """
    Tạo email message (MIME format)
    """
    message = MIMEMultipart()
    message['From'] = sender
    message['To'] = to
    message['Subject'] = subject
    
    if cc:
        message['Cc'] = cc
    
    # Thêm nội dung email
    message.attach(MIMEText(body, 'plain', 'utf-8'))
    
    # Xử lý attachment từ BytesIO
    if file_bytes is not None and filename:
        part = MIMEBase('application', "octet-stream")
        part.set_payload(file_bytes.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment', filename=filename)
        message.attach(part)

    # Chuyển message thành format base64 cho Gmail API
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw}

def send_email_oauth(service, sender, to, subject, body, attachment_path=None, cc=None):
    """Gửi email qua Gmail API"""
    try:
        # ✅ FIX: Đọc file ở chế độ binary (rb) và dùng BytesIO để đính kèm
        file_bytes = None
        file_name = None
        
        if attachment_path:
            file_name = os.path.basename(attachment_path)
            with open(attachment_path, 'rb') as f:
                file_bytes = BytesIO(f.read())

        message = create_message(
            sender, to, subject, body, 
            file_bytes=file_bytes, 
            filename=file_name, 
            cc=cc
        )
        
        service.users().messages().send(userId='me', body=message).execute()
        return True, ""
    except HttpError as error:
        error_message = f'An error occurred: {error}'
        return False, error_message
    except Exception as e:
        return False, str(e)


def send_emails_oauth(
    credentials,
    sender_email,
    sender_name,
    excel_folder,
    email_file_path,
    ref_col,
    name_col=None,
    email_col=None,
    cc_col=None,
    selected_col_for_match=None,
    subject_template="",
    body_template="",
    start_row=2,
    end_row=99999,
    progress_callback=None,
    is_zip=None
):
    """Gửi hàng loạt email"""
    
    credentials = refresh_access_token_if_needed(credentials)
    
    print("📧 Building Gmail service...")
    service = build('gmail', 'v1', credentials=credentials)
    
    # Đọc danh sách email
    df_email = pd.read_excel(email_file_path)
    # Lọc theo dòng bắt đầu/kết thúc do người dùng nhập (start_row là index 1)
    df_email = df_email.iloc[start_row-1:end_row] 
    
    # ✅ FIX KeyError: Kiểm tra cột Mã ID chính
    print(f"🔍 Checking email list columns... (Ref: '{ref_col}', Name: '{name_col}')")

    if ref_col not in df_email.columns:
        print(f"❌ LỖI NGHIÊM TRỌNG: Cột Mã ID chính '{ref_col}' KHÔNG TÌM THẤY trong file email.")
        raise KeyError(f"Cột Mã ID chính '{ref_col}' không tìm thấy trong file email. Vui lòng kiểm tra lại file Excel và tên cột bạn nhập.")

    # Kiểm tra cột Tên (nếu được nhập)
    if name_col and name_col not in df_email.columns:
        print(f"❌ LỖI NGHIÊM TRỌNG: Cột Tên '{name_col}' KHÔNG TÌM THẤY trong file email.")
        raise KeyError(f"Cột Tên '{name_col}' (dùng để đối chiếu) không tìm thấy trong file email. Vui lòng kiểm tra lại.")
        
    print("✅ Email list columns verified.")
    
    logs = []
    
    # Lấy danh sách file trong thư mục
    files = [f for f in os.listdir(excel_folder) if f.endswith('.xlsx')]
    total_files = len(files)
    
    if total_files == 0:
        print("⚠️ Không tìm thấy file Excel nào để gửi.")
        logs.append({
            "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Code": "",
            "Name": "",
            "Email To": "",
            "Email CC": "",
            "Status": "Failed",
            "Error": "Không tìm thấy file Excel nào để gửi."
        })
        # Ghi log vào BytesIO
        df_log = pd.DataFrame([logs[0]])
        output = BytesIO()
        df_log.to_csv(output, index=False, encoding="utf-8-sig")
        output.seek(0)
        return output

    print(f"🔍 Found {total_files} files to send")
    
    for current, file in enumerate(files, 1):
        npp_code = ""
        ten_npp = ""
        email_to = ""
        email_cc = ""
        
        try:
            # ✅ BƯỚC 1: Extract CẢ HAI PHẦN từ filename
            npp_code, npp_name_from_file = extract_parts_from_filename(file)

            if not npp_code:
                logs.append({
                    "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Code": "",
                    "Name": file,
                    "Email To": "",
                    "Email CC": "",
                    "Status": "Failed",
                    "Error": f"Không thể trích xuất Mã ID từ tên file '{file}'"
                })
                print(f"❌ [{current}/{total_files}] Failed: Không thể trích xuất Mã ID từ tên file '{file}'")
                continue
            
            # ✅ BƯỚC 2: TÌM DỮ LIỆU KHỚP (ĐỐI CHIẾU 2 CỘT)
            
            # Điều kiện 1: Mã ID phải khớp (luôn luôn)
            # Thêm .str.strip() để xóa khoảng trắng thừa cho Mã ID
            match_id = (df_email[ref_col].astype(str).str.strip() == str(npp_code))
            
            matched = df_email[match_id]
            
            # Nếu người dùng có nhập "Cột Tên" VÀ tên file cũng có tên
            if name_col and npp_name_from_file is not None:
                # Phải khớp CẢ TÊN
                print(f"  > [{current}/{total_files}] Matching ID '{npp_code}' AND Name '{npp_name_from_file}'...")
                # Thêm .str.strip() cho Tên
                match_name = (df_email[name_col].astype(str).str.strip() == str(npp_name_from_file).strip())
                
                # Kết hợp cả 2 điều kiện
                matched = df_email[match_id & match_name]
            else:
                print(f"  > [{current}/{total_files}] Matching ID '{npp_code}' only...")

            if matched.empty:
                ten_npp = npp_name_from_file if npp_name_from_file else "N/A"
                logs.append({
                    "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Code": npp_code,
                    "Name": ten_npp,
                    "Email To": "N/A",
                    "Email CC": "N/A",
                    "Status": "Skipped",
                    "Error": f"Không tìm thấy email khớp với Mã ID: {npp_code}"
                })
                print(f"⚠️ [{current}/{total_files}] Skipped: No match found for {npp_code} ({npp_name_from_file})")
                continue
            
            if len(matched) > 1:
                ten_npp = npp_name_from_file if npp_name_from_file else "N/A"
                logs.append({
                    "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Code": npp_code,
                    "Name": ten_npp,
                    "Email To": "N/A",
                    "Email CC": "N/A",
                    "Status": "Skipped",
                    "Error": f"Tìm thấy nhiều hơn 1 email khớp với Mã ID: {npp_code}"
                })
                print(f"⚠️ [{current}/{total_files}] Skipped: Multiple matches found for {npp_code}")
                continue
            
            # Lấy thông tin email
            row = matched.iloc[0]
            email_to = row[email_col] if email_col in row and pd.notna(row[email_col]) else ""
            email_cc = row[cc_col] if cc_col and cc_col in row and pd.notna(row[cc_col]) else ""
            ten_npp = row[name_col] if name_col and name_col in row and pd.notna(row[name_col]) else "Bạn"
            
            if not email_to or str(email_to).strip() == "":
                logs.append({
                    "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Code": npp_code,
                    "Name": ten_npp,
                    "Email To": "N/A",
                    "Email CC": email_cc if email_cc else "",
                    "Status": "Skipped",
                    "Error": "Địa chỉ email người nhận (TO) trống."
                })
                print(f"⚠️ [{current}/{total_files}] Skipped: TO email is empty for {npp_code}")
                continue
            
            # Cập nhật tiến độ
            if progress_callback:
                progress_callback(current, total_files)
                
            # Chuẩn bị và gửi email
            subject = subject_template.replace("{ma_npp}", npp_code).replace("{ten_npp}", str(ten_npp))
            body = body_template.replace("{ma_npp}", npp_code).replace("{ten_npp}", str(ten_npp))
            
            attachment_path = os.path.join(excel_folder, file)
            
            success, error = send_email_oauth(
                service,
                f"{sender_name} <{sender_email}>",
                email_to,
                subject,
                body,
                attachment_path,
                email_cc if email_cc and pd.notna(email_cc) and str(email_cc).strip() != "" else None
            )
            
            if success:
                logs.append({
                    "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Code": npp_code,
                    "Name": ten_npp,
                    "Email To": email_to,
                    "Email CC": email_cc if email_cc else "",
                    "Status": "Success",
                    "Error": ""
                })
                print(f"✅ [{current}/{total_files}] Sent to {email_to} ({npp_code} - {ten_npp})")
            else:
                logs.append({
                    "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Code": npp_code,
                    "Name": ten_npp,
                    "Email To": email_to,
                    "Email CC": email_cc if email_cc else "",
                    "Status": "Failed",
                    "Error": error
                })
                print(f"❌ [{current}/{total_files}] Error sending to {email_to} ({npp_code}): {error}")
        
        except FileNotFoundError:
            logs.append({
                "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Code": npp_code,
                "Name": ten_npp,
                "Email To": email_to,
                "Email CC": email_cc,
                "Status": "Failed",
                "Error": f"File not found: {file}"
            })
            print(f"❌ [{current}/{total_files}] File not found: {npp_code}")
        except Exception as e:
            logs.append({
                "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Code": npp_code,
                "Name": ten_npp,
                "Email To": email_to,
                "Email CC": email_cc,
                "Status": "Failed",
                "Error": str(e)
            })
            print(f"❌ [{current}/{total_files}] Critical Error: {str(e)}")

    # ✅ FIX: Ghi log vào BytesIO buffer
    df_log = pd.DataFrame(logs)
    
    output = BytesIO()
    df_log.to_csv(output, index=False, encoding="utf-8-sig")
    output.seek(0)  # ✅ QUAN TRỌNG: reset pointer về đầu
    
    print("✅ Email sending completed.\n")
    return output  # ✅ FIX: Trả về BytesIO, không phải tuple