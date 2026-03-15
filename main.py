import os
from flask import Flask, request, make_response
from flask_cors import CORS
from config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, origins=Config.CORS_ORIGINS, supports_credentials=True, allow_headers=["Content-Type", "Authorization"], methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])

    # Handle CORS preflight (OPTIONS) before Flask routing kicks in
    @app.before_request
    def handle_options():
        if request.method == 'OPTIONS':
            origin = request.headers.get('Origin', '')
            allowed = Config.CORS_ORIGINS
            if '*' in allowed or origin in allowed:
                resp = make_response('', 204)
                resp.headers['Access-Control-Allow-Origin'] = origin if origin else '*'
                resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
                resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
                resp.headers['Access-Control-Allow-Credentials'] = 'true'
                resp.headers['Access-Control-Max-Age'] = '86400'
                return resp

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
