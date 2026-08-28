from datetime import timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import User, Session, Booking


class SessionAPITestCase(TestCase):
    """
    Test suite for Session CRUD, catalog listing, detail views, and Creator ownership authorization.
    """

    def setUp(self):
        self.creator_a = User.objects.create_user(
            username='creator_a',
            email='creator_a@ahoum.com',
            is_creator=True
        )
        self.creator_b = User.objects.create_user(
            username='creator_b',
            email='creator_b@ahoum.com',
            is_creator=True
        )
        self.regular_user = User.objects.create_user(
            username='regular_user',
            email='regular@ahoum.com',
            is_creator=False
        )

        self.token_creator_a = str(RefreshToken.for_user(self.creator_a).access_token)
        self.token_creator_b = str(RefreshToken.for_user(self.creator_b).access_token)
        self.token_user = str(RefreshToken.for_user(self.regular_user).access_token)

        self.session_a = Session.objects.create(
            creator=self.creator_a,
            title='Morning Flow with Creator A',
            description='Mindful movement.',
            starts_at=timezone.now() + timedelta(days=2),
            capacity=10,
            location='Online'
        )

    def test_unauthenticated_session_catalog_returns_401(self):
        client = APIClient()
        response = client.get(reverse('session_list_create'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error']['code'], 'not_authenticated')

    def test_authenticated_user_can_list_sessions(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_user}')
        response = client.get(reverse('session_list_create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Morning Flow with Creator A')

    def test_authenticated_user_can_view_session_detail(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_user}')
        response = client.get(reverse('session_detail', args=[self.session_a.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.session_a.id)
        self.assertEqual(response.data['remaining_seats'], 10)
        self.assertEqual(response.data['active_booking_count'], 0)

    def test_creator_can_create_session(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_creator_a}')
        payload = {
            'title': 'New Breathwork Circle',
            'description': 'Pranayama deep dive.',
            'starts_at': (timezone.now() + timedelta(days=5)).isoformat(),
            'capacity': 15,
            'location': 'Studio B'
        }
        response = client.post(reverse('session_list_create'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'New Breathwork Circle')
        self.assertEqual(response.data['creator']['id'], self.creator_a.id)
        self.assertEqual(response.data['capacity'], 15)

    def test_regular_user_cannot_create_session_returns_403(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_user}')
        payload = {
            'title': 'Unauthorized Session',
            'starts_at': (timezone.now() + timedelta(days=1)).isoformat(),
            'capacity': 5
        }
        response = client.post(reverse('session_list_create'), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error']['code'], 'permission_denied')

    def test_creator_can_update_own_session(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_creator_a}')
        payload = {'title': 'Updated Title', 'capacity': 20}
        response = client.patch(reverse('session_detail', args=[self.session_a.id]), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Title')
        self.assertEqual(response.data['capacity'], 20)

    def test_creator_cannot_update_another_creator_session_returns_403(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_creator_b}')
        payload = {'title': 'Malicious Edit'}
        response = client.patch(reverse('session_detail', args=[self.session_a.id]), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_regular_user_cannot_update_session_returns_403(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_user}')
        payload = {'title': 'User Hack'}
        response = client.patch(reverse('session_detail', args=[self.session_a.id]), payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_creator_can_delete_own_session(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_creator_a}')
        response = client.delete(reverse('session_detail', args=[self.session_a.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Session.objects.filter(id=self.session_a.id).exists())

    def test_creator_cannot_delete_another_creator_session_returns_403(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_creator_b}')
        response = client.delete(reverse('session_detail', args=[self.session_a.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Session.objects.filter(id=self.session_a.id).exists())

    def test_regular_user_cannot_delete_session_returns_403(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_user}')
        response = client.delete(reverse('session_detail', args=[self.session_a.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_creator_can_view_own_session_bookings(self):
        Booking.objects.create(user=self.regular_user, session=self.session_a, status='active')
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_creator_a}')
        response = client.get(reverse('session_bookings_list', args=[self.session_a.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['user']['email'], self.regular_user.email)

    def test_other_creator_cannot_view_session_bookings_returns_403(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_creator_b}')
        response = client.get(reverse('session_bookings_list', args=[self.session_a.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_regular_user_cannot_view_session_bookings_returns_403(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_user}')
        response = client.get(reverse('session_bookings_list', args=[self.session_a.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_creator_toggle_retains_existing_session_ownership(self):
        """
        When a creator disables creator mode (is_creator=False), they cannot create new sessions,
        but they retain full ownership and update/delete permissions over previously created sessions.
        """
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_creator_a}')

        # 1. Switch is_creator to False
        patch_resp = client.patch(reverse('current_user_profile'), {'is_creator': False}, format='json')
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)
        self.assertFalse(patch_resp.data['is_creator'])

        # 2. User cannot create NEW sessions
        new_session_payload = {
            'title': 'Blocked Session Creation',
            'starts_at': (timezone.now() + timedelta(days=2)).isoformat(),
            'capacity': 5
        }
        create_resp = client.post(reverse('session_list_create'), new_session_payload, format='json')
        self.assertEqual(create_resp.status_code, status.HTTP_403_FORBIDDEN)

        # 3. User still owns and can UPDATE existing session_a
        update_resp = client.patch(
            reverse('session_detail', args=[self.session_a.id]),
            {'title': 'Still Owned By Creator A (Now Inactive)'},
            format='json'
        )
        self.assertEqual(update_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(update_resp.data['title'], 'Still Owned By Creator A (Now Inactive)')

        # 4. User still owns and can DELETE existing session_a
        del_resp = client.delete(reverse('session_detail', args=[self.session_a.id]))
        self.assertEqual(del_resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_session_delete_with_active_bookings_cascades_cleanly(self):
        """Deleting an owned session cleanly deletes the session and cascades associated bookings."""
        Booking.objects.create(user=self.regular_user, session=self.session_a, status='active')
        self.assertEqual(Booking.objects.filter(session=self.session_a).count(), 1)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_creator_a}')
        response = client.delete(reverse('session_detail', args=[self.session_a.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertFalse(Session.objects.filter(id=self.session_a.id).exists())
        self.assertEqual(Booking.objects.filter(session_id=self.session_a.id).count(), 0)


class BookingAPITestCase(TestCase):
    """
    Test suite for Booking operations: creation, edge case conflicts, listing, and cancellation.
    """

    def setUp(self):
        self.creator = User.objects.create_user(
            username='creator_user',
            email='creator@ahoum.com',
            is_creator=True
        )
        self.user_a = User.objects.create_user(username='user_a', email='user_a@ahoum.com')
        self.user_b = User.objects.create_user(username='user_b', email='user_b@ahoum.com')

        self.token_a = str(RefreshToken.for_user(self.user_a).access_token)
        self.token_b = str(RefreshToken.for_user(self.user_b).access_token)

        self.open_session = Session.objects.create(
            creator=self.creator,
            title='Sound Healing Bath',
            starts_at=timezone.now() + timedelta(days=2),
            capacity=2,
            location='Online'
        )

    def test_unauthenticated_booking_returns_401(self):
        client = APIClient()
        response = client.post(reverse('booking_create'), {'session_id': self.open_session.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)

    def test_booking_nonexistent_session_returns_404(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_a}')
        response = client.post(reverse('booking_create'), {'session_id': 99999}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
        self.assertEqual(response.data['error']['code'], 'session_not_found')

    def test_successful_booking(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_a}')
        response = client.post(reverse('booking_create'), {'session_id': self.open_session.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'active')
        self.assertEqual(response.data['session_id'], self.open_session.id)
        self.assertEqual(Booking.objects.filter(session=self.open_session, status='active').count(), 1)

    def test_double_booking_same_session_returns_409_already_booked(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_a}')
        resp1 = client.post(reverse('booking_create'), {'session_id': self.open_session.id}, format='json')
        self.assertEqual(resp1.status_code, status.HTTP_201_CREATED)

        # Attempt to book same session again
        resp2 = client.post(reverse('booking_create'), {'session_id': self.open_session.id}, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(resp2.data['error']['code'], 'ALREADY_BOOKED')

    def test_booking_full_session_returns_409_session_full(self):
        # Fill capacity (capacity = 2)
        Booking.objects.create(user=self.user_a, session=self.open_session, status='active')
        Booking.objects.create(user=self.user_b, session=self.open_session, status='active')

        user_c = User.objects.create_user(username='user_c', email='user_c@ahoum.com')
        token_c = str(RefreshToken.for_user(user_c).access_token)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token_c}')
        response = client.post(reverse('booking_create'), {'session_id': self.open_session.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['error']['code'], 'SESSION_FULL')

    def test_booking_started_session_returns_409_session_already_started(self):
        started_session = Session.objects.create(
            creator=self.creator,
            title='Past Session',
            starts_at=timezone.now() - timedelta(hours=2),
            capacity=10
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_a}')
        response = client.post(reverse('booking_create'), {'session_id': started_session.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['error']['code'], 'SESSION_ALREADY_STARTED')

    def test_session_booking_exact_start_boundary_rejected(self):
        """A session with starts_at <= timezone.now() is strictly rejected."""
        exact_session = Session.objects.create(
            creator=self.creator,
            title='Exact Boundary Session',
            starts_at=timezone.now() - timedelta(seconds=2),
            capacity=5
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_a}')
        response = client.post(reverse('booking_create'), {'session_id': exact_session.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['error']['code'], 'SESSION_ALREADY_STARTED')

    def test_user_bookings_mine_split_active_and_past(self):
        future_session = Session.objects.create(
            creator=self.creator,
            title='Future Session',
            starts_at=timezone.now() + timedelta(days=2),
            capacity=5
        )
        past_session = Session.objects.create(
            creator=self.creator,
            title='Past Session',
            starts_at=timezone.now() - timedelta(days=1),
            capacity=5
        )

        b1 = Booking.objects.create(user=self.user_a, session=future_session, status='active')
        b2 = Booking.objects.create(user=self.user_a, session=past_session, status='active')

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_a}')
        response = client.get(reverse('user_bookings_mine'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['active']), 1)
        self.assertEqual(response.data['active'][0]['id'], b1.id)
        self.assertEqual(len(response.data['past']), 1)
        self.assertEqual(response.data['past'][0]['id'], b2.id)

    def test_booking_cancellation_by_owner_frees_seat(self):
        single_seat_session = Session.objects.create(
            creator=self.creator,
            title='1-Seat Workshop',
            starts_at=timezone.now() + timedelta(days=3),
            capacity=1
        )
        booking = Booking.objects.create(user=self.user_a, session=single_seat_session, status='active')

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_a}')
        response = client.delete(reverse('booking_cancel', args=[booking.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        booking.refresh_from_db()
        self.assertEqual(booking.status, 'cancelled')

        # Now user_b can book the freed seat
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_b}')
        resp_b = client.post(reverse('booking_create'), {'session_id': single_seat_session.id}, format='json')
        self.assertEqual(resp_b.status_code, status.HTTP_201_CREATED)

    def test_booking_cancellation_by_non_owner_returns_403(self):
        booking = Booking.objects.create(user=self.user_a, session=self.open_session, status='active')
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_b}')
        response = client.delete(reverse('booking_cancel', args=[booking.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'active')

    def test_user_can_rebook_after_own_cancellation(self):
        booking = Booking.objects.create(user=self.user_a, session=self.open_session, status='active')

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token_a}')
        # Cancel
        client.delete(reverse('booking_cancel', args=[booking.id]))

        # Re-book
        resp = client.post(reverse('booking_create'), {'session_id': self.open_session.id}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Booking.objects.filter(user=self.user_a, session=self.open_session, status='active').count(), 1)
