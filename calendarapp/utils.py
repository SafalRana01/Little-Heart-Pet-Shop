from calendar import HTMLCalendar
from .models.unifiedbooking import UnifiedBooking
from datetime import datetime, timedelta

class Calendar(HTMLCalendar):
    def __init__(self, year=None, month=None):
        self.year = year
        self.month = month
        super(Calendar, self).__init__()

    def formatday(self, day, events):
        events_per_day = events.filter(date_time__day=day)
        d = ""
        for event in events_per_day:
            d += f"<li>{event}</li>"  # Customize event display as needed
        if day != 0:
            return f"<td><span class='date'>{day}</span><ul> {d} </ul></td>"
        return "<td></td>"

    def formatweek(self, theweek, events):
        week = ""
        for d, weekday in theweek:
            week += self.formatday(d, events)
        return f"<tr> {week} </tr>"

    def formatmonth(self, withyear=True):
        events = UnifiedBooking.objects.filter(
            date_time__year=self.year, date_time__month=self.month, is_deleted=False
        )
        cal = '<table border="0" cellpadding="0" cellspacing="0" class="calendar">\n'
        cal += f"{self.formatmonthname(self.year, self.month, withyear=withyear)}\n"
        cal += f"{self.formatweekheader()}\n"
        for week in self.monthdays2calendar(self.year, self.month):
            cal += f"{self.formatweek(week, events)}\n"
        return cal


def is_slot_available(booking_date, booking_time):
    date_time = datetime.combine(booking_date, booking_time)
    return not UnifiedBooking.objects.filter(date_time=date_time, is_deleted=False).exists()


def calculate_duration(service_type, size, add_ons):
    base_durations = {
        'puppy_bath': {'XS': 60, 'S': 60, 'M': 60, 'L': 60},
        'wash_dry': {'XS': 45, 'S': 60, 'M': 90, 'L': 120},
        'wash_tidy': {'XS': 60, 'S': 75, 'M': 90, 'L': 120},
        'full_groom': {'XS': 90, 'S': 120, 'M': 150, 'L': 210},
    }
    duration_minutes = base_durations.get(service_type, {}).get(size, 60)

    if 'dematting' in add_ons:
        duration_minutes += 15
    if 'deshedding' in add_ons:
        duration_minutes += 15

    other_addons = ['nail_trim', 'anal_gland', 'teeth_brush']
    duration_minutes += 5 * sum(1 for addon in add_ons if addon in other_addons)

    return timedelta(minutes=duration_minutes)


def is_slot_available_with_duration(start_datetime, service_type, size, add_ons):
    """Check if given slot overlaps with existing bookings in UnifiedBooking"""
    duration = calculate_duration(service_type, size, add_ons)
    end_datetime = start_datetime + duration

    bookings = UnifiedBooking.objects.filter(
        date_time__date=start_datetime.date(),
        status='approved',  # only consider approved slots
        is_deleted=False
    )

    for booking in bookings:
        existing_start = booking.date_time
        existing_duration = calculate_duration(booking.service_type, booking.size, booking.add_ons or [])
        existing_end = existing_start + existing_duration

        # Check if time ranges overlap
        if (start_datetime < existing_end and end_datetime > existing_start):
            print("Overlap detected!")
            return False

    print("No overlap detected.")
    return True