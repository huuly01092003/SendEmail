import os
# ⭐ ALLOW HTTP ON LOCALHOST FOR OAUTH (Remove in production)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from dotenv import load_dotenv
from flask import Flask, render_template, request, session, redirect, url_for, jsonify, send_file
from flask_session import Session
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO
import tempfile, zipfile
import threading
import base64
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# ✅ LOAD .env FILE
load_dotenv()

# ✅ Flask App Config - CRITICAL FIXES
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')

# ✅ Session Config - FIX: Use memory + increase timeouts
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True  # ⭐ CHANGED: Keep session after browser close
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)  # ⭐ CHANGED: Longer timeout
app.config['SESSION_COOKIE_SECURE'] = False  # HTTP on localhost
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # ⭐ Allow cross-site callback
app.config['SESSION_COOKIE_NAME'] = 'gmail_oauth_session'
app.config['SESSION_REFRESH_EACH_REQUEST'] = True  # ⭐ Refresh on every request

Session(app)

# ✅ Create session directory
SESSION_DIR = os.path.join(os.path.dirname(__file__), 'flask_session')
os.makedirs(SESSION_DIR, exist_ok=True)

# ✅ In-memory state store (backup for filesystem issues)
STATE_STORE = {}

# ✅ Google OAuth Config
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/gmail.readonly',
    'openid'
]
CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
REDIRECT_URI = os.environ.get('REDIRECT_URI', 'http://localhost:5000/oauth2callback')

# ✅ Global tracking
email_status = {}

# ✅ Check env variables
if not CLIENT_ID or not CLIENT_SECRET:
    print("⚠️ WARNING: GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not set!")
else:
    print("✅ OAuth Config Loaded Successfully")
    print(f"  CLIENT_ID: {CLIENT_ID[:30]}...")
    print(f"  REDIRECT_URI: {REDIRECT_URI}")
    print(f"  Session folder: {SESSION_DIR}\n")

# ⭐ NEW: Session persistence before request
@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(hours=24)

@app.route('/auth/login')
def oauth_login():
    """Initiate Google OAuth flow with dual state storage"""
    try:
        print("\n🔵 [OAuth Login] Initiating...")
        
        # ✅ Create OAuth flow
        flow = Flow.from_client_config(
            {
                "installed": {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [REDIRECT_URI]
                }
            },
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        
        # ✅ Generate auth URL and state
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        # ⭐ DUAL STORAGE: Save state to both session AND in-memory store
        session['oauth_state'] = state
        session['oauth_state_time'] = datetime.now().isoformat()
        STATE_STORE[state] = {
            'timestamp': datetime.now().isoformat(),
            'session_id': request.cookies.get('gmail_oauth_session', 'new')
        }
        session.modified = True
        
        print(f"✅ State created: {state[:40]}...")
        print(f"  Saved to session: YES")
        print(f"  Saved to memory: YES")
        print(f"  Session cookie: {request.cookies.get('gmail_oauth_session', 'NEW')}")
        
        return redirect(auth_url)
        
    except Exception as e:
        print(f"❌ [OAuth Login] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/oauth2callback')
def oauth_callback():
    """Handle OAuth callback with state verification"""
    try:
        print("\n🔵 [OAuth Callback] Received...")
        
        # ✅ Get state from Google
        state_from_google = request.args.get('state')
        code = request.args.get('code')
        error = request.args.get('error')
        
        # ✅ Get state from session (multiple attempts)
        state_from_session = session.get('oauth_state')
        state_from_memory = STATE_STORE.get(state_from_google, {})
        
        print(f"  Google State: {state_from_google[:40] if state_from_google else 'NONE'}...")
        print(f"  Session State: {state_from_session[:40] if state_from_session else 'NONE'}...")
        print(f"  Memory Store: {'EXISTS' if state_from_memory else 'MISSING'}")
        print(f"  Code: {code[:20] if code else 'NONE'}...")
        
        # ✅ Check for error from Google
        if error:
            print(f"❌ Google Error: {error}")
            return f"❌ Google Error: {error}", 400
        
        # ✅ Verify state (session OR memory)
        if not state_from_google:
            print("❌ No state from Google")
            return "❌ No state from Google - Login again", 400
        
        if not code:
            print("❌ No authorization code")
            return "❌ No authorization code - Login again", 400
        
        # ⭐ FIXED: Check BOTH session and memory store
        if state_from_session and state_from_google == state_from_session:
            print("✅ State verified from SESSION")
            verified = True
        elif state_from_memory:
            print("✅ State verified from MEMORY STORE")
            verified = True
        else:
            print("❌ State NOT verified - MISMATCH")
            return "❌ State mismatch - Login again", 400
        
        if not verified:
            return "❌ State verification failed - Login again", 400
        
        print(f"✅ State verification PASSED")
        
        # ✅ Exchange code for tokens
        flow = Flow.from_client_config(
            {
                "installed": {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [REDIRECT_URI]
                }
            },
            scopes=SCOPES,
            state=state_from_google,
            redirect_uri=REDIRECT_URI
        )
        
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        
        print(f"✅ Tokens received from Google")
        
        # ✅ Get user email
        service = build('gmail', 'v1', credentials=credentials)
        profile = service.users().getProfile(userId='me').execute()
        user_email = profile.get('emailAddress', '')
        
        print(f"✅ User email: {user_email}")
        
        # ✅ Save to session
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        session['user_email'] = user_email
        session['oauth_state'] = None  # Clear state
        session.modified = True
        
        # ✅ Clean up state store
        if state_from_google in STATE_STORE:
            del STATE_STORE[state_from_google]
        
        print(f"✅ Session saved - Logged in as: {user_email}\n")
        
        return redirect(url_for('index'))
        
    except Exception as e:
        print(f"❌ [OAuth Callback] Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"❌ Error: {str(e)}", 500

@app.route('/auth/logout')
def oauth_logout():
    """Logout user"""
    user_email = session.get('user_email', 'Unknown')
    print(f"\n✅ Logged out: {user_email}\n")
    session.clear()
    return redirect(url_for('index'))

# ==================== HELPER FUNCTIONS ====================

def refresh_access_token_if_needed(credentials):
    """Refresh access token if expired"""
    if credentials.expired and credentials.refresh_token:
        print("⚠️ [Token Refresh] Refreshing expired access token...")
        credentials.refresh(Request())
        print("✅ [Token Refresh] Token refreshed")
    return credentials

# ==================== MAIN ROUTES ====================

@app.route('/')
def index():
    user_email = session.get('user_email')
    return render_template('index_multiuser.html', user_email=user_email)

@app.route('/split', methods=['POST'])
def split_route():
    """Split Excel file (no login required)"""
    try:
        from modules.excel_splitter import split_excel
        return split_excel()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/send_emails', methods=['POST'])
def send_emails_route():
    """Send emails (login required)"""
    try:
        # ✅ Check login
        if 'user_email' not in session:
            return jsonify({'error': 'Please login with Gmail first'}), 401
        
        if 'credentials' not in session:
            return jsonify({'error': 'OAuth token invalid - Please login again'}), 401
        
        print(f"\n🔵 [Send Emails] Started by: {session['user_email']}")
        
        job_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        sender_name = request.form.get('sender_name', 'System')
        
        ref_col = request.form['ref_col']
        name_col = request.form.get('name_col')
        email_col = request.form['email_col']
        cc_col = request.form.get('cc_col')
        subject = request.form['subject']
        body = request.form['body']
        
        start_row_email = int(request.form.get('start_row_email', 2))
        end_row_email = int(request.form.get('end_row_email', 99999))
        
        split_zip = request.files.get('split_zip')
        email_file = request.files.get('email_file')
        
        if not split_zip or not email_file:
            return jsonify({'error': 'Please upload both files (ZIP + Email list)'}), 400
        
        temp_dir = tempfile.mkdtemp()
        
        zip_path = os.path.join(temp_dir, "split.zip")
        excel_email_path = os.path.join(temp_dir, "emails.xlsx")
        
        split_zip.save(zip_path)
        email_file.save(excel_email_path)
        
        extract_folder = os.path.join(temp_dir, "excel_files")
        os.makedirs(extract_folder, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_folder)
        
        email_status[job_id] = {
            'status': 'processing',
            'progress': 0,
            'total': 0,
            'log_buffer': None
        }
        
        def send_in_background():
            try:
                from modules.email_sender_oauth import send_emails_oauth
                
                # ✅ Restore credentials from session
                creds_dict = session['credentials']
                credentials = Credentials(
                    token=creds_dict['token'],
                    refresh_token=creds_dict['refresh_token'],
                    token_uri=creds_dict['token_uri'],
                    client_id=creds_dict['client_id'],
                    client_secret=creds_dict['client_secret'],
                    scopes=creds_dict['scopes']
                )
                
                log_buffer = send_emails_oauth(
                    credentials=credentials,
                    sender_email=session['user_email'],
                    sender_name=sender_name,
                    excel_folder=extract_folder,
                    email_file_path=excel_email_path,
                    ref_col=ref_col,
                    name_col=name_col,
                    email_col=email_col,
                    cc_col=cc_col,
                    selected_col_for_match=ref_col,
                    subject_template=subject,
                    body_template=body,
                    start_row=start_row_email,
                    end_row=end_row_email,
                    progress_callback=lambda current, total: update_progress(job_id, current, total)
                )
                email_status[job_id]['status'] = 'completed'
                email_status[job_id]['log_buffer'] = log_buffer
                print(f"✅ [Send Emails] Completed")
            except Exception as e:
                email_status[job_id]['status'] = 'failed'
                email_status[job_id]['error'] = str(e)
                print(f"❌ [Send Emails] Failed: {str(e)}")
        
        thread = threading.Thread(target=send_in_background)
        thread.start()
        
        return jsonify({
            'job_id': job_id,
            'message': 'Processing emails...'
        })
    
    except Exception as e:
        print(f"❌ [Send Emails] Error: {str(e)}")
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