"""
Supabase client singletons.

- `supabase_anon`  → public anon client (used on behalf of the authenticated user, respects RLS)
- `supabase_admin` → service-role client (bypasses RLS; used ONLY in backend for skill-profile writes)
"""

from supabase import create_client, Client
from app.config import SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY

# Anon/public client (authenticate users; respects RLS)
supabase_anon: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# Service-role admin client (bypasses RLS — use only in trusted backend code)
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
