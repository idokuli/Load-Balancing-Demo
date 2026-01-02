from s3_service import S3Service
from web_config import S3WebApp

# CORRECT
def main():
    web_server = S3WebApp()
    web_server.run()

if __name__ == '__main__':
    main()