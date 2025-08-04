from django.contrib import admin
from django.urls import path, include
from frontend_littleheart import views  
from django.conf import settings
from django.conf.urls.static import static
from calendarapp.views import DashboardView


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('terms-and-conditions/', views.terms, name='terms_and_conditions'),  
    path('about/', views.about, name='about'),
    path('blog/', views.blog_list, name='blog_list'),
    path('blog/<slug:slug>/', views.blog_detail, name='blog_detail'),
    path('contact/', views.contact, name='contact'),
    path('grooming/', views.grooming, name='grooming'),
    path('dog/', views.dog, name='dog'),
    path('cat/', views.cat, name='cat'),
    path('get-time-slots/', views.get_time_slots, name='get_time_slots'),
    path('book-grooming-appointment/', views.book_grooming_appointment, name='book_grooming_appointment'),
    path('grooming-booking/', views.grooming_booking, name='grooming_booking'),  # Added new path

    # Staff side: Dashboard and calendarapp URLs
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('accounts/', include('accounts.urls')),         # login/logout/signup for staff side
    path('calendarapp/', include('calendarapp.urls')),   # calendarapp URLs with prefix
    
] + static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0]) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)