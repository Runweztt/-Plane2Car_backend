from flask import Blueprint, request, jsonify
from app.services.supabase_client import supabase_admin
from app.middleware.auth import token_required, role_required

bookings_bp = Blueprint('bookings', __name__)


@bookings_bp.route('/', methods=['POST'])
@token_required
@role_required(['passenger'])
def create_booking():
    data = request.json or {}
    user_id = request.user.id

    airport_id = data.get('airport_id')
    service_tier_id = data.get('service_tier_id')
    flight_number = data.get('flight_number', '').strip()
    arrival_time = data.get('arrival_time')

    if not all([airport_id, service_tier_id, flight_number, arrival_time]):
        return jsonify({"error": "airport_id, service_tier_id, flight_number, and arrival_time are required"}), 400

    try:
        response = supabase_admin.table('bookings').insert({
            "passenger_id": user_id,
            "airport_id": airport_id,
            "service_tier_id": service_tier_id,
            "flight_number": flight_number,
            "arrival_time": arrival_time,
            "status": "pending"
        }).execute()
        return jsonify(response.data[0]), 201
    except Exception:
        return jsonify({"error": "Failed to create booking"}), 400


@bookings_bp.route('/', methods=['GET'])
@token_required
def get_user_bookings():
    user_id = request.user.id

    try:
        profile = supabase_admin.table('profiles').select('role').eq('id', user_id).single().execute()
        role = profile.data.get('role') if profile.data else None

        query = supabase_admin.table('bookings').select(
            '*, airports(name, code), service_tiers(name, price), '
            'profiles:passenger_id(full_name, email), concierge:concierge_id(full_name, phone_number)'
        )

        if role == 'passenger':
            query = query.eq('passenger_id', user_id)
        elif role == 'concierge':
            query = query.eq('concierge_id', user_id)
        # admin gets all

        response = query.order('arrival_time', desc=True).execute()
        return jsonify(response.data), 200
    except Exception:
        return jsonify({"error": "Failed to fetch bookings"}), 400


@bookings_bp.route('/<booking_id>', methods=['GET'])
@token_required
def get_booking_details(booking_id):
    user_id = request.user.id

    try:
        profile = supabase_admin.table('profiles').select('role').eq('id', user_id).single().execute()
        role = profile.data.get('role') if profile.data else None

        response = supabase_admin.table('bookings').select(
            '*, airports(name, code), service_tiers(name, price), '
            'profiles:passenger_id(full_name), concierge:concierge_id(full_name)'
        ).eq('id', booking_id).single().execute()

        if not response.data:
            return jsonify({"error": "Booking not found"}), 404

        booking = response.data

        # Enforce ownership: passengers see only their own, concierges see assigned ones
        if role == 'passenger' and booking.get('passenger_id') != user_id:
            return jsonify({"error": "Access denied"}), 403
        if role == 'concierge' and booking.get('concierge_id') != user_id:
            return jsonify({"error": "Access denied"}), 403

        return jsonify(booking), 200
    except Exception:
        return jsonify({"error": "Failed to fetch booking"}), 400


@bookings_bp.route('/airports', methods=['GET'])
def get_airports():
    try:
        response = supabase_admin.table('airports').select('*').execute()
        return jsonify(response.data), 200
    except Exception:
        return jsonify({"error": "Failed to fetch airports"}), 500


@bookings_bp.route('/tiers', methods=['GET'])
def get_tiers():
    try:
        response = supabase_admin.table('service_tiers').select('*').execute()
        return jsonify(response.data), 200
    except Exception:
        return jsonify({"error": "Failed to fetch service tiers"}), 500
