import os
from flask import Blueprint, request, jsonify
from app.services.supabase_client import supabase, supabase_admin

auth_bp = Blueprint('auth', __name__)

ALLOWED_ROLES = {'passenger', 'concierge'}


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json or {}
    email = data.get('email', '').strip()
    password = data.get('password', '')
    full_name = data.get('full_name', '').strip()
    role = data.get('role', 'passenger')

    if not email or not password or not full_name:
        return jsonify({"error": "email, password, and full_name are required"}), 400

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    # Prevent privilege escalation — only passenger/concierge allowed at registration
    if role not in ALLOWED_ROLES:
        role = 'passenger'

    try:
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "full_name": full_name,
                    "role": role
                }
            }
        })
    except Exception as e:
        return jsonify({"error": "Registration failed", "detail": str(e)}), 400

    if not auth_response.user:
        return jsonify({"error": "Registration failed — no user returned"}), 400

    # If identities is empty the email is already confirmed in Supabase — reject duplicate
    identities = getattr(auth_response.user, 'identities', None)
    if identities is not None and len(identities) == 0:
        return jsonify({"error": "An account with this email already exists. Please log in."}), 409

    try:
        # upsert so repeated registration attempts don't crash on duplicate key
        supabase_admin.table('profiles').upsert({
            "id": auth_response.user.id,
            "full_name": full_name,
            "role": role,
            "email": email
        }).execute()
    except Exception as e:
        return jsonify({"error": "Profile creation failed", "detail": str(e)}), 400

    session = auth_response.session
    return jsonify({
        "message": "Registration successful",
        "user_id": auth_response.user.id,
        "access_token": session.access_token if session else None,
        "user": {
            "id": auth_response.user.id,
            "email": email,
            "full_name": full_name,
            "role": role
        }
    }), 201


@auth_bp.route('/admin-login', methods=['POST'])
def admin_login():
    import jwt
    import datetime

    try:
        data = request.json or {}
        email = data.get('email', '').strip()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({"error": "email and password are required"}), 400

        admin_email = os.getenv('ADMIN_EMAIL', '').strip()
        admin_password = os.getenv('ADMIN_PASSWORD', '').strip()

        if not admin_email or not admin_password:
            return jsonify({"error": "Admin credentials not configured on server"}), 500

        if email != admin_email or password != admin_password:
            return jsonify({"error": "Invalid admin credentials"}), 401

        try:
            profile = supabase_admin.table('profiles').select('id, full_name, role').eq('email', email).maybe_single().execute()
        except Exception as e:
            return jsonify({"error": "Could not fetch admin profile", "detail": str(e)}), 500

        if not profile.data or profile.data.get('role') != 'admin':
            return jsonify({"error": "Access denied. Admin role not found."}), 403

        payload = {
            "sub": profile.data['id'],
            "email": email,
            "role": "admin",
            "type": "admin_session",
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }
        token = jwt.encode(payload, os.getenv('SECRET_KEY'), algorithm='HS256')

        return jsonify({
            "access_token": token,
            "user": {
                "id": profile.data['id'],
                "email": email,
                "full_name": profile.data.get('full_name', ''),
                "role": "admin"
            }
        }), 200

    except Exception as e:
        return jsonify({"error": "Admin login failed", "detail": str(e)}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json or {}
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
    except Exception:
        return jsonify({"error": "Invalid email or password"}), 401

    # Auth succeeded — fetch role separately so a missing profile never kills login
    role = 'passenger'
    full_name = ''
    try:
        profile = supabase_admin.table('profiles').select('role, full_name').eq('id', response.user.id).maybe_single().execute()
        if profile.data:
            role = profile.data.get('role', 'passenger')
            full_name = profile.data.get('full_name', '')
    except Exception:
        pass

    return jsonify({
        "access_token": response.session.access_token,
        "user": {
            "id": response.user.id,
            "email": response.user.email,
            "full_name": full_name,
            "role": role
        }
    }), 200
