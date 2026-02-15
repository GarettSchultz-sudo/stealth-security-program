"""
Supabase Database Client
"""
from supabase import create_client
import os

_supabase = None

def get_supabase():
    """Get or create Supabase client singleton"""
    global _supabase
    if _supabase is None:
        _supabase = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_KEY"]
        )
    return _supabase
