from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import time, date, datetime, timedelta
import pytz
from django.db.models import Q



class UnifiedBookingManager(models.Manager):
    """ Manager for UnifiedBooking """

    def get_all_events(self, user):
        return self.filter(
            Q(user=user) | Q(user__isnull=True),
            is_active=True,
            is_deleted=False,
            # booking_type='event'
        )

    def get_running_events(self, user=None):
        today = date.today()
        start = datetime.combine(today, time.min)
        end = datetime.combine(today, time.max)
        qs = self.filter(
            Q(user=user) | Q(user__isnull=True),
            is_active=True,
            is_deleted=False,
            # booking_type='event',
            date_time__range=(start, end)
        ).order_by('date_time')


    def get_completed_events(self, user):
        """Past events before today."""
        today = date.today()
        today_start = datetime.combine(today, time.min)
        return self.filter(
            Q(user=user) | Q(user__isnull=True),
            is_active=True,
            is_deleted=False,
            # booking_type='event',
            date_time__lt=today_start
        )

    def get_upcoming_events(self, user):
        """Future events after today."""
        today = date.today()
        today_end = datetime.combine(today, time.max)
        return self.filter(
            Q(user=user) | Q(user__isnull=True),
            is_active=True,
            is_deleted=False,
            # booking_type='event',
            date_time__gt=today_end
        )


class UnifiedBooking(models.Model):
    BOOKING_TYPE_CHOICES = (
        ('event', 'Calendar Event'),
        ('grooming', 'Grooming Booking'),
    )

    booking_type = models.CharField(max_length=20, choices=BOOKING_TYPE_CHOICES)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    full_name = models.CharField(max_length=100, blank=True, null=True)
    contact_no = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    size = models.CharField(max_length=10, blank=True, null=True)
    pet_size = models.CharField(
        max_length=10,
        choices=[
            ('XS', 'Extra Small'),
            ('S', 'Small'),
            ('M', 'Medium'),
            ('L', 'Large'),
            ('XL', 'Extra Large'),
            ('XXL', 'Double Extra Large')
        ],
        blank=True,
        null=True
    )

    service_type = models.CharField(max_length=100)
    add_ons = models.JSONField(default=list, blank=True, null=True)

    # UTC datetime field for bookings
    date_time = models.DateTimeField()

    notes = models.TextField(blank=True, null=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    estimated_time = models.IntegerField(null=True, blank=True)

    status = models.CharField(
        max_length=10,
        choices=(('approved', 'Approved'), ('canceled', 'Canceled')),
        default='approved'
    )

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    objects = UnifiedBookingManager()
    def __str__(self):
        return f"{self.booking_type} for {self.user} at {self.local_date_time.strftime('%Y-%m-%d %H:%M')}"

    def save(self, *args, **kwargs):
        """
        Ensure the `date_time` is stored in UTC.
        Convert from Asia/Kathmandu if naive or localized.
        """
    
        if self.date_time:
            if timezone.is_aware(self.date_time):
                self.date_time = self.date_time.astimezone(pytz.UTC).replace(tzinfo=None)
        super(UnifiedBooking, self).save(*args, **kwargs)

    @property
    def local_date_time(self):
        """
        Return the stored UTC datetime as localized to Asia/Kathmandu.
        Used for rendering in calendar or frontend.
        """
        # kathmandu_tz = pytz.timezone("Asia/Kathmandu")
        # return timezone.localtime(self.date_time, kathmandu_tz)
        return self.date_time
    
    @property
    def end_time(self):
        """
        Calculate the booking end time by adding estimated_time minutes to date_time.
        Returns None if date_time is None.
        """
        if self.date_time and self.estimated_time:
            return self.date_time + timedelta(minutes=self.estimated_time)
        return self.date_time  # or None if you prefer


    @staticmethod
    def get_running_events(user=None):
        today = date.today()
        start_of_today = datetime.combine(today, time.min)  # naive datetime in local time

        queryset = UnifiedBooking.objects.filter(date_time__gte=start_of_today)
        if user and not user.is_staff:
            queryset = queryset.filter(user=user)
        return queryset