from s3_service import S3Service
from web_config import S3WebApp

def main():
    web_server = S3WebApp(S3Service)
    print("--- Secure S3 Manager Started ---")
    web_server.start(host='0.0.0.0', port=443)

if __name__ == '__main__':
    main()