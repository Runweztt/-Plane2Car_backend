-- ============================================================
-- Create a test concierge directly in Supabase
-- Run in: Supabase Dashboard > SQL Editor > New Query
-- ============================================================

-- Step 1: Create concierge in Supabase auth
-- Go to Supabase Dashboard > Authentication > Users > Add user
-- Create with any email e.g. concierge@test.com and a password
-- Check "Auto Confirm User" then click Create

-- Step 2: After creating via Dashboard, run this to set concierge role
INSERT INTO profiles (id, full_name, email, role, verification_status)
SELECT
  id,
  'Test Concierge',
  email,
  'concierge',
  'pending'
FROM auth.users
WHERE email = 'concierge@test.com'
ON CONFLICT (id) DO UPDATE
  SET role = 'concierge', verification_status = 'pending';

-- Step 3: Confirm
SELECT id, email, role, verification_status FROM profiles WHERE email = 'concierge@test.com';
