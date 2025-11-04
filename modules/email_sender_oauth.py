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
from collections import defaultdict # Import thêm

# Hàm phụ trợ mới: Extract cả Mã và Tên từ tên file
def extract_parts_from_filename(filename):
    """
    Extracts parts from filename
    Ví dụ: 'S12731-Công ty TNHH ABC.xlsx' -> ('S12731', 'Công ty TNHH ABC')
    Ví dụ: 'S12731-Công ty TNHH ABC-XXX.xlsx' -> ('S12731', 'Công ty TNHH ABC-XXX')
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

def create_message(sender, to, subject, body, attachments=None, cc=None):
    """
    Tạo email message (MIME format)
    ✅ SỬA ĐỔI: Chấp nhận một danh sách attachments
    attachments là một list các tuple: [(filename, file_bytes_io), ...]
    """
    message = MIMEMultipart()
    message['From'] = sender
    message['To'] = to
    message['Subject'] = subject
    
    if cc:
        message['Cc'] = cc
    
    # Thêm nội dung email
    message.attach(MIMEText(body, 'plain', 'utf-8'))
    
    # Xử lý attachments
    if attachments:
        for filename, file_bytes in attachments:
            part = MIMEBase('application', "octet-stream")
            # QUAN TRỌNG: reset con trỏ của BytesIO trước khi đọc
            file_bytes.seek(0) 
            part.set_payload(file_bytes.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment', filename=filename)
            message.attach(part)

    # Chuyển message thành format base64 cho Gmail API
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw}

def send_email_oauth(service, sender, to, subject, body, attachment_paths=None, cc=None):
    """
    Gửi email qua Gmail API
    ✅ SỬA ĐỔI: Chấp nhận một danh sách các đường dẫn file (attachment_paths)
    """
    try:
        attachments = []
        if attachment_paths:
            for path in attachment_paths:
                file_name = os.path.basename(path)
                with open(path, 'rb') as f:
                    file_bytes = BytesIO(f.read())
                attachments.append((file_name, file_bytes))
        
        message = create_message(
            sender, to, subject, body, 
            attachments=attachments, # Gửi list attachments
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
    selected_col_for_match=None, # Không dùng nữa, nhưng giữ lại cho tương thích
    subject_template="",
    body_template="",
    start_row=2,
    end_row=99999,
    progress_callback=None,
    is_zip=None
):
    """
    Gửi hàng loạt email
    ✅ LOGIC ĐƯỢC VIẾT LẠI HOÀN TOÀN:
    1. Quét và NHÓM file theo Mã ID.
    2. Lặp qua TỪNG NHÓM ID (thay vì từng file).
    3. Gửi 1 email duy nhất với NHIỀU file đính kèm cho mỗi ID.
    """
    
    credentials = refresh_access_token_if_needed(credentials)
    
    print("📧 Building Gmail service...")
    service = build('gmail', 'v1', credentials=credentials)
    
    # Đọc danh sách email
    df_email = pd.read_excel(email_file_path)
    df_email = df_email.iloc[start_row-1:end_row] 
    
    # Kiểm tra các cột
    print(f"🔍 Checking email list columns... (Ref: '{ref_col}', Name: '{name_col}')")
    if ref_col not in df_email.columns:
        raise KeyError(f"Cột Mã ID chính '{ref_col}' không tìm thấy trong file email.")
    if name_col and name_col not in df_email.columns:
        print(f"⚠️ Cảnh báo: Cột Tên '{name_col}' không tìm thấy. Tên sẽ được lấy từ tên file (nếu có).")
    if email_col not in df_email.columns:
        raise KeyError(f"Cột Email '{email_col}' không tìm thấy trong file email.")
        
    print("✅ Email list columns verified.")
    
    logs = []
    
    # ✅ BƯỚC 1: QUÉT VÀ NHÓM FILE THEO MÃ ID
    print("🔍 Scanning and grouping files by ID...")
    files_map = defaultdict(list) # Key: npp_code, Value: [full_path, full_path, ...]
    all_files_in_folder = [f for f in os.listdir(excel_folder) if f.endswith('.xlsx')]
    
    if not all_files_in_folder:
        print("⚠️ Không tìm thấy file Excel nào để gửi.")
        logs.append({
            "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Code": "", "Name": "",
            "Email To": "", "Email CC": "", "Status": "Failed",
            "Error": "Không tìm thấy file Excel nào để gửi."
        })
        df_log = pd.DataFrame([logs[0]])
        output = BytesIO()
        df_log.to_csv(output, index=False, encoding="utf-8-sig")
        output.seek(0)
        return output

    for file in all_files_in_folder:
        try:
            # Chỉ cần extract code. Tên file đầy đủ sẽ được đính kèm.
            npp_code, _ = extract_parts_from_filename(file) 
            
            if not npp_code:
                logs.append({
                    "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Code": "", "Name": file,
                    "Email To": "", "Email CC": "", "Status": "Failed",
                    "Error": f"Không thể trích xuất Mã ID từ tên file '{file}'"
                })
                print(f"❌ Failed: Không thể trích xuất Mã ID từ tên file '{file}'")
                continue
                
            full_path = os.path.join(excel_folder, file)
            files_map[npp_code].append(full_path)
            
        except Exception as e:
            logs.append({
                "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Code": "", "Name": file,
                "Email To": "", "Email CC": "", "Status": "Failed",
                "Error": f"Lỗi xử lý file '{file}': {e}"
            })

    print(f"✅ Found {len(all_files_in_folder)} files, grouped into {len(files_map)} unique IDs (jobs).")

    # ✅ BƯỚC 2: LẶP QUA CÁC NHÓM ID, TÌM EMAIL VÀ GỬI
    total_jobs = len(files_map)
    
    for current, (npp_code, attachment_paths) in enumerate(files_map.items(), 1):
        email_to = ""
        email_cc = ""
        ten_npp = "Bạn" # Default
        
        try:
            # Cập nhật tiến độ theo "job" (mỗi job là 1 ID, 1 email)
            if progress_callback:
                progress_callback(current, total_jobs)

            # BƯỚC 2A: TÌM DỮ LIỆU KHỚP (CHỈ ĐỐI CHIẾU MÃ ID)
            print(f"  > [{current}/{total_jobs}] Processing ID: {npp_code} ({len(attachment_paths)} files)")
            
            match_id = (df_email[ref_col].astype(str).str.strip() == str(npp_code))
            matched = df_email[match_id]

            if matched.empty:
                logs.append({
                    "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Code": npp_code,
                    "Name": "N/A (No match)",
                    "Email To": "N/A", "Email CC": "N/A", "Status": "Skipped",
                    "Error": f"Không tìm thấy email khớp với Mã ID: {npp_code}"
                })
                print(f"⚠️ [{current}/{total_jobs}] Skipped: No match found for {npp_code}")
                continue
            
            if len(matched) > 1:
                logs.append({
                    "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Code": npp_code,
                    "Name": "N/A (Multiple matches)",
                    "Email To": "N/A", "Email CC": "N/A", "Status": "Skipped",
                    "Error": f"Tìm thấy nhiều hơn 1 email khớp với Mã ID: {npp_code}"
                })
                print(f"⚠️ [{current}/{total_jobs}] Skipped: Multiple matches found for {npp_code}")
                continue
            
            # BƯỚC 2B: Lấy thông tin email (đã tìm thấy 1 match)
            row = matched.iloc[0]
            email_to = row[email_col] if email_col in row and pd.notna(row[email_col]) else ""
            email_cc = row[cc_col] if cc_col and cc_col in row and pd.notna(row[cc_col]) else ""
            
            # Ưu tiên lấy tên từ file email (chuyên nghiệp), nếu không có thì fallback là "Bạn"
            if name_col and name_col in row and pd.notna(row[name_col]):
                ten_npp = row[name_col]
            
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
                print(f"⚠️ [{current}/{total_jobs}] Skipped: TO email is empty for {npp_code}")
                continue
            
            # BƯỚC 2C: Chuẩn bị và gửi email
            subject = subject_template.replace("{ma_npp}", npp_code).replace("{ten_npp}", str(ten_npp))
            body = body_template.replace("{ma_npp}", npp_code).replace("{ten_npp}", str(ten_npp))
            
            # GỬI EMAIL VỚI NHIỀU FILE
            success, error = send_email_oauth(
                service,
                f"{sender_name} <{sender_email}>",
                email_to,
                subject,
                body,
                attachment_paths, # Gửi list paths
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
                    "Error": f"Sent {len(attachment_paths)} files."
                })
                print(f"✅ [{current}/{total_jobs}] Sent to {email_to} ({npp_code} - {ten_npp}) with {len(attachment_paths)} files.")
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
                print(f"❌ [{current}/{total_jobs}] Error sending to {email_to} ({npp_code}): {error}")

        except Exception as e:
            # Log lỗi nghiêm trọng
            logs.append({
                "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Code": npp_code,
                "Name": ten_npp,
                "Email To": email_to,
                "Email CC": email_cc,
                "Status": "Failed",
                "Error": str(e)
            })
            print(f"❌ [{current}/{total_jobs}] Critical Error for ID {npp_code}: {str(e)}")

    # Ghi log vào BytesIO buffer
    df_log = pd.DataFrame(logs)
    
    output = BytesIO()
    df_log.to_csv(output, index=False, encoding="utf-8-sig")
    output.seek(0)
    
    print("✅ Email sending completed.\n")
    return output