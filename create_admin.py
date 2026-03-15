"""
One-time setup script — creates the admin auth user and profile in Supabase.
Run once from the backend folder:  python create_admin.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

url = os.getenv("SUPABASE_URL")
service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
anon_key = os.getenv("SUPABASE_KEY")
admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
admin_password = os.getenv("ADMIN_PASSWORD", "").strip()

if not all([url, service_key, anon_key, admin_email, admin_password]):
    print("ERROR: Missing env vars. Check .env has SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_KEY, ADMIN_EMAIL, ADMIN_PASSWORD")
    exit(1)

supabase_admin = create_client(url, service_key)
supabase_anon  = create_client(url, anon_key)

user_id = None

# Step 1: Try to create the auth user
print(f"Creating auth user for {admin_email} ...")
try:
    result = supabase_admin.auth.admin.create_user({
        "email": admin_email,
        "password": admin_password,
        "email_confirm": True,
        "user_metadata": {"full_name": "Admin", "role": "admin"}
    })
    user_id = result.user.id
    print(f"Auth user created: {user_id}")
except Exception as e:
    print(f"Create user failed: {e}")

# Step 2: If creation failed, sign in to get the existing user ID
if not user_id:
    print("Trying to sign in to retrieve existing user ID ...")
    try:
        session = supabase_anon.auth.sign_in_with_password({
            "email": admin_email,
            "password": admin_password
        })
        user_id = session.user.id
        print(f"Found existing auth user: {user_id}")
    except Exception as e:
        print(f"Sign-in also failed: {e}")

# Step 3: If we still don't have a user ID, ask the user to paste it manually
if not user_id:
    print("\nCould not retrieve user ID automatically.")
    print("Go to: Supabase Dashboard → Authentication → Users")
    print(f"Find the user with email: {admin_email}")
    print("Copy the UUID from the 'UID' column and paste it below.")
    user_id = input("Paste UUID here: ").strip()
    if not user_id:
        print("No UUID provided. Exiting.")
        exit(1)

# Step 4: Upsert the admin profile
print(f"Upserting admin profile (id={user_id}) ...")
try:
    supabase_admin.table("profiles").upsert({
        "id": user_id,
        "email": admin_email,
        "full_name": "Admin",
        "role": "admin"
    }).execute()
    print("Admin profile created/updated successfully.")
    print(f"\nAdmin login ready:")
    print(f"  Email:    {admin_email}")
    print(f"  Password: {admin_password}")
    print(f"  URL:      http://localhost:5173/admin/login")
except Exception as e:
    print(f"ERROR upserting profile: {e}")
    exit(1)
