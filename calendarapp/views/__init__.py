from .dashboard import DashboardView
from .event_list import AllEventsListView, CompletedEventsListView, RunningEventsListView, UpcomingEventsListView

from .other_views import (
    CalendarViewNew,
    CalendarView,
    create_event,
    EventEdit,
    event_details,
    add_eventmember,
    EventMemberDeleteView,
    delete_booking,
    next_week,
    next_day,
    next_month,
)


__all__ = [
    DashboardView,
    AllEventsListView,
    RunningEventsListView,
    UpcomingEventsListView,
    CompletedEventsListView,
    CalendarViewNew,
    CalendarView,
    create_event,
    EventEdit,
    event_details,
    add_eventmember,
    EventMemberDeleteView,
    delete_booking,
    next_week,
    next_day,
    next_month,
]
