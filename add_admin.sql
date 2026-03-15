-- ============================================================
-- Create Admin User from scratch
-- Run in: Supabase Dashboard > SQL Editor > New Query
-- Replace YOUR_PASSWORD_HERE with your actual password
-- ============================================================

-- Step 1: Create the user in Supabase auth
INSERT INTO auth.users (
  instance_id,
  id,
  aud,
  role,
  email,
  encrypted_password,
  email_confirmed_at,
  created_at,
  updated_at,
  raw_app_meta_data,
  raw_user_meta_data,
  is_super_admin
)
SELECT
  '00000000-0000-0000-0000-000000000000',
  gen_random_uuid(),
  'authenticated',
  'authenticated',
  'amarikwat@gmail.com',
  crypt('YOUR_PASSWORD_HERE', gen_salt('bf')),
  NOW(),
  NOW(),
  NOW(),
  '{"provider":"email","providers":["email"]}',
  '{"full_name":"Admin"}',
  FALSE
WHERE NOT EXISTS (
  SELECT 1 FROM auth.users WHERE email = 'amarikwat@gmail.com'
);

-- Step 2: Create or update the profile as admin
INSERT INTO profiles (id, full_name, email, role, verification_status)
SELECT
  id,
  'Admin',
  email,
  'admin',
  'approved'
FROM auth.users
WHERE email = 'amarikwat@gmail.com'
ON CONFLICT (id) DO UPDATE
  SET role = 'admin', verification_status = 'approved';

-- Step 3: Confirm everything
SELECT
  u.id,
  u.email,
  u.email_confirmed_at,
  p.role,
  p.verification_status
FROM auth.users u
JOIN profiles p ON p.id = u.id
WHERE u.email = 'amarikwat@gmail.com';
