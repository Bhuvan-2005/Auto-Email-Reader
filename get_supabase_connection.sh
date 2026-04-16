#!/bin/bash
# Quick setup script for Supabase connection

echo "Getting Supabase PostgreSQL connection string..."
echo ""
echo "1. Go to: https://supabase.com/dashboard/project/owiqyvtewcuhxthaycse/settings/database"
echo "2. Scroll to 'Connection string' section"
echo "3. Click 'URI' tab"
echo "4. Copy the connection string (starts with postgresql://)"
echo "5. It should look like:"
echo "   postgresql://postgres.owiqyvtewcuhxthaycse:[YOUR-PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"
echo ""
echo "Then run:"
echo "  export DATABASE_URL='<paste-connection-string-here>'"
echo ""
echo "To test connection:"
echo "  python3 -c 'from src.database_adapter import init_database; init_database()'"
