from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta

from ..models.unifiedbooking import UnifiedBooking

class DashboardView(LoginRequiredMixin, View):
    login_url = "accounts:signin"
    template_name = "calendarapp/dashboard.html"

    def get(self, request, *args, **kwargs):
        user = request.user
        today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        day_after_tomorrow = today + timedelta(days=2)

        # Get all bookings for the user (or all if staff)
        if user.is_staff:
            all_bookings = UnifiedBooking.objects.filter(is_deleted=False)
        else:
            all_bookings = UnifiedBooking.objects.filter(
                Q(user=user) | Q(user__isnull=True),
                is_deleted=False
            )

        # Filter bookings starting from today onward
        future_bookings = all_bookings.filter(date_time__gte=today)

        # ✅ Bookings for Today
        today_events = future_bookings.filter(date_time__date=today.date()).order_by("date_time")

        # ✅ Bookings for Tomorrow
        tomorrow_events = future_bookings.filter(date_time__date=tomorrow.date()).order_by("date_time")

        # ✅ Upcoming Events: After Tomorrow (Day After Tomorrow onwards)
        upcoming_events = future_bookings.filter(date_time__date__gte=day_after_tomorrow.date()).order_by("date_time")

        context = {
            "total_event": all_bookings.count(),
            "today_events": today_events,
            "tomorrow_events": tomorrow_events,
            "upcoming_events": upcoming_events,
        }
        return render(request, self.template_name, context)

