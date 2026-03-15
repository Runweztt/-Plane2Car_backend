import secrets
import string
from flask import Blueprint, request, jsonify
from app.services.supabase_client import supabase_admin
from app.middleware.auth import token_required, role_required
from app.services.email_service import (
    send_passenger_assignment_email,
    send_concierge_assignment_email,
    send_concierge_welcome_email,
)

admin_bp = Blueprint('admin', __name__)

VALID_VERIFICATION_STATUSES = {'approved', 'rejected'}


@admin_bp.route('/concierges/add', methods=['POST'])
@token_required
@role_required(['admin'])
def add_concierge():
    data = request.json or {}
    full_name = (data.get('full_name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    phone_number = (data.get('phone_number') or '').strip()
    password = (data.get('password') or '').strip()

    if not full_name or not email:
        return jsonify({"error": "full_name and email are required"}), 400

    # Auto-generate a password if not provided
    if not password:
        alphabet = string.ascii_letters + string.digits
        password = ''.join(secrets.choice(alphabet) for _ in range(12))
        auto_generated = True
    else:
        auto_generated = False

    try:
        # Create the auth user (email confirmed so they can log in immediately)
        user_res = supabase_admin.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {"full_name": full_name},
        })
        user_id = user_res.user.id
    except Exception as e:
        err_msg = str(e)
        if 'already been registered' in err_msg or 'already exists' in err_msg.lower():
            return jsonify({"error": "An account with this email already exists"}), 409
        return jsonify({"error": f"Failed to create auth user: {err_msg}"}), 400

    try:
        supabase_admin.table('profiles').insert({
            "id": user_id,
            "full_name": full_name,
            "email": email,
            "role": "concierge",
            "phone_number": phone_number or None,
            "verification_status": "approved",
        }).execute()
    except Exception as e:
        # Roll back the auth user if profile insert fails
        try:
            supabase_admin.auth.admin.delete_user(user_id)
        except Exception:
            pass
        return jsonify({"error": f"Failed to create profile: {str(e)}"}), 400

    # Send welcome email with login credentials
    try:
        send_concierge_welcome_email(email, full_name, password)
    except Exception:
        pass  # Don't fail the request if email send errors

    return jsonify({
        "id": user_id,
        "full_name": full_name,
        "email": email,
        "phone_number": phone_number,
        "auto_generated_password": auto_generated,
        "message": "Concierge created and welcome email sent",
    }), 201


@admin_bp.route('/bookings/assign', methods=['POST'])
@token_required
@role_required(['admin'])
def assign_concierge():
    data = request.json or {}
    booking_id = data.get('booking_id')
    concierge_id = data.get('concierge_id')

    if not booking_id or not concierge_id:
        return jsonify({"error": "booking_id and concierge_id are required"}), 400

    try:
        # Verify concierge is approved
        concierge_res = supabase_admin.table('profiles') \
            .select('full_name, email, phone_number, role, verification_status') \
            .eq('id', concierge_id).single().execute()

        if not concierge_res.data:
            return jsonify({"error": "Concierge not found"}), 404

        concierge = concierge_res.data
        if concierge.get('role') != 'concierge':
            return jsonify({"error": "User is not a concierge"}), 400
        if concierge.get('verification_status') != 'approved':
            return jsonify({"error": "Concierge is not verified"}), 400

        # Assign the concierge
        response = supabase_admin.table('bookings').update({
            "concierge_id": concierge_id,
            "status": "assigned",
        }).eq('id', booking_id).execute()

        if not response.data:
            return jsonify({"error": "Booking not found"}), 404

        # Fetch full booking details for email notifications
        booking_res = supabase_admin.table('bookings').select(
            '*, airports(name, code), profiles:passenger_id(full_name, email)'
        ).eq('id', booking_id).single().execute()

        booking = booking_res.data or {}
        passenger = booking.get('profiles') or {}
        airport = booking.get('airports') or {}

        passenger_name = passenger.get('full_name', 'Passenger')
        passenger_email = passenger.get('email')
        flight_number = booking.get('flight_number', 'N/A')
        arrival_time = booking.get('arrival_time', 'N/A')
        airport_name = airport.get('name', 'the airport')

        # Email the passenger
        if passenger_email:
            try:
                send_passenger_assignment_email(
                    passenger_email=passenger_email,
                    passenger_name=passenger_name,
                    concierge_name=concierge.get('full_name', ''),
                    concierge_phone=concierge.get('phone_number'),
                    flight_number=flight_number,
                    arrival_time=arrival_time,
                    airport_name=airport_name,
                )
            except Exception:
                pass

        # Email the concierge
        if concierge.get('email'):
            try:
                send_concierge_assignment_email(
                    concierge_email=concierge['email'],
                    concierge_name=concierge.get('full_name', ''),
                    passenger_name=passenger_name,
                    passenger_email=passenger_email or 'N/A',
                    flight_number=flight_number,
                    arrival_time=arrival_time,
                    airport_name=airport_name,
                )
            except Exception:
                pass

        return jsonify(response.data[0]), 200

    except Exception as e:
        return jsonify({"error": f"Failed to assign concierge: {str(e)}"}), 400


@admin_bp.route('/concierges/pending', methods=['GET'])
@token_required
@role_required(['admin'])
def get_pending_concierges():
    try:
        response = supabase_admin.table('profiles') \
            .select('id, full_name, email, phone_number, created_at') \
            .eq('role', 'concierge').eq('verification_status', 'pending').execute()
        return jsonify(response.data), 200
    except Exception:
        return jsonify({"error": "Failed to fetch pending concierges"}), 400


@admin_bp.route('/concierges/approved', methods=['GET'])
@token_required
@role_required(['admin'])
def get_approved_concierges():
    try:
        response = supabase_admin.table('profiles') \
            .select('id, full_name, email, phone_number') \
            .eq('role', 'concierge').eq('verification_status', 'approved').execute()
        return jsonify(response.data), 200
    except Exception:
        return jsonify({"error": "Failed to fetch approved concierges"}), 400


@admin_bp.route('/concierges/verify', methods=['POST'])
@token_required
@role_required(['admin'])
def verify_concierge():
    data = request.json or {}
    concierge_id = data.get('concierge_id')
    status = data.get('status')

    if not concierge_id or not status:
        return jsonify({"error": "concierge_id and status are required"}), 400

    if status not in VALID_VERIFICATION_STATUSES:
        return jsonify({"error": "status must be 'approved' or 'rejected'"}), 400

    try:
        response = supabase_admin.table('profiles').update({
            "verification_status": status,
        }).eq('id', concierge_id).eq('role', 'concierge').execute()

        if not response.data:
            return jsonify({"error": "Concierge not found"}), 404

        return jsonify(response.data[0]), 200
    except Exception:
        return jsonify({"error": "Failed to update verification status"}), 400
