-- ============================================================
-- Diagnostic — run in Supabase SQL Editor
-- ============================================================

-- 1. Check if user exists in auth and their state
SELECT
  id,
  email,
  email_confirmed_at,
  created_at,
  encrypted_password IS NOT NULL AS has_password,
  raw_user_meta_data
FROM auth.users
WHERE email = 'amarikwat@gmail.com';

-- 2. Check if profile exists and role
SELECT id, email, role, verification_status
FROM profiles
WHERE email = 'amarikwat@gmail.com';

-- 3. Count all users in auth
SELECT COUNT(*) AS total_auth_users FROM auth.users;

-- 4. Count all profiles
SELECT COUNT(*) AS total_profiles FROM profiles;
