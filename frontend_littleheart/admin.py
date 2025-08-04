from django.contrib import admin
from .models import Contact, Blog, GroomingBooking

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'created_at')
    search_fields = ('name', 'email', 'subject')
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)

@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at')
    search_fields = ('title', 'content')
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)
    prepopulated_fields = {'slug': ('title',)}
    def has_add_permission(self, request):
        return request.user.is_staff
    def has_change_permission(self, request, obj=None):
        return request.user.is_staff
    def has_delete_permission(self, request, obj=None):
        return request.user.is_staff

@admin.register(GroomingBooking)
class GroomingBookingAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'pet_size', 'service_type', 'date_time', 'status', 'created_at')
    search_fields = ('full_name', 'contact_no', 'email', 'service_type')
    list_filter = ('status', 'created_at', 'pet_size', 'service_type')
    readonly_fields = ('created_at',)