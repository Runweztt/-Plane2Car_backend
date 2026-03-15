"""
Run this once to create the admin user in Supabase.
Usage: python create_admin.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

url = os.getenv("SUPABASE_URL")
service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
admin_email = os.getenv("ADMIN_EMAIL", "").strip()
admin_password = os.getenv("ADMIN_PASSWORD", "").strip()

if not all([url, service_key, admin_email, admin_password]):
    print("ERROR: Missing env vars. Check SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, ADMIN_EMAIL, ADMIN_PASSWORD in .env")
    exit(1)

supabase = create_client(url, service_key)

# Step 1: Create auth user (or get existing)
print(f"Creating auth user for {admin_email}...")
try:
    result = supabase.auth.admin.create_user({
        "email": admin_email,
        "password": admin_password,
        "email_confirm": True,
        "user_metadata": {"full_name": "Admin", "role": "admin"}
    })
    user_id = result.user.id
    print(f"Auth user created: {user_id}")
except Exception as e:
    if "already been registered" in str(e) or "already exists" in str(e):
        # User exists — fetch their ID
        print("Auth user already exists, fetching ID...")
        users = supabase.auth.admin.list_users()
        user = next((u for u in users if u.email == admin_email), None)
        if not user:
            print(f"ERROR: Could not find auth user with email {admin_email}")
            exit(1)
        user_id = user.id
        print(f"Found existing auth user: {user_id}")
    else:
        print(f"ERROR creating auth user: {e}")
        exit(1)

# Step 2: Upsert admin profile
print("Upserting admin profile in profiles table...")
try:
    supabase.table("profiles").upsert({
        "id": user_id,
        "email": admin_email,
        "full_name": "Admin",
        "role": "admin"
    }).execute()
    print("Admin profile created/updated successfully.")
    print(f"\nAdmin login credentials:")
    print(f"  Email:    {admin_email}")
    print(f"  Password: {admin_password}")
    print(f"\nUse these at /admin/login")
except Exception as e:
    print(f"ERROR upserting profile: {e}")
    exit(1)
