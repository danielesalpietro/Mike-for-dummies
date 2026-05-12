// Runs inside mike_backend container:
// docker exec mike_backend node /app/test-profile-update.mjs <email> <password>

const [,, email, password] = process.argv;
if (!email || !password) {
  console.error('Usage: node test-profile-update.mjs <email> <password>');
  process.exit(1);
}

const BASE = 'http://supabase-api:8000';

// Step 1: sign in via GoTrue
const signIn = await fetch(`${BASE}/auth/v1/token?grant_type=password`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'apikey': process.env.SUPABASE_ANON_KEY || '' },
  body: JSON.stringify({ email, password }),
});
const session = await signIn.json();
if (!session.access_token) {
  console.error('Sign-in failed:', JSON.stringify(session));
  process.exit(1);
}
console.log('✓ Signed in, user id:', session.user?.id);

// Step 2: update display_name via PostgREST with user JWT
const update = await fetch(`${BASE}/rest/v1/user_profiles?user_id=eq.${session.user.id}`, {
  method: 'PATCH',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${session.access_token}`,
    'apikey': process.env.SUPABASE_ANON_KEY || '',
    'Prefer': 'return=representation',
  },
  body: JSON.stringify({ display_name: 'CLI Test Name', updated_at: new Date().toISOString() }),
});
const result = await update.text();
console.log('PATCH status:', update.status);
console.log('PATCH body:', result);
