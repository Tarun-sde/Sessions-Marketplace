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
    Verifies that under simultaneous race conditions on the last available seat,
    PostgreSQL row-level locking (select_for_update) guarantees that:
    1. Exactly ONE booking succeeds (201 Created).
    2. All other concurrent requests are rejected cleanly with SESSION_FULL (409 Conflict).
    3. The database active booking count is exactly 1 (0 oversold).
    """

    def setUp(self):
        # Create creator and a session with capacity = 1
        self.creator = User.objects.create_user(
            username='concurrency_creator',
            email='concurrency_creator@ahoum.com',
            is_creator=True
        )
        self.session = Session.objects.create(
            creator=self.creator,
            title='Exclusive 1-on-1 Meditation',
            description='High contention single-seat session.',
            starts_at=timezone.now() + timedelta(days=3),
            capacity=1,
            location='Private Suite'
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

    def test_ten_users_race_for_one_seat(self):
        """
        10 threads simultaneously fire POST /api/bookings/ against a session with capacity=1.
        Uses threading.Barrier to ensure millisecond alignment.
        """
        barrier = threading.Barrier(self.num_workers)
        results = []
        results_lock = threading.Lock()

        def worker_task(user_token):
            # Close existing connection to ensure worker gets its own DB connection
            connection.close()

            client = APIClient()
            client.credentials(HTTP_AUTHORIZATION=f'Bearer {user_token}')

            # Wait at barrier until all 10 workers are ready
            barrier.wait()

            # Execute simultaneous booking request
            response = client.post(
                '/api/bookings/',
                {'session_id': self.session.id},
                format='json'
            )

            with results_lock:
                results.append({
                    'status_code': response.status_code,
                    'data': response.data
                })

            # Clean up connection
            connection.close()

        threads = []
        for token in self.tokens:
            t = threading.Thread(target=worker_task, args=(token,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Reopen main connection for assertions
        connection.close()

        # 1. Tally outcomes
        successes = [r for r in results if r['status_code'] == 201]
        conflicts = [r for r in results if r['status_code'] == 409]
        others = [r for r in results if r['status_code'] not in (201, 409)]

        # 2. Strict concurrency assertions
        self.assertEqual(len(results), self.num_workers, "All workers must finish and report results.")
        self.assertEqual(len(others), 0, f"No unexpected errors (500, 400, etc.) allowed. Found: {others}")
        self.assertEqual(len(successes), 1, f"Exactly ONE booking must succeed. Found: {len(successes)}")
        self.assertEqual(len(conflicts), self.num_workers - 1, f"Remaining {self.num_workers - 1} must receive 409 conflict.")

        # Verify error code on all conflicting requests
        for conflict in conflicts:
            self.assertIn('error', conflict['data'])
            self.assertEqual(conflict['data']['error']['code'], 'SESSION_FULL')

        # 3. Database Invariant Assertion: Exactly 1 active booking in PostgreSQL
        active_db_bookings = Booking.objects.filter(
            session=self.session,
            status=Booking.STATUS_ACTIVE
        )
        self.assertEqual(active_db_bookings.count(), 1, "Database active booking count must be exactly 1.")
        self.assertLessEqual(active_db_bookings.count(), self.session.capacity, "Capacity must never be oversold.")

    def test_concurrent_cancel_and_rebook_race(self):
        """
        Tests race between active user cancelling their booking and other users attempting to book.
        Verifies that no more than 1 active booking ever exists concurrently.
        """
        # User 0 books the only seat first
        Booking.objects.create(
            user=self.users[0],
            session=self.session,
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
            booking = Booking.objects.get(user=self.users[0], session=self.session)
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
            resp = client.post('/api/bookings/', {'session_id': self.session.id}, format='json')
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

        # Invariant: At most 1 active booking exists in DB
        active_count = Booking.objects.filter(session=self.session, status=Booking.STATUS_ACTIVE).count()
        self.assertLessEqual(active_count, 1)
