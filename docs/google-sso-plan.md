# Future Feature: Google SSO Integration

This document outlines the strategy for integrating Google Single Sign-On (SSO) using Amazon Cognito's Hosted UI.

## Objective
Provide a secure, easy-to-implement login flow where users are redirected to AWS to authenticate via Google and are then returned to the 'set' app with a valid JWT.

## Infrastructure Requirements (AWS Side)
1.  **Google Cloud Console**: Create OAuth 2.0 Client IDs to get a Client ID and Secret.
2.  **Amazon Cognito**: 
    *   Add Google as a Federated Identity Provider in the User Pool.
    *   Enable the Hosted UI.
    *   Configure Callback/Sign-out URLs.

## Implementation Details

### Frontend (React)
- **Login Redirect**: Replace or augment the local login form with a "Login with Google" button that redirects to the Cognito Hosted UI endpoint.
- **Token Capture**: Use a `useEffect` hook to detect the redirect back (checking for `#id_token=` or `code=` in the URL), extract the JWT, and store it in `localStorage`.

### Backend (FastAPI)
- **Token Validation**: The existing `get_current_user` dependency is already built to handle JWTs. It will need to fetch the JWKS from Cognito's public endpoint to verify the signature of the Google-issued Cognito token.

## Local Development vs. Production
- **Local**: Continue using `MOCK_AUTH=true` with the custom login screen.
- **Production**: Use real Cognito Hosted UI integration.
