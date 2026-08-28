import threading
from datetime import timedelta
from django.test import TransactionTestCase
from django.utils import timezone
from django.db import connection
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import User, Session, Booking


class BookingConcurrencyTestCase(TransactionTestCase):
    """
    Real PostgreSQL concurrency proof using TransactionTestCase and multi-threaded workers.
    Verifies that under simultaneous race conditions on the last available seat(s),
    PostgreSQL row-level locking (select_for_update) guarantees that:
    1. Exactly N bookings succeed where N = capacity.
    2. All excess concurrent requests are rejected cleanly with SESSION_FULL (409 Conflict).
    3. The database active booking count is exactly equal to capacity (0 oversold).
    """

    def setUp(self):
        self.creator = User.objects.create_user(
            username='concurrency_creator',
            email='concurrency_creator@ahoum.com',
            is_creator=True
        )

        # Create 10 distinct users and generate their JWT access tokens
        self.num_workers = 10
        self.users = []
        self.tokens = []
        for i in range(self.num_workers):
            user = User.objects.create_user(
                username=f'racer_user_{i}',
                email=f'racer_{i}@ahoum.com'
            )
            refresh = RefreshToken.for_user(user)
            self.users.append(user)
            self.tokens.append(str(refresh.access_token))

    def _execute_concurrent_booking_race(self, session, capacity):
        barrier = threading.Barrier(self.num_workers)
        results = []
        results_lock = threading.Lock()

        def worker_task(user_token):
            connection.close()
            client = APIClient()
            client.credentials(HTTP_AUTHORIZATION=f'Bearer {user_token}')

            # Wait at barrier until all 10 workers are ready
            barrier.wait()

            response = client.post(
                '/api/bookings/',
                {'session_id': session.id},
                format='json'
            )

            with results_lock:
                results.append({
                    'status_code': response.status_code,
                    'data': response.data
                })

            connection.close()

        threads = []
        for token in self.tokens:
            t = threading.Thread(target=worker_task, args=(token,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        connection.close()

        successes = [r for r in results if r['status_code'] == 201]
        conflicts = [r for r in results if r['status_code'] == 409]
        others = [r for r in results if r['status_code'] not in (201, 409)]

        self.assertEqual(len(results), self.num_workers)
        self.assertEqual(len(others), 0, f"No unexpected errors (500, 400) allowed. Found: {others}")
        self.assertEqual(len(successes), capacity, f"Exactly {capacity} bookings must succeed.")
        self.assertEqual(len(conflicts), self.num_workers - capacity, f"Remaining {self.num_workers - capacity} must receive 409 conflict.")

        for conflict in conflicts:
            self.assertIn('error', conflict['data'])
            self.assertEqual(conflict['data']['error']['code'], 'SESSION_FULL')

        active_db_bookings = Booking.objects.filter(session=session, status=Booking.STATUS_ACTIVE)
        self.assertEqual(active_db_bookings.count(), capacity)
        self.assertLessEqual(active_db_bookings.count(), session.capacity)

    def test_ten_users_race_for_one_seat(self):
        """10 threads race for capacity=1 -> exactly 1 success, 9 conflicts, 1 active DB booking."""
        session = Session.objects.create(
            creator=self.creator,
            title='1-Seat Breathwork Sprint',
            starts_at=timezone.now() + timedelta(days=3),
            capacity=1,
            location='Private Suite'
        )
        self._execute_concurrent_booking_race(session, capacity=1)

    def test_ten_users_race_for_two_seats(self):
        """10 threads race for capacity=2 -> exactly 2 successes, 8 conflicts, 2 active DB bookings."""
        session = Session.objects.create(
            creator=self.creator,
            title='2-Seat Duet Sound Bath',
            starts_at=timezone.now() + timedelta(days=3),
            capacity=2,
            location='Studio 2'
        )
        self._execute_concurrent_booking_race(session, capacity=2)

    def test_ten_users_race_for_five_seats(self):
        """10 threads race for capacity=5 -> exactly 5 successes, 5 conflicts, 5 active DB bookings."""
        session = Session.objects.create(
            creator=self.creator,
            title='5-Seat Small Group Meditation',
            starts_at=timezone.now() + timedelta(days=3),
            capacity=5,
            location='Main Hall'
        )
        self._execute_concurrent_booking_race(session, capacity=5)

    def test_concurrent_cancel_and_rebook_race(self):
        """
        Tests race between active user cancelling their booking and other users attempting to book.
        Verifies that no more than 1 active booking ever exists concurrently and row locking serializes states.
        """
        session = Session.objects.create(
            creator=self.creator,
            title='1-Seat Contention Session',
            starts_at=timezone.now() + timedelta(days=3),
            capacity=1,
            location='Private Suite'
        )

        # User 0 books the only seat first
        Booking.objects.create(
            user=self.users[0],
            session=session,
            status=Booking.STATUS_ACTIVE
        )

        num_racers = 5
        barrier = threading.Barrier(num_racers)
        results = []
        results_lock = threading.Lock()

        # User 0 cancels
        def cancel_task():
            connection.close()
            client = APIClient()
            client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.tokens[0]}')
            booking = Booking.objects.get(user=self.users[0], session=session)
            barrier.wait()
            resp = client.delete(f'/api/bookings/{booking.id}/')
            with results_lock:
                results.append(('cancel', resp.status_code))
            connection.close()

        # Users 1 to 4 attempt to book
        def book_task(token):
            connection.close()
            client = APIClient()
            client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
            barrier.wait()
            resp = client.post('/api/bookings/', {'session_id': session.id}, format='json')
            with results_lock:
                results.append(('book', resp.status_code))
            connection.close()

        threads = [threading.Thread(target=cancel_task)]
        for token in self.tokens[1:num_racers]:
            threads.append(threading.Thread(target=book_task, args=(token,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        connection.close()

        # Invariant: At most 1 active booking exists in DB, capacity is never violated
        active_count = Booking.objects.filter(session=session, status=Booking.STATUS_ACTIVE).count()
        self.assertLessEqual(active_count, 1)
