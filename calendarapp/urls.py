from django.urls import path
from calendarapp.views.other_views import book_unified_appointment, delete_booking, next_month
from . import views

app_name = "calendarapp"


urlpatterns = [
    path("calender/", views.CalendarViewNew.as_view(), name="calendar"),
    path("calenders/", views.CalendarView.as_view(), name="calendars"),
    # path('delete_event/<int:event_id>/', views.delete_event, name='delete_event'),
    path('delete_booking/<int:booking_id>/', delete_booking, name='delete_booking'),
    path('next_day/<int:booking_id>/', views.next_day, name='next_day'),
    # path('next_week/<int:event_id>/', views.next_week, name='next_week'),
    path('next_month/<int:booking_id>/', next_month, name='next_month'),
    path('next_day/<int:event_id>/', views.next_day, name='next_day'),
    path("event/new/", views.create_event, name="event_new"),
    path("event/edit/<int:pk>/", views.EventEdit.as_view(), name="event_edit"),
    path("event/<int:event_id>/details/", views.event_details, name="event-detail"),
    path(
        "add_eventmember/<int:event_id>", views.add_eventmember, name="add_eventmember"
    ),
    path(
        "event/<int:pk>/remove",
        views.EventMemberDeleteView.as_view(),
        name="remove_event",
    ),
    path("all-event-list/", views.AllEventsListView.as_view(), name="all_events"),
    path(
        "running-event-list/",
        views.RunningEventsListView.as_view(),
        name="running_events",
    ),
    path(
        "upcoming-event-list/",
        views.UpcomingEventsListView.as_view(),
        name="upcoming_events",
    ),
    path(
        "completed-event-list/",
        views.CompletedEventsListView.as_view(),
        name="completed_events",
    ),

    path("book-unified/", 
         book_unified_appointment, 
         name="book_unified"
         ),
    
    # path("check-slot/", ajax_check_slot, name="ajax_check_slot"),



]
