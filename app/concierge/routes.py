from flask import Blueprint, request, jsonify
from ..services.supabase_client import supabase, supabase_admin
from ..middleware.auth import token_required, role_required

concierge_bp = Blueprint('concierge', __name__)

@concierge_bp.route('/bookings/<booking_id>/status', methods=['PATCH'])
@token_required
@role_required(['concierge'])
def update_booking_status(booking_id):
    data = request.json
    new_status = data.get('status')
    
    # Allowed status transitions for concierge
    allowed_statuses = [
        'passenger_arrived', 
        'passenger_met', 
        'baggage_assistance', 
        'escort_in_progress', 
        'completed'
    ]
    
    if new_status not in allowed_statuses:
        return jsonify({"message": "Invalid status update"}), 400
        
    try:
        # Ensure the concierge is assigned to this booking
        booking = supabase.table('bookings').select('concierge_id').eq('id', booking_id).single().execute()
        if booking.data.get('concierge_id') != request.user.id:
            return jsonify({"message": "Access denied"}), 403

        response = supabase_admin.table('bookings').update({
            "status": new_status
        }).eq('id', booking_id).execute()
        
        # Log status change (optional, but good for MVP)
        supabase_admin.table('booking_status_logs').insert({
            "booking_id": booking_id,
            "status": new_status,
            "changed_by": request.user.id
        }).execute()
        
        return jsonify(response.data[0]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
