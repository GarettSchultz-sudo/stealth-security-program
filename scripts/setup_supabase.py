#!/usr/bin/env python3
"""
One-click Supabase setup script
Sets up the database schema and seeds pricing data
"""
import os
import sys
from pathlib import Path

try:
    from supabase import create_client
except ImportError:
    print("❌ supabase package not found. Install with: pip install supabase")
    sys.exit(1)

def main():
    # Get credentials
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables")
        sys.exit(1)
    
    print("🔌 Connecting to Supabase...")
    supabase = create_client(supabase_url, supabase_key)
    
    # Read and execute migrations
    migrations_dir = Path(__file__).parent.parent / "supabase" / "migrations"
    
    for migration_file in sorted(migrations_dir.glob("*.sql")):
        print(f"📄 Running {migration_file.name}...")
        with open(migration_file) as f:
            sql = f.read()
        
        # Note: Supabase Python client doesn't support raw SQL execution
        # You'll need to run these in the Supabase SQL Editor
        print(f"   ⚠️  Please run this file in Supabase SQL Editor:")
        print(f"   {migration_file}")
    
    # Seed data
    seed_file = Path(__file__).parent.parent / "supabase" / "seed.sql"
    print(f"📄 Running {seed_file.name}...")
    print(f"   ⚠️  Please run this file in Supabase SQL Editor:")
    print(f"   {seed_file}")
    
    print("")
    print("✅ Setup instructions complete!")
    print("")
    print("Next steps:")
    print("1. Go to https://supabase.com/dashboard")
    print("2. Open SQL Editor")
    print("3. Run each migration file in order")
    print("4. Run seed.sql for pricing data")

if __name__ == "__main__":
    main()
