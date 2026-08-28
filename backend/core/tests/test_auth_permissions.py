from unittest.mock import patch
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import User


class AuthAndProfileAPITestCase(TestCase):
    """
    Automated test suite for Phase 2:
    - Google OAuth ID token verification (with mocking)
    - Development authentication escape hatch gating
    - JWT issuance and refresh
    - Authenticated /api/me/ profile retrieval and partial update
    - Protection of immutable and internal fields
    - is_creator role toggle transitions
    - Idempotent OAuth identity lookup (no duplicate users)
    """

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@ahoum.com',
            first_name='Test',
            last_name='User',
            bio='Software engineer',
            avatar_url='https://example.com/avatar.png',
            is_creator=False
        )
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.refresh_token = str(refresh)

    def test_unauthenticated_profile_returns_401(self):
        """GET /api/me/ without credentials returns 401 Unauthorized."""
        response = self.client.get(reverse('current_user_profile'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error']['code'], 'not_authenticated')

    def test_invalid_jwt_returns_401(self):
        """GET /api/me/ with malformed or invalid Bearer token returns 401."""
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid.jwt.token')
        response = self.client.get(reverse('current_user_profile'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error']['code'], 'token_not_valid')

    def test_valid_jwt_profile_access(self):
        """GET /api/me/ with valid Bearer token returns current user profile."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.get(reverse('current_user_profile'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.user.id)
        self.assertEqual(response.data['email'], 'testuser@ahoum.com')
        self.assertEqual(response.data['name'], 'Test User')
        self.assertEqual(response.data['bio'], 'Software engineer')
        self.assertEqual(response.data['is_creator'], False)
        # Verify internal fields are NOT leaked
        self.assertNotIn('password', response.data)
        self.assertNotIn('oauth_sub', response.data)

    def test_profile_update_allowed_fields(self):
        """PATCH /api/me/ updates only allowed profile fields (name, bio, avatar_url, is_creator)."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        payload = {
            'name': 'Updated Name',
            'bio': 'Updated bio content',
            'avatar_url': 'https://example.com/new-avatar.png',
            'is_creator': True
        }
        response = self.client.patch(reverse('current_user_profile'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Name')
        self.assertEqual(response.data['bio'], 'Updated bio content')
        self.assertEqual(response.data['is_creator'], True)

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
        self.assertEqual(self.user.last_name, 'Name')
        self.assertEqual(self.user.bio, 'Updated bio content')
        self.assertTrue(self.user.is_creator)

    def test_profile_update_protected_fields_ignored(self):
        """PATCH /api/me/ must NOT allow modifying id, email, oauth_provider, oauth_sub, password."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        original_id = self.user.id
        original_email = self.user.email

        payload = {
            'id': 99999,
            'email': 'hacked@evil.com',
            'oauth_provider': 'custom_hacker',
            'oauth_sub': 'fake_sub',
            'password': 'hacked_password',
            'bio': 'Safe bio change'
        }
        response = self.client.patch(reverse('current_user_profile'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertEqual(self.user.id, original_id)
        self.assertEqual(self.user.email, original_email)
        self.assertEqual(self.user.oauth_provider, '')
        self.assertEqual(self.user.oauth_sub, '')
        self.assertEqual(self.user.bio, 'Safe bio change')

    def test_is_creator_toggle_transition(self):
        """Any user can become a creator (is_creator=True) and toggle back to False."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

        # Toggle to True
        resp1 = self.client.patch(reverse('current_user_profile'), {'is_creator': True}, format='json')
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)
        self.assertTrue(resp1.data['is_creator'])

        # Toggle back to False
        resp2 = self.client.patch(reverse('current_user_profile'), {'is_creator': False}, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertFalse(resp2.data['is_creator'])

    @override_settings(AUTH_DEV_MODE=True, DEBUG=True)
    def test_dev_authentication_success(self):
        """When AUTH_DEV_MODE=True & DEBUG=True, devtoken:<email> authenticates successfully."""
        response = self.client.post(
            reverse('google_auth'),
            {'id_token': 'devtoken:devuser@ahoum.com'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['email'], 'devuser@ahoum.com')

        # Check DB user was created with dev identity
        dev_user = User.objects.get(email='devuser@ahoum.com')
        self.assertEqual(dev_user.oauth_provider, 'google')
        self.assertEqual(dev_user.oauth_sub, 'dev-devuser@ahoum.com')

    @override_settings(AUTH_DEV_MODE=True, DEBUG=True)
    def test_repeated_dev_authentication_idempotent(self):
        """Repeated dev logins with the same email return the existing user without duplicate rows."""
        self.client.post(reverse('google_auth'), {'id_token': 'devtoken:repeat@ahoum.com'}, format='json')
        initial_count = User.objects.filter(email='repeat@ahoum.com').count()
        self.assertEqual(initial_count, 1)

        # Login again
        resp2 = self.client.post(reverse('google_auth'), {'id_token': 'devtoken:repeat@ahoum.com'}, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        final_count = User.objects.filter(email='repeat@ahoum.com').count()
        self.assertEqual(final_count, 1)

    @override_settings(AUTH_DEV_MODE=False, DEBUG=True)
    def test_dev_authentication_rejected_when_auth_dev_mode_false(self):
        """When AUTH_DEV_MODE=False (even if DEBUG=True), devtoken:<email> is rejected with 401."""
        response = self.client.post(
            reverse('google_auth'),
            {'id_token': 'devtoken:devuser@ahoum.com'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['error']['code'], 'dev_auth_disabled')

    @override_settings(AUTH_DEV_MODE=True, DEBUG=False)
    def test_dev_authentication_rejected_when_debug_false(self):
        """When DEBUG=False (production mode), devtoken:<email> is strictly rejected with 401."""
        response = self.client.post(
            reverse('google_auth'),
            {'id_token': 'devtoken:devuser@ahoum.com'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['error']['code'], 'dev_auth_disabled')

    @override_settings(AUTH_DEV_MODE=True, DEBUG=True)
    def test_dev_authentication_invalid_email_format(self):
        """Malformed devtoken (missing @) returns 401."""
        response = self.client.post(
            reverse('google_auth'),
            {'id_token': 'devtoken:notanemail'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['error']['code'], 'invalid_token')

    @patch('core.oauth.id_token.verify_oauth2_token')
    def test_google_oauth_verification_success(self, mock_verify):
        """Verified Google ID token returns JWT and creates user profile."""
        mock_verify.return_value = {
            'iss': 'https://accounts.google.com',
            'sub': 'google-uid-123456789',
            'email': 'googleuser@gmail.com',
            'name': 'Google User',
            'picture': 'https://lh3.googleusercontent.com/a/photo.jpg'
        }

        response = self.client.post(
            reverse('google_auth'),
            {'id_token': 'real.google.idtoken.payload'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['user']['email'], 'googleuser@gmail.com')
        self.assertEqual(response.data['user']['avatar_url'], 'https://lh3.googleusercontent.com/a/photo.jpg')

        created_user = User.objects.get(oauth_sub='google-uid-123456789')
        self.assertEqual(created_user.oauth_provider, 'google')
        self.assertEqual(created_user.email, 'googleuser@gmail.com')

    @patch('core.oauth.id_token.verify_oauth2_token')
    def test_repeated_google_oauth_login_returns_same_user(self, mock_verify):
        """Subsequent logins with the same Google sub return the existing user without duplicates."""
        mock_verify.return_value = {
            'iss': 'accounts.google.com',
            'sub': 'google-uid-unique-999',
            'email': 'unique_google@gmail.com',
            'name': 'Unique Google',
            'picture': ''
        }

        self.client.post(reverse('google_auth'), {'id_token': 'token1'}, format='json')
        count_after_first = User.objects.filter(oauth_sub='google-uid-unique-999').count()
        self.assertEqual(count_after_first, 1)

        # Second login
        resp2 = self.client.post(reverse('google_auth'), {'id_token': 'token2'}, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        count_after_second = User.objects.filter(oauth_sub='google-uid-unique-999').count()
        self.assertEqual(count_after_second, 1)

    @patch('core.oauth.id_token.verify_oauth2_token')
    def test_google_oauth_verification_failure_returns_401(self, mock_verify):
        """Failed cryptographic verification returns clean 401 with standard error shape."""
        mock_verify.side_effect = ValueError("Token signature is invalid.")

        response = self.client.post(
            reverse('google_auth'),
            {'id_token': 'tampered.token.here'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error']['code'], 'invalid_token')

    def test_jwt_token_refresh_success(self):
        """POST /api/auth/refresh/ with valid refresh token returns new access token."""
        response = self.client.post(
            reverse('token_refresh'),
            {'refresh': self.refresh_token},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_jwt_token_refresh_invalid_token(self):
        """POST /api/auth/refresh/ with invalid refresh token returns 401."""
        response = self.client.post(
            reverse('token_refresh'),
            {'refresh': 'invalid.refresh.token'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
