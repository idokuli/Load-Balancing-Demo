import os
import secrets
import subprocess
from dotenv import load_dotenv
from flask import Flask, request, render_template, redirect, url_for, session, flash
from datetime import timedelta
from s3_service import S3Service

load_dotenv()

class S3WebApp:
    def __init__(self, s3_class):
        self._ensure_certs()
        self.app = Flask(__name__)
        self.app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)
        self.app.permanent_session_lifetime = timedelta(days=30)
        self.S3Class = s3_class
        self._setup_routes()

    def _ensure_certs(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        cert_path = os.path.join(base_dir, 'cert.pem')
        key_path = os.path.join(base_dir, 'key.pem')
        if not os.path.exists(cert_path):
            subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:4096", "-nodes", 
                           "-out", cert_path, "-keyout", key_path, "-days", "365", 
                           "-subj", "/CN=localhost"], check=True)

    def _get_worker(self):
        return self.S3Class(session.get('access'), session.get('secret'), session.get('region'))

    def _setup_routes(self):
        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            if request.method == 'POST':
                access, secret = request.form.get('access'), request.form.get('secret')
                region, bucket = request.form.get('region'), request.form.get('bucket')
                try:
                    temp_worker = self.S3Class(access, secret, region)
                    actual = temp_worker.get_actual_region(bucket)
                    if not actual:
                        flash("Connection Failed: Check keys or bucket name.", "error")
                    elif actual != region:
                        flash(f"Region Error: Bucket is in {actual}, not {region}.", "error")
                    else:
                        session.update({'access': access, 'secret': secret, 'region': actual, 'bucket': bucket})
                        return redirect(url_for('index'))
                except Exception as e:
                    flash(f"System Error: {str(e)}", "error")
            return render_template('login.html')

        @self.app.route('/')
        def index():
            if 'access' not in session: return redirect(url_for('login'))
            try:
                worker = self._get_worker()
                _, all_files = worker.list_files(session['bucket'], prefix='')
                v_status = worker.get_versioning_status(session['bucket'])
                return render_template('index.html', files=all_files, bucket=session['bucket'], v_status=v_status)
            except Exception as e:
                flash(f"AWS Fetch Error: {str(e)}", "error")
                return render_template('index.html', files=[], bucket=session.get('bucket'), v_status="Error")

        @self.app.route('/toggle_versioning')
        def toggle_versioning():
            worker = self._get_worker()
            current = worker.get_versioning_status(session['bucket'])
            new_status = 'Enabled' if current != 'Enabled' else 'Suspended'
            worker.set_versioning(session['bucket'], new_status)
            flash(f"Versioning set to {new_status}", "success")
            return redirect(url_for('index'))

        @self.app.route('/history/<path:filename>')
        def history(filename):
            worker = self._get_worker()
            versions = worker.get_file_versions(session['bucket'], filename)
            return render_template('history.html', filename=filename, versions=versions)

        @self.app.route('/download_version/<path:filename>/<version_id>')
        def download_version(filename, version_id):
            worker = self._get_worker()
            url = worker.get_version_url(session['bucket'], filename, version_id)
            return redirect(url)

        @self.app.route('/upload', methods=['POST'])
        def upload():
            f = request.files.get('file')
            if f:
                try:
                    name = f.filename.lower()
                    if name.endswith((".jpg", ".png", ".jpeg")): folder = "images/"
                    elif name.endswith(".pdf"): folder = "pdf/"
                    else: folder = "others/"
                    target_key = f"{folder}{f.filename}"
                    self._get_worker().upload(session['bucket'], f, target_key, f.content_type)
                    flash(f"Uploaded to: {target_key}", "success")
                except Exception as e:
                    flash(f"Upload Failed: {str(e)}", "error")
            return redirect(url_for('index'))

        @self.app.route('/download/<path:filename>')
        def download(filename):
            try:
                url = self._get_worker().get_url(session['bucket'], filename)
                return redirect(url)
            except Exception as e:
                flash(f"Download Error: {str(e)}", "error")
                return redirect(url_for('index'))

        @self.app.route('/delete/<path:filename>')
        def delete(filename):
            try:
                self._get_worker().delete(session['bucket'], filename)
                flash("File deleted successfully.", "success")
            except Exception as e:
                flash(f"Delete Error: {str(e)}", "error")
            return redirect(url_for('index'))

        @self.app.route('/logout')
        def logout():
            session.clear()
            return redirect(url_for('login'))

    def start(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        cert, key = os.path.join(base_dir, 'cert.pem'), os.path.join(base_dir, 'key.pem')
        self.app.run(host='0.0.0.0', port=443, ssl_context=(cert, key))