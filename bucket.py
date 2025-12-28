import os
import boto3
from flask import Flask, request, render_template_string, redirect, url_for
from dotenv import load_dotenv

# Load credentials from .env file
load_dotenv()

app = Flask(__name__)

# --- AWS CONFIGURATION ---
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
REGION_NAME = os.getenv('REGION_NAME')
BUCKET_NAME = os.getenv('BUCKET_NAME')

# Initialize S3 Client
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=REGION_NAME
)

# --- THE UI (HTML/CSS) ---
HTML_UI = """
<!DOCTYPE html>
<html>
<head>
    <title>SECURE S3 Manager</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background: #eef2f7; }
        .container { max-width: 800px; margin: auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
        h2 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        .upload-section { background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 30px; border: 1px dashed #cbd5e0; }
        .file-item { display: flex; justify-content: space-between; align-items: center; padding: 15px; border-bottom: 1px solid #edf2f7; }
        .file-item:last-child { border-bottom: none; }
        .btn { padding: 8px 16px; border-radius: 6px; text-decoration: none; font-weight: 600; cursor: pointer; transition: 0.2s; border: none; }
        .btn-upload { background: #3498db; color: white; }
        .btn-download { background: #2ecc71; color: white; margin-right: 5px; }
        .btn-delete { background: #e74c3c; color: white; }
        .btn:hover { opacity: 0.8; }
        .badge { font-size: 0.8em; color: #7f8c8d; }
    </style>
</head>
<body>
    <div class="container">
        <h2><span style="color: #27ae60;">🔒</span> S3 HTTPS Manager</h2>
        
        <div class="upload-section">
            <form action="/upload" method="post" enctype="multipart/form-data">
                <input type="file" name="file" required>
                <button type="submit" class="btn btn-upload">Upload to S3</button>
            </form>
        </div>

        <h3>Files in Bucket: <span class="badge">{{ bucket }}</span></h3>
        <div class="file-list">
            {% for file in files %}
            <div class="file-item">
                <span>{{ file }}</span>
                <div>
                    <a class="btn btn-download" href="/download/{{ file }}">Download</a>
                    <a class="btn btn-delete" href="/delete/{{ file }}" onclick="return confirm('Delete this file permanently?')">Delete</a>
                </div>
            </div>
            {% endfor %}
            {% if not files %}<p style="color: #95a5a6;">No files found in this bucket.</p>{% endif %}
        </div>
    </div>
</body>
</html>
"""

# --- ROUTES ---

@app.route('/')
def index():
    files = []
    try:
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)
        if 'Contents' in response:
            files = [obj['Key'] for obj in response['Contents']]
    except Exception as e:
        return f"S3 Error: {str(e)} - Check your .env credentials and region!"
    
    return render_template_string(HTML_UI, files=files, bucket=BUCKET_NAME)

@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files.get('file')
    if file:
        s3_client.upload_fileobj(
            file, 
            BUCKET_NAME, 
            file.filename, 
            ExtraArgs={"ContentType": file.content_type}
        )
    return redirect(url_for('index'))

@app.route('/download/<path:filename>')
def download_file(filename):
    url = s3_client.generate_presigned_url(
        'get_object', 
        Params={'Bucket': BUCKET_NAME, 'Key': filename}, 
        ExpiresIn=3600
    )
    return redirect(url)

@app.route('/delete/<path:filename>')
def delete_file(filename):
    s3_client.delete_object(Bucket=BUCKET_NAME, Key=filename)
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Changed port to 443
    app.run(
        host='0.0.0.0', 
        port=443, 
        ssl_context=('cert.pem', 'key.pem'),
        debug=True
    )