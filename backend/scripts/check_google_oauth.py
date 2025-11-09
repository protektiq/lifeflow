#!/usr/bin/env python3
"""Diagnostic script to check Google OAuth configuration"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_env_file():
    """Check if .env file exists and has required variables"""
    env_path = Path(__file__).parent.parent / ".env"
    
    if not env_path.exists():
        print("❌ ERROR: .env file not found in backend directory")
        return False
    
    print("✅ .env file found")
    
    # Read .env file
    env_vars = {}
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    # Check required variables
    required = ['GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET', 'GOOGLE_REDIRECT_URI']
    all_present = True
    
    for var in required:
        if var not in env_vars:
            print(f"❌ ERROR: {var} not found in .env file")
            all_present = False
        elif not env_vars[var]:
            print(f"❌ ERROR: {var} is empty in .env file")
            all_present = False
        else:
            # Show partial value for verification
            value = env_vars[var]
            if var == 'GOOGLE_CLIENT_ID':
                if '.apps.googleusercontent.com' in value:
                    print(f"✅ {var}: {value[:20]}...{value[-20:]}")
                else:
                    print(f"⚠️  WARNING: {var} doesn't look like a valid Google Client ID (should end with .apps.googleusercontent.com)")
                    print(f"   Value: {value[:50]}...")
            elif var == 'GOOGLE_CLIENT_SECRET':
                print(f"✅ {var}: {'*' * min(len(value), 20)}... (hidden)")
            else:
                print(f"✅ {var}: {value}")
    
    return all_present

def check_oauth_config():
    """Check if OAuth configuration can be loaded"""
    try:
        from app.config import settings
        
        print("\n📋 Checking OAuth configuration loading...")
        
        client_id = settings.GOOGLE_CLIENT_ID
        client_secret = settings.GOOGLE_CLIENT_SECRET
        redirect_uri = settings.GOOGLE_REDIRECT_URI
        
        if not client_id:
            print("❌ ERROR: GOOGLE_CLIENT_ID is empty")
            return False
        
        if not client_secret:
            print("❌ ERROR: GOOGLE_CLIENT_SECRET is empty")
            return False
        
        if not redirect_uri:
            print("❌ ERROR: GOOGLE_REDIRECT_URI is empty")
            return False
        
        print(f"✅ GOOGLE_CLIENT_ID loaded: {client_id[:20]}...{client_id[-20:]}")
        print(f"✅ GOOGLE_CLIENT_SECRET loaded: {'*' * 20}...")
        print(f"✅ GOOGLE_REDIRECT_URI: {redirect_uri}")
        
        # Validate Client ID format
        if not client_id.endswith('.apps.googleusercontent.com'):
            print("⚠️  WARNING: Client ID doesn't match expected format")
            print("   Expected format: *.apps.googleusercontent.com")
        
        # Validate redirect URI format
        if not redirect_uri.startswith('http'):
            print("⚠️  WARNING: Redirect URI should start with http:// or https://")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR loading configuration: {str(e)}")
        return False

def check_oauth_flow():
    """Check if OAuth flow can be created"""
    try:
        from app.api.auth import get_google_flow
        
        print("\n📋 Checking OAuth flow creation...")
        
        redirect_uri = "http://localhost:8000/api/auth/google/callback"
        flow = get_google_flow(redirect_uri)
        
        print("✅ OAuth flow created successfully")
        print(f"   Scopes: {flow.scope}")
        print(f"   Redirect URI: {redirect_uri}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR creating OAuth flow: {str(e)}")
        print(f"   This might indicate invalid credentials")
        return False

def main():
    print("=" * 60)
    print("Google OAuth Configuration Diagnostic")
    print("=" * 60)
    
    # Check .env file
    print("\n1️⃣ Checking .env file...")
    env_ok = check_env_file()
    
    if not env_ok:
        print("\n❌ Please fix .env file issues before continuing")
        return 1
    
    # Check configuration loading
    config_ok = check_oauth_config()
    
    if not config_ok:
        print("\n❌ Configuration loading failed")
        return 1
    
    # Check OAuth flow
    flow_ok = check_oauth_flow()
    
    if not flow_ok:
        print("\n❌ OAuth flow creation failed")
        print("\n💡 TROUBLESHOOTING:")
        print("   1. Verify your GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in Google Cloud Console")
        print("   2. Make sure the OAuth client is enabled")
        print("   3. Check that the redirect URI matches exactly:")
        print("      http://localhost:8000/api/auth/google/callback")
        print("   4. Ensure Google Calendar API is enabled in your Google Cloud project")
        return 1
    
    print("\n" + "=" * 60)
    print("✅ All checks passed!")
    print("=" * 60)
    print("\n💡 If you're still getting 'invalid_client' error:")
    print("   1. Go to Google Cloud Console > APIs & Services > Credentials")
    print("   2. Find your OAuth 2.0 Client ID")
    print("   3. Verify the Client ID matches your .env file exactly")
    print("   4. Check that the redirect URI is added:")
    print("      http://localhost:8000/api/auth/google/callback")
    print("   5. Make sure the OAuth consent screen is configured")
    print("   6. If using a test app, add your email as a test user")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

