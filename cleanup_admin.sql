-- ============================================================
-- Step 1: Clean up corrupted admin user
-- Run in: Supabase Dashboard > SQL Editor > New Query
-- ============================================================

DELETE FROM profiles WHERE email = 'amarikwat@gmail.com';
DELETE FROM auth.users WHERE email = 'amarikwat@gmail.com';

-- ============================================================
-- Step 2: Confirm cleanup worked (both should return 0 rows)
-- ============================================================

SELECT * FROM profiles WHERE email = 'amarikwat@gmail.com';
SELECT * FROM auth.users WHERE email = 'amarikwat@gmail.com';
