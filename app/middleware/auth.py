import os
import jwt
from functools import wraps
from flask import request, jsonify
from app.services.supabase_client import supabase, supabase_admin


class _User:
    """Minimal user object for custom admin JWT sessions."""
    def __init__(self, user_id, email):
        self.id = user_id
        self.email = email


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        parts = auth_header.split()

        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({'message': 'Authorization header missing or malformed'}), 401

        token = parts[1]

        # Try custom admin JWT first (works even when GoTrue is down)
        try:
            payload = jwt.decode(token, os.getenv('SECRET_KEY'), algorithms=['HS256'])
            if payload.get('type') == 'admin_session':
                request.user = _User(payload['sub'], payload['email'])
                return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except Exception:
            pass

        # Fall back to Supabase JWT validation for regular users
        try:
            user = supabase.auth.get_user(token)
            request.user = user.user
        except Exception:
            return jsonify({'message': 'Token is invalid or expired'}), 401

        return f(*args, **kwargs)
    return decorated


def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_id = getattr(request.user, 'id', None)
            if not user_id:
                return jsonify({'message': 'User not authenticated'}), 401

            try:
                profile = supabase_admin.table('profiles').select('role').eq('id', user_id).maybe_single().execute()
            except Exception:
                return jsonify({'message': 'Permission denied'}), 403

            if not profile.data or profile.data.get('role') not in allowed_roles:
                return jsonify({'message': 'Permission denied'}), 403

            return f(*args, **kwargs)
        return decorated
    return decorator
