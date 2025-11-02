# gfauth - Google OAuth Authentication

Provides Google OAuth authentication for admin access at https://www.givefood.org.uk/auth/

## Overview

gfauth handles authentication for Give Food's administrative interfaces using Google OAuth 2.0. It provides a secure, single sign-on experience for Give Food staff to access the admin tools without managing separate passwords.

**Live URL**: https://www.givefood.org.uk/auth/

## Features

### Google OAuth Integration
- **Google Sign-In**: One-click authentication with Google accounts
- **OAuth 2.0**: Industry-standard authentication protocol
- **Token Verification**: Server-side verification of Google ID tokens
- **Session Management**: Stores authenticated user data in Django sessions

### Security
- **CSRF Exempt**: Uses Google's secure token mechanism instead
- **Never Cached**: Authentication pages are never cached
- **Token Validation**: Verifies tokens against Google's servers
- **Session-Based**: Maintains user state across requests

## URL Structure

### Authentication Endpoints
- `/auth/` - Sign-in page with Google authentication button
- `/auth/receiver/` - OAuth callback receiver (processes Google token)
- `/auth/sign-out/` - Sign-out endpoint (clears session)

## Authentication Flow

### Sign-In Process
1. User visits `/auth/` and sees Google Sign-In button
2. User clicks button and authenticates with Google
3. Google returns a credential token to the browser
4. Browser POSTs token to `/auth/receiver/`
5. Server verifies token with Google
6. User data stored in Django session
7. User redirected back to sign-in page (now showing authenticated state)

### Sign-Out Process
1. User accesses `/auth/sign-out/`
2. Session data is cleared
3. User redirected to sign-in page

## Technical Details

### Google OAuth Configuration
- **Client ID**: `927281004707-tboi1tsphl4bgtqn72e76rmc7r2q22tk.apps.googleusercontent.com`
- **Provider**: Google OAuth 2.0
- **Token Type**: ID tokens (not access tokens)

### Session Storage
User data stored in `request.session['user_data']` includes:
- User email
- User name
- Google user ID
- Profile picture URL
- Other profile information from Google

### Security Decorators
- `@csrf_exempt` - OAuth receiver doesn't use CSRF tokens
- `@never_cache` - All auth pages are never cached for security

### Token Verification
Uses `google.oauth2.id_token.verify_oauth2_token()` to:
- Validate token signature
- Check token expiration
- Verify token audience (client ID)
- Extract user information

### Error Handling
- Invalid tokens return HTTP 403 Forbidden
- Failed verification returns 403
- No exception details exposed to users

## Integration with Other Apps

### gfadmin Integration
The admin app (`gfadmin`) uses authentication via the `LoginRequiredAccess` middleware, which checks for authenticated sessions created by gfauth.

### Middleware
The `LoginRequiredAccess` middleware in `givefood.middleware` enforces authentication for admin pages by:
1. Checking for `user_data` in session
2. Redirecting to `/auth/` if not authenticated
3. Allowing access if authenticated

## Templates

Located in `templates/auth/`:
- `sign_in.html` - Authentication page with Google Sign-In button

## User Experience

### For Staff Members
1. Navigate to any admin page
2. Automatically redirected to `/auth/` if not signed in
3. Click "Sign in with Google" button
4. Authenticate with authorized Google account
5. Automatically redirected back to admin area

### Authorized Users
Only Google accounts authorized by Give Food administrators can access the admin interface. The list of authorized accounts is managed separately from this authentication system.

## Development Notes

### Local Development
For local development, ensure:
- Google OAuth client ID is configured
- Localhost is added to authorized origins in Google Console
- Session backend is properly configured in Django settings

### Testing
Authentication flows cannot be easily unit tested due to Google OAuth dependency. Manual testing required:
1. Test sign-in with valid Google account
2. Test sign-out
3. Test access to protected pages
4. Test invalid/expired tokens

### Security Considerations
- Never expose client secrets in code
- All authentication pages use HTTPS in production
- Sessions should use secure cookies in production
- Consider session timeout for inactive users

## Related Apps

- **gfadmin** - Primary consumer of authentication
- **givefood** - Contains `LoginRequiredAccess` middleware

## Dependencies

### Python Packages
- `google-auth` - Google authentication library
- `google.oauth2` - OAuth 2.0 support
- `google.auth.transport` - HTTP transport for requests

### External Services
- **Google OAuth 2.0** - Authentication provider
- **Google APIs** - Token verification

## Contact

For authentication issues or access requests:
- Email: mail@givefood.org.uk
