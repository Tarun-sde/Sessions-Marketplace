import logging
from django.conf import settings
from google.oauth2 import id_token
from google.auth.transport import requests
from rest_framework.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)


def verify_google_id_token(token_str: str) -> dict:
    """
    Cryptographically verify a Google OAuth2 ID Token.
    Returns extracted claims dict: {'sub', 'email', 'name', 'picture'}.

    Supports a gated development authentication escape hatch ONLY when BOTH
    settings.AUTH_DEV_MODE is True and settings.DEBUG is True.
    """
    if not token_str or not isinstance(token_str, str):
        raise AuthenticationFailed("ID token is required and must be a string.", code="invalid_token")

    token_str = token_str.strip()

    # Development escape hatch (strictly gated to dev + debug mode)
    if token_str.startswith("devtoken:"):
        if getattr(settings, 'AUTH_DEV_MODE', False) and getattr(settings, 'DEBUG', False):
            email = token_str.split("devtoken:", 1)[1].strip()
            if not email or "@" not in email:
                raise AuthenticationFailed("Invalid development token format. Expected devtoken:<valid_email>.", code="invalid_token")
            return {
                "sub": f"dev-{email.lower()}",
                "email": email.lower(),
                "name": email.split("@")[0].replace('.', ' ').title(),
                "picture": ""
            }
        else:
            raise AuthenticationFailed("Development token authentication is disabled.", code="dev_auth_disabled")

    # Production cryptographic verification via google-auth
    client_id = getattr(settings, 'GOOGLE_CLIENT_ID', None) or None
    try:
        request = requests.Request()
        # If client_id is configured, verify audience matches
        claims = id_token.verify_oauth2_token(token_str, request, audience=client_id)

        # Verify issuer
        if claims.get('iss') not in ['accounts.google.com', 'https://accounts.google.com']:
            raise AuthenticationFailed("Invalid token issuer.", code="invalid_token")

        sub = claims.get('sub')
        email = claims.get('email')
        if not sub or not email:
            raise AuthenticationFailed("Google token missing required identity claims.", code="missing_claims")

        return {
            "sub": str(sub),
            "email": str(email).lower(),
            "name": claims.get('name', claims.get('email', '')),
            "picture": claims.get('picture', '')
        }
    except ValueError as e:
        logger.warning(f"Google ID token verification failed: {e}")
        raise AuthenticationFailed(f"Invalid Google ID token: {str(e)}", code="invalid_token")
    except Exception as e:
        logger.error(f"Unexpected error during Google token verification: {e}")
        raise AuthenticationFailed("Authentication failed during token verification.", code="auth_failed")
