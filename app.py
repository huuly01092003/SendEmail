from flask import Flask, render_template, request, send_file, jsonify
from modules.email_sender import send_emails
from modules.excel_splitter import split_excel
import os, tempfile, zipfile
from datetime import datetime
import threading


app = Flask(__name__)

app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default_secret_key') 

# Dictionary để lưu trạng thái gửi email
email_status = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/split', methods=['POST'])
def split_route():
    return split_excel()

@app.route('/send_emails', methods=['POST'])
def send_emails_route():
    try:
        # Tạo job ID
        job_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
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

        # Khởi tạo status
        email_status[job_id] = {
            'status': 'processing',
            'progress': 0,
            'total': 0,
            'log_buffer': None
        }

        # Chạy gửi email trong background thread
        def send_in_background():
            try:
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
                    end_row=end_row_email,
                    progress_callback=lambda current, total: update_progress(job_id, current, total)
                )
                email_status[job_id]['status'] = 'completed'
                email_status[job_id]['log_buffer'] = log_buffer
            except Exception as e:
                email_status[job_id]['status'] = 'failed'
                email_status[job_id]['error'] = str(e)

        thread = threading.Thread(target=send_in_background)
        thread.start()

        # Trả về job_id để client có thể check progress
        return jsonify({
            'job_id': job_id,
            'message': 'Đang xử lý gửi email. Vui lòng đợi...'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def update_progress(job_id, current, total):
    if job_id in email_status:
        email_status[job_id]['progress'] = current
        email_status[job_id]['total'] = total

@app.route('/check_status/<job_id>', methods=['GET'])
def check_status(job_id):
    if job_id not in email_status:
        return jsonify({'error': 'Job not found'}), 404
    
    status = email_status[job_id]
    return jsonify({
        'status': status['status'],
        'progress': status.get('progress', 0),
        'total': status.get('total', 0)
    })

@app.route('/download_log/<job_id>', methods=['GET'])
def download_log(job_id):
    if job_id not in email_status:
        return "Job not found", 404
    
    if email_status[job_id]['status'] != 'completed':
        return "Job not completed yet", 400
    
    log_buffer = email_status[job_id]['log_buffer']
    if not log_buffer:
        return "No log available", 404
    
    filename = f"email_log_{job_id}.csv"
    return send_file(log_buffer, as_attachment=True, download_name=filename, mimetype="text/csv")


if __name__ == '__main__':
    app.run(debug=True, port=5000)