from flask import Flask, render_template, request, send_file
from modules.email_sender import send_emails
import os, tempfile, zipfile
from datetime import datetime


app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send_emails', methods=['POST'])
def send_emails_route():
    gmail_user = request.form['gmail_user']
    gmail_password = request.form['gmail_password']
    sender_name = request.form['sender_name']

    ref_col = request.form['ref_col']
    name_col = request.form.get('name_col')
    email_col = request.form['email_col']
    cc_col = request.form.get('cc_col')
    subject = request.form['subject']
    body = request.form['body']

    start_row_email = int(request.form.get('start_row_email', 2))
    end_row_email = int(request.form.get('end_row_email', 99999))

    split_zip = request.files['split_zip']
    email_file = request.files['email_file']

    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "split.zip")
    excel_email_path = os.path.join(temp_dir, "emails.xlsx")

    split_zip.save(zip_path)
    email_file.save(excel_email_path)

    extract_folder = os.path.join(temp_dir, "excel_files")
    os.makedirs(extract_folder, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_folder)

    # 📨 Gửi mail + lấy file CSV log trong bộ nhớ
    log_buffer = send_emails(
        gmail_user=gmail_user,
        gmail_password=gmail_password,
        sender_name=sender_name,
        excel_folder=extract_folder,
        email_file_path=excel_email_path,
        ma_npp_col=ref_col,
        ten_npp_col=name_col,
        email_npp_col=email_col,
        email_cc_col=cc_col,
        selected_col_for_match=ref_col,
        subject_template=subject,
        body_template=body,
        start_row=start_row_email,
        end_row=end_row_email
    )

    # 📤 Tải CSV log về máy người dùng
    filename = f"email_log_{gmail_user}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return send_file(log_buffer, as_attachment=True, download_name=filename, mimetype="text/csv")


if __name__ == '__main__':
    app.run(debug=True, port=5000)
