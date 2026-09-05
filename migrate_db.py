#!/usr/bin/env python3
"""
Database Migration Script
Run this script to migrate existing database to new schema
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data.database import migrate_database

if __name__ == "__main__":
    print("Running database migration...")
    try:
        migrate_database()
        print("Migration completed successfully!")
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)