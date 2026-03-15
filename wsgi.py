# Entry point for Gunicorn (Hostinger VPS) and Vercel Serverless
from main import create_app

app = create_app()

if __name__ == '__main__':
    app.run()
