from main import create_app
import os

app = create_app()

if __name__ == '__main__':
    debug = os.getenv('FLASK_ENV', 'production') == 'development'
    app.run(debug=debug, port=5000)
