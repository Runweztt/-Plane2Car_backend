import os
from flask import Flask
from flask_cors import CORS
from config import Config


def create_app():
    # Fail fast at startup if required env vars are missing.
    # In production this surfaces immediately in Vercel build/runtime logs
    # rather than as a cryptic 500 on the first request.
    Config.validate()

    app = Flask(__name__)
    app.config.from_object(Config)

    # Flask-CORS handles OPTIONS preflight automatically — do NOT add a
    # manual before_request handler alongside it.  Mixing the two produces
    # duplicate Access-Control-Allow-Origin headers which browsers reject.
    CORS(
        app,
        origins=Config.CORS_ORIGINS,
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        max_age=86400,
    )

    from app.auth.routes import auth_bp
    from app.bookings.routes import bookings_bp
    from app.concierge.routes import concierge_bp
    from app.admin.routes import admin_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(bookings_bp, url_prefix='/api/bookings')
    app.register_blueprint(concierge_bp, url_prefix='/api/concierge')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')

    # Security headers on every response
    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    # JSON error handlers
    @app.errorhandler(404)
    def not_found(e):
        return {'error': 'Not found'}, 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return {'error': 'Method not allowed'}, 405

    @app.errorhandler(500)
    def server_error(e):
        return {'error': 'Internal server error'}, 500

    @app.route('/health')
    def health():
        return {'status': 'healthy'}, 200

    return app


if __name__ == '__main__':
    app = create_app()
    debug = os.getenv('FLASK_ENV', 'production') == 'development'
    app.run(debug=debug, port=5000)
