# Google OAuth Integration - Backend Setup Guide

## Overview
Your backend now supports Google OAuth login and registration. This guide documents all the required setup steps.

## Required Environment Variables

Add these to your `.env` file:

```env
GOOGLE_CLIENT_IDS=your-client-id-1.apps.googleusercontent.com,your-client-id-2.apps.googleusercontent.com
```

**Note:** Multiple client IDs can be comma-separated (useful for dev, staging, and production environments).

## Getting Your Google Client ID

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select an existing one
3. Enable the **Google+ API**
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Choose **Web application**
6. Add authorized JavaScript origins:
   - `http://localhost:3000` (for local development)
   - `https://yourdomain.com` (for production)
7. Add authorized redirect URIs:
   - `http://localhost:3000/auth/google/callback` (for local development)
   - `https://yourdomain.com/auth/google/callback` (for production)
8. Copy the **Client ID** and add it to your `.env` file

## Backend Changes

### 1. Database Schema
- `password_hash` column is now **nullable** to support Google-only accounts
- Migration `0005_google_oauth_support.py` makes this change
- Existing users retain their password hashes

### 2. New Dependencies
- `google-auth-oauthlib==1.2.0` added to `requirements.txt`
- Provides Google OAuth 2.0 token verification

### 3. Updated User Model
- `google_sub` field stores Google's unique user identifier
- Prevents account linking confusion if user tries to sign in with different Google accounts
- Automatically populated on first Google sign-in

### 4. Authentication Endpoints

#### POST /api/google (Login + Registration)
**Request:**
```json
{
  "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjFjNzg4..."
}
```

**Behavior:**
- ✅ Validates ID token with Google's servers
- ✅ Extracts: email, name, picture (avatar)
- ✅ Creates user on first sign-in (auto-registration)
- ✅ Links existing users if email matches
- ✅ Returns JWT token + full user profile

**Response:**
```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "John Doe",
    "avatar_url": "https://...",
    "role": "USER",
    "verification_status": "NOT_APPLIED",
    "analytics_specialties": [],
    "primary_analytics_topic_id": null,
    "created_at": "2026-09-04T12:00:00Z"
  },
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 5. Security Validations
The backend performs these security checks:

1. **Token Signature** - Verifies token is signed by Google
2. **Issuer Check** - Ensures `iss` is `accounts.google.com` or `https://accounts.google.com`
3. **Audience Check** - Ensures `aud` matches one of your configured `GOOGLE_CLIENT_IDS`
4. **Email Verification** - Ensures `email_verified` is true
5. **Token Expiry** - Uses 10-second clock skew for distributed systems

### 6. Password Handling
- **Google-only accounts** have NULL password_hash
- **Regular login route** (`POST /api/login`) checks for NULL password and rejects
- **Google OAuth accounts** cannot use the password login
- Users can still register with email/password separately

### 7. Admin Session Protection
- Admin console (`POST /api/admin/session`) also validates password_hash is not NULL
- Prevents Google-only admins from accessing admin console
- Admin accounts must have passwords set

## Database Migration

Run migrations to apply the schema change:

```bash
# Using Alembic
alembic upgrade head
```

Or via Docker:
```bash
docker-compose exec backend alembic upgrade head
```

## Testing the Implementation

### 1. Test Registration via Google
```bash
curl -X POST http://localhost:8000/api/google \
  -H "Content-Type: application/json" \
  -d '{"id_token":"YOUR_GOOGLE_ID_TOKEN"}'
```

### 2. Test Existing User Sign-In
Sign in with a new Google account, then try signing in with a different Google account but the same email (should fail with 409 error).

### 3. Test Email Conflict
- Register user with email: `test@example.com` via Google
- Try to register same email via Google with different account (should link to existing user)

## Frontend Integration Requirements

Your frontend needs to:

1. Get the `id_token` from Google Sign-In library
2. Send it to `POST /api/google`
3. Store the returned JWT `token` for subsequent API calls
4. Include token in `Authorization: Bearer {token}` header

**Frontend Code Example:**
```javascript
// After Google Sign-In callback
const response = await fetch('/api/google', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ id_token: googleIdToken })
});

const { user, token } = await response.json();
localStorage.setItem('auth_token', token);
```

## Troubleshooting

### Error: "Google sign-in is not configured"
- Ensure `GOOGLE_CLIENT_IDS` is set in `.env`
- Restart the backend service

### Error: "Google identity could not be verified"
- Client ID doesn't match `GOOGLE_CLIENT_IDS`
- Token is from wrong Google project
- Check Google Cloud Console credentials

### Error: "A verified Google account is required"
- User's Google account email is not verified
- Ensure user verified their email in Google Account Settings

### Error: "This email is linked to another Google identity"
- User with this email already linked to different Google `sub`
- This prevents account takeover via email spoofing

## Key Security Features

✅ **Token validation against Google's servers** - Not client-side only  
✅ **Email verification requirement** - Only verified Google emails allowed  
✅ **Account linking protection** - Prevents unauthorized linking  
✅ **Rate limiting** - Same as password login (8 attempts/minute)  
✅ **Automatic user creation** - Seamless first-time experience  
✅ **Nullable passwords** - Google users aren't forced to set passwords  

## Files Changed

- `app/models/models.py` - Made `password_hash` nullable
- `app/core/config.py` - Added `GOOGLE_CLIENT_IDS` setting
- `app/api/routes/auth.py` - Updated login/admin-session to handle NULL passwords
- `requirements.txt` - Added `google-auth-oauthlib`
- `.env.example` - Documented `GOOGLE_CLIENT_IDS` setup
- `alembic/versions/0005_google_oauth_support.py` - Database migration

## Next Steps

1. Set `GOOGLE_CLIENT_IDS` in your `.env` file
2. Run database migrations: `alembic upgrade head`
3. Restart the backend
4. Update frontend to send Google ID tokens to `/api/google`
5. Test the full flow end-to-end
