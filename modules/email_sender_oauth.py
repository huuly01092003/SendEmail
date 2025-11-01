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

def build_gmail_service(credentials):
    """Xây dựng Gmail service từ credentials"""
    return build('gmail', 'v1', credentials=credentials)

def refresh_access_token_if_needed(credentials):
    """Làm mới access token nếu hết hạn"""
    if credentials.expired and credentials.refresh_token:
        print("⚠️ Access token expired - Refreshing...")
        credentials.refresh(Request())
        print("✅ Access token refreshed")
    return credentials

def create_message(sender, to, subject, body, file_path=None, cc=None):
    """Tạo email message (MIME format)"""
    message = MIMEMultipart()
    message['From'] = sender
    message['To'] = to
    message['Subject'] = subject
    
    if cc:
        message['Cc'] = cc
    
    # Thêm nội dung email
    message.attach(MIMEText(body, 'plain', 'utf-8'))
    
    # Thêm attachment nếu có
    if file_path and os.path.exists(file_path):
        with open(file_path, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
        
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(file_path)}')
        message.attach(part)
    
    # Mã hóa message thành base64
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw_message}

def send_email_oauth(service, sender, to, subject, body, file_path=None, cc=None):
    """Gửi email qua Gmail API (OAuth)"""
    try:
        message = create_message(sender, to, subject, body, file_path, cc)
        send_message = service.users().messages().send(userId='me', body=message)
        result = send_message.execute()
        return True, None
    except HttpError as error:
        return False, str(error)

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
    progress_callback=None
):
    """Gửi email qua Gmail OAuth 2.0 (Multiuser)"""
    
    # ✅ Làm mới token nếu cần
    credentials = refresh_access_token_if_needed(credentials)
    
    print("📧 Building Gmail service...")
    service = build_gmail_service(credentials)
    
    df_email = pd.read_excel(email_file_path)
    df_email = df_email.iloc[start_row-1:end_row]
    
    logs = []
    files = [f for f in os.listdir(excel_folder) if f.endswith(".xlsx")]
    total_files = len(files)
    print(f"🔍 Found {total_files} files to send\n")
    
    current = 0
    for file in files:
        current += 1
        
        if progress_callback:
            progress_callback(current, total_files)
        
        npp_code = os.path.splitext(file)[0]
        matched = df_email[df_email[selected_col_for_match].astype(str) == str(npp_code)]
        
        if matched.empty:
            logs.append([
                datetime.now(), npp_code, "", "", "", "Skipped",
                "NPP code not found in email list"
            ])
            continue
        
        email_to = matched[email_col].values[0] if email_col in matched.columns else None
        email_cc = matched[cc_col].values[0] if cc_col and cc_col in matched.columns else None
        ten_npp = matched[name_col].values[0] if name_col and name_col in matched.columns else ""
        
        if not pd.notna(email_to) or str(email_to).strip() == "":
            logs.append([
                datetime.now(), npp_code, ten_npp, "", "", "Skipped",
                "No email to send"
            ])
            continue
        
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
            logs.append([
                datetime.now(), npp_code, ten_npp, email_to, email_cc,
                "Success", ""
            ])
            print(f"✅ [{current}/{total_files}] Sent to {email_to} ({npp_code} - {ten_npp})")
        else:
            logs.append([
                datetime.now(), npp_code, ten_npp, email_to, email_cc,
                "Failed", error
            ])
            print(f"❌ [{current}/{total_files}] Error sending to {email_to} ({npp_code}): {error}")
    
    # Ghi log
    df_log = pd.DataFrame(logs, columns=[
        "Time", "Code", "Name", "To Email", "CC Email", "Status", "Error"
    ])
    output = BytesIO()
    df_log.to_csv(output, index=False, encoding="utf-8-sig")
    output.seek(0)
    
    print("✅ Email sending completed.\n")
    return output