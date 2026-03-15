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
            if origin in Config.CORS_ORIGINS:
                resp = make_response('', 204)
                resp.headers['Access-Control-Allow-Origin'] = origin
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

    @app.route('/debug-keys')
    def debug_keys():
        from app.services.supabase_client import supabase, supabase_admin
        from config import Config
        results = {}

        # Check env vars are loaded
        results['SUPABASE_URL'] = bool(Config.SUPABASE_URL)
        results['SUPABASE_KEY'] = bool(Config.SUPABASE_KEY)
        results['SUPABASE_SERVICE_KEY'] = bool(Config.SUPABASE_SERVICE_KEY)
        results['SECRET_KEY'] = bool(Config.SECRET_KEY)

        # Test anon key — read public table
        try:
            r = supabase.table('airports').select('id').limit(1).execute()
            results['anon_key_table_read'] = 'OK'
        except Exception as e:
            results['anon_key_table_read'] = f'FAILED: {e}'

        # Test service role key — read profiles
        try:
            r = supabase_admin.table('profiles').select('id').limit(1).execute()
            results['service_key_table_read'] = 'OK'
        except Exception as e:
            results['service_key_table_read'] = f'FAILED: {e}'

        # Test service role auth admin
        try:
            users = supabase_admin.auth.admin.list_users()
            results['service_key_auth_admin'] = f'OK — {len(users)} users found'
        except Exception as e:
            results['service_key_auth_admin'] = f'FAILED: {e}'

        return results, 200

    return app


if __name__ == '__main__':
    app = create_app()
    debug = os.getenv('FLASK_ENV', 'production') == 'development'
    app.run(debug=debug, port=5000)
