from django.contrib import admin
from calendarapp import models

@admin.register(models.Event)
class EventAdmin(admin.ModelAdmin):
    model = models.Event
    list_display = [
        "id",
        "user",
        "size",
        "booking_date",
        "booking_time",
        "service_type",
        "is_active",
        "is_deleted",
    ]
    list_filter = ["is_active", "is_deleted", "service_type", "size"]
    search_fields = ["user__username", "size", "service_type"]

@admin.register(models.EventMember)
class EventMemberAdmin(admin.ModelAdmin):
    model = models.EventMember
    list_display = ["id", "event", "user"]
    list_filter = ["event", "user"]
