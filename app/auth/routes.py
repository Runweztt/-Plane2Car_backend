import os
import jwt
import datetime
from flask import Blueprint, request, jsonify
from app.services.supabase_client import supabase, supabase_admin

auth_bp = Blueprint('auth', __name__)

ALLOWED_ROLES = {'passenger', 'concierge'}


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    full_name = data.get('full_name', '').strip()
    role = data.get('role', 'passenger')

    if not email or not password or not full_name:
        return jsonify({"error": "email, password, and full_name are required"}), 400

    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400

    if len(full_name) > 100 or len(email) > 254:
        return jsonify({"error": "Input too long"}), 400

    if role not in ALLOWED_ROLES:
        role = 'passenger'

    # Create the Supabase auth user
    try:
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {"full_name": full_name, "role": role},
                "email_redirect_to": f"{Config.FRONTEND_URL_BASE}/login",
            }
        })
    except Exception as e:
        return jsonify({"error": "Registration failed", "detail": str(e)}), 400

    if not auth_response.user:
        return jsonify({"error": "Registration failed"}), 400

    # Reject duplicate confirmed accounts
    identities = getattr(auth_response.user, 'identities', None)
    if identities is not None and len(identities) == 0:
        return jsonify({"error": "An account with this email already exists. Please log in."}), 409

    # Upsert profile — safe for repeated attempts
    try:
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


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    # Check if the email exists but is unconfirmed — Supabase returns the same
    # "Invalid login credentials" error for both wrong password AND unconfirmed email,
    # so we must distinguish them using the admin client before attempting sign-in.
    try:
        admin_lookup = supabase_admin.auth.admin.get_user_by_email(email)
        if admin_lookup and admin_lookup.user:
            if not admin_lookup.user.email_confirmed_at:
                return jsonify({"error": "Please confirm your email address. Check your inbox for the confirmation link."}), 401
    except Exception:
        pass  # If lookup fails, proceed to sign-in and let it surface naturally

    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
    except Exception as e:
        return jsonify({"error": "Invalid email or password"}), 401

    # Supabase returns session=None when email confirmation is required.
    # Guard explicitly — accessing .access_token on None raises AttributeError → 500.
    if not response.session:
        return jsonify({"error": "Please confirm your email address before signing in."}), 401

    # Fetch role from profiles — use .limit(1) instead of maybe_single() for reliability
    role = 'passenger'
    full_name = ''
    try:
        result = supabase_admin.table('profiles').select('role, full_name').eq('id', response.user.id).limit(1).execute()
        if result.data:
            role = result.data[0].get('role', 'passenger')
            full_name = result.data[0].get('full_name', '')
    except Exception:
        pass  # Non-fatal — default role applies

    return jsonify({
        "access_token": response.session.access_token,
        "user": {
            "id": response.user.id,
            "email": response.user.email,
            "full_name": full_name,
            "role": role
        }
    }), 200


@auth_bp.route('/admin-login', methods=['POST'])
def admin_login():
    try:
        data = request.json or {}
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({"error": "email and password are required"}), 400

        admin_email = os.getenv('ADMIN_EMAIL', '').strip().lower()
        admin_password = os.getenv('ADMIN_PASSWORD', '').strip()

        if not admin_email or not admin_password:
            return jsonify({"error": "Admin credentials not configured on server"}), 500

        if email != admin_email or password != admin_password:
            return jsonify({"error": "Invalid admin credentials"}), 401

        # Use .limit(1) — maybe_single() returns None in supabase-py 2.9.x when no row found
        try:
            result = supabase_admin.table('profiles').select('id, full_name, role').eq('email', email).limit(1).execute()
        except Exception:
            return jsonify({"error": "Could not fetch admin profile"}), 500

        if not result.data:
            return jsonify({"error": "Admin profile not found. Run create_admin.py to set up the admin account."}), 403

        profile_data = result.data[0]

        if profile_data.get('role') != 'admin':
            return jsonify({"error": "Access denied"}), 403

        payload = {
            "sub": profile_data['id'],
            "email": email,
            "role": "admin",
            "type": "admin_session",
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }
        token = jwt.encode(payload, os.getenv('SECRET_KEY'), algorithm='HS256')

        return jsonify({
            "access_token": token,
            "user": {
                "id": profile_data['id'],
                "email": email,
                "full_name": profile_data.get('full_name', ''),
                "role": "admin"
            }
        }), 200

    except Exception as e:
        return jsonify({"error": "Admin login failed", "detail": str(e)}), 500
