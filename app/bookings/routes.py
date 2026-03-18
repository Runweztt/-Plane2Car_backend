import uuid
import requests as http_requests
from flask import Blueprint, request, jsonify
from app.services.supabase_client import supabase_admin
from app.middleware.auth import token_required, role_required
from config import Config

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

    # Reject bookings for inactive airports
    airport = supabase_admin.table('airports').select('is_active').eq('id', airport_id).single().execute()
    if not airport.data or not airport.data.get('is_active', False):
        return jsonify({"error": "This airport is not yet available. Please select Murtala Muhammed International Airport (Lagos)."}), 400

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

        if role == 'passenger' and booking.get('passenger_id') != user_id:
            return jsonify({"error": "Access denied"}), 403
        if role == 'concierge' and booking.get('concierge_id') != user_id:
            return jsonify({"error": "Access denied"}), 403

        return jsonify(booking), 200
    except Exception:
        return jsonify({"error": "Failed to fetch booking"}), 400


# ── Payment endpoints ────────────────────────────────────────────────────────

@bookings_bp.route('/<booking_id>/payment/initiate', methods=['POST'])
@token_required
@role_required(['passenger'])
def initiate_payment(booking_id):
    """
    Initialises a Paystack transaction entirely on the server.
    Idempotent: if a pending payment already exists for this booking,
    returns the cached authorization_url without calling Paystack again.
    The secret key never leaves the backend.
    """
    if not Config.PAYSTACK_SECRET_KEY:
        return jsonify({"error": "Payment is not configured on this server."}), 503

    try:
        # 1. Load booking + tier price, verify ownership
        booking = supabase_admin.table('bookings').select(
            'id, passenger_id, payment_status, service_tiers(price)'
        ).eq('id', booking_id).single().execute()

        if not booking.data or booking.data.get('passenger_id') != request.user.id:
            return jsonify({"error": "Booking not found"}), 404

        if booking.data.get('payment_status') == 'paid':
            return jsonify({"error": "This booking has already been paid."}), 400

        # 2. Idempotency check — one payment row per booking
        idempotency_key = booking_id
        existing = supabase_admin.table('payments') \
            .select('status, authorization_url') \
            .eq('idempotency_key', idempotency_key) \
            .maybe_single().execute()

        if existing.data:
            if existing.data.get('status') == 'paid':
                return jsonify({"error": "This booking has already been paid."}), 400
            # Pending payment exists — return cached URL, no new Paystack call
            if existing.data.get('authorization_url'):
                return jsonify({"authorization_url": existing.data['authorization_url']}), 200

        # 3. Build Paystack request
        price = booking.data.get('service_tiers', {}).get('price', 0)
        amount_cents = int(float(price) * 100)  # Paystack expects amount in cents for USD
        reference = f"P2C-{booking_id[:8]}-{uuid.uuid4().hex[:8]}"
        callback_url = f"{Config.FRONTEND_URL_BASE}/payment/callback"

        profile = supabase_admin.table('profiles').select('email') \
            .eq('id', request.user.id).single().execute()
        email = profile.data.get('email') if profile.data else None

        # 4. Call Paystack (secret key stays on server)
        resp = http_requests.post(
            "https://api.paystack.co/transaction/initialize",
            headers={
                "Authorization": f"Bearer {Config.PAYSTACK_SECRET_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "email": email,
                "amount": amount_cents,
                "currency": "USD",
                "reference": reference,
                "callback_url": callback_url,
                "metadata": {"booking_id": booking_id},
            },
            timeout=15,
        )
        resp.raise_for_status()
        ps_data = resp.json()

        if not ps_data.get("status"):
            return jsonify({"error": "Payment provider rejected the request."}), 502

        authorization_url = ps_data["data"]["authorization_url"]

        # 5. Persist payment record (upsert on idempotency_key)
        supabase_admin.table('payments').upsert({
            "booking_id": booking_id,
            "passenger_id": request.user.id,
            "amount": float(price),
            "currency": "USD",
            "paystack_reference": reference,
            "authorization_url": authorization_url,
            "idempotency_key": idempotency_key,
            "status": "pending",
        }, on_conflict="idempotency_key").execute()

        return jsonify({"authorization_url": authorization_url}), 200

    except http_requests.RequestException:
        return jsonify({"error": "Could not reach payment provider. Try again."}), 502
    except Exception as e:
        print(f"[initiate_payment] {e}")
        return jsonify({"error": "Failed to initiate payment."}), 500


@bookings_bp.route('/payment/verify', methods=['POST'])
@token_required
@role_required(['passenger'])
def verify_payment():
    """
    Verifies a Paystack reference server-side and marks the booking paid.
    Idempotent: calling this twice for the same reference is safe.
    """
    if not Config.PAYSTACK_SECRET_KEY:
        return jsonify({"error": "Payment is not configured on this server."}), 503

    data = request.json or {}
    reference = data.get('reference', '').strip()
    if not reference:
        return jsonify({"error": "Payment reference is required."}), 400

    try:
        # 1. Verify with Paystack
        resp = http_requests.get(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers={"Authorization": f"Bearer {Config.PAYSTACK_SECRET_KEY}"},
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()

        tx = result.get("data", {})
        if not result.get("status") or tx.get("status") != "success":
            return jsonify({"error": "Payment was not successful."}), 402

        booking_id = tx.get("metadata", {}).get("booking_id")
        if not booking_id:
            return jsonify({"error": "Booking ID missing from payment metadata."}), 400

        # 2. Verify ownership
        booking = supabase_admin.table('bookings').select('passenger_id, payment_status') \
            .eq('id', booking_id).single().execute()

        if not booking.data or booking.data.get('passenger_id') != request.user.id:
            return jsonify({"error": "Booking not found."}), 404

        # 3. Idempotency — already processed, return success immediately
        if booking.data.get('payment_status') == 'paid':
            return jsonify({"booking_id": booking_id, "status": "paid"}), 200

        # 4. Mark payment record paid
        supabase_admin.table('payments').update({
            "status": "paid",
            "provider_response": tx,
        }).eq('paystack_reference', reference).execute()

        # 5. Mark booking paid
        supabase_admin.table('bookings').update({
            "payment_status": "paid",
            "payment_reference": reference,
        }).eq('id', booking_id).execute()

        return jsonify({"booking_id": booking_id, "status": "paid"}), 200

    except http_requests.RequestException:
        return jsonify({"error": "Could not reach payment provider. Try again."}), 502
    except Exception as e:
        print(f"[verify_payment] {e}")
        return jsonify({"error": "Failed to verify payment."}), 500


# ── Reference data endpoints ─────────────────────────────────────────────────

@bookings_bp.route('/airports', methods=['GET'])
def get_airports():
    try:
        response = supabase_admin.table('airports').select('*').order('is_active', desc=True).execute()
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
