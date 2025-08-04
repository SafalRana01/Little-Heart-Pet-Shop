from datetime import datetime, date
from django.db import models
from django.urls import reverse
from accounts.models import User
from .unifiedbooking import UnifiedBooking


class EventManager(models.Manager):
    """ Event manager """

    def get_all_events(self, user):
        return Event.objects.filter(user=user, is_active=True, is_deleted=False)

    def get_running_events(self, user):
        """Consider 'running' as events happening today."""
        today = date.today()
        return Event.objects.filter(
            user=user,
            is_active=True,
            is_deleted=False,
            booking_date=today
        ).order_by("booking_time")

    def get_completed_events(self, user):
        """Completed = booked in the past."""
        today = date.today()
        return Event.objects.filter(
            user=user,
            is_active=True,
            is_deleted=False,
            booking_date__lt=today
        )

    def get_upcoming_events(self, user):
        """Upcoming = booked in the future."""
        today = date.today()
        return Event.objects.filter(
            user=user,
            is_active=True,
            is_deleted=False,
            booking_date__gt=today
        )


class Event(models.Model):
    """ Event model """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="events")
    size = models.CharField(max_length=10)  # e.g., 'S','M','L','XL'
    booking_date = models.DateField(null=True, blank=True)
    booking_time = models.TimeField(null=True, blank=True)
    service_type = models.CharField(max_length=100)  # e.g., 'washDry','washTidy'
    addons = models.TextField(blank=True, null=True)  # comma-separated strings

    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)

    objects = EventManager()

    def __str__(self):
        return f"Event for {self.user.username} on {self.booking_date} at {self.booking_time}"

    def get_absolute_url(self):
        return reverse("calendarapp:event-detail", args=(self.id,))

    @property
    def get_html_url(self):
        url = reverse("calendarapp:event-detail", args=(self.id,))
        return f'<a href="{url}">{self.service_type}</a>'

    def save(self, *args, **kwargs):
        date_time = None
        if self.booking_date and self.booking_time:
            # Create naive datetime (no timezone)
            date_time = datetime.combine(self.booking_date, self.booking_time)

        super().save(*args, **kwargs)

        UnifiedBooking.objects.update_or_create(
            booking_type='event',
            user=self.user,
            date_time=date_time,
            defaults={
                'size': self.size,
                'service_type': self.service_type,
                'add_ons': self.addons.split(',') if self.addons else [],
                'status': 'approved' if self.is_active else 'canceled',
                'is_active': self.is_active,
                'is_deleted': self.is_deleted,
            }
        )
