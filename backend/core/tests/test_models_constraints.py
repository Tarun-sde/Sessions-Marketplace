from datetime import timedelta
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.db import IntegrityError
from core.models import User, Session, Booking
from core.serializers import SessionSerializer


class ModelConstraintTestCase(TransactionTestCase):
    """
    Tests enforcing database-level integrity constraints on PostgreSQL:
    1. Session capacity >= 1 CheckConstraint
    2. Booking UNIQUE(user, session) WHERE status='active' partial unique index
    """

    def setUp(self):
        self.creator = User.objects.create_user(
            username='creator_user',
            email='creator@ahoum.com',
            is_creator=True
        )
        self.user = User.objects.create_user(
            username='booker_user',
            email='booker@ahoum.com'
        )
        self.session = Session.objects.create(
            creator=self.creator,
            title='Yoga Nidra Meditation',
            description='Deep relaxation session.',
            starts_at=timezone.now() + timedelta(days=2),
            capacity=5,
            location='Online'
        )

    def test_session_capacity_check_constraint(self):
        """Database rejects session capacity < 1 at DB layer."""
        with self.assertRaises(IntegrityError):
            Session.objects.create(
                creator=self.creator,
                title='Invalid Capacity Session',
                starts_at=timezone.now() + timedelta(days=1),
                capacity=0
            )

    def test_booking_active_partial_unique_constraint(self):
        """A user cannot hold two active bookings for the same session."""
        # 1st active booking succeeds
        b1 = Booking.objects.create(
            user=self.user,
            session=self.session,
            status=Booking.STATUS_ACTIVE
        )
        self.assertIsNotNone(b1.id)

        # 2nd simultaneous active booking for same (user, session) fails at DB level
        with self.assertRaises(IntegrityError):
            Booking.objects.create(
                user=self.user,
                session=self.session,
                status=Booking.STATUS_ACTIVE
            )

    def test_cancelled_booking_allows_rebooking(self):
        """Cancelling an active booking allows the user to re-book."""
        b1 = Booking.objects.create(
            user=self.user,
            session=self.session,
            status=Booking.STATUS_ACTIVE
        )

        # Cancel the booking
        b1.status = Booking.STATUS_CANCELLED
        b1.save()

        # New active booking for same user and session now succeeds
        b2 = Booking.objects.create(
            user=self.user,
            session=self.session,
            status=Booking.STATUS_ACTIVE
        )
        self.assertIsNotNone(b2.id)
        self.assertNotEqual(b1.id, b2.id)


class SessionSerializerValidationTestCase(TestCase):
    """
    Tests serializer-level validation for Session inputs.
    """

    def setUp(self):
        self.creator = User.objects.create_user(
            username='creator_user',
            email='creator@ahoum.com',
            is_creator=True
        )

    def test_serializer_capacity_minimum(self):
        data = {
            'title': 'Test Session',
            'starts_at': timezone.now() + timedelta(days=1),
            'capacity': 0
        }
        serializer = SessionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('capacity', serializer.errors)

    def test_serializer_capacity_maximum(self):
        data = {
            'title': 'Test Session',
            'starts_at': timezone.now() + timedelta(days=1),
            'capacity': 10001
        }
        serializer = SessionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('capacity', serializer.errors)

    def test_serializer_starts_at_in_past_rejected_on_create(self):
        data = {
            'title': 'Past Session',
            'starts_at': timezone.now() - timedelta(hours=1),
            'capacity': 10
        }
        serializer = SessionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('starts_at', serializer.errors)

    def test_serializer_valid_creation(self):
        data = {
            'title': 'Valid Future Session',
            'starts_at': timezone.now() + timedelta(days=5),
            'capacity': 25,
            'location': 'Studio A'
        }
        serializer = SessionSerializer(data=data)
        self.assertTrue(serializer.is_valid())
