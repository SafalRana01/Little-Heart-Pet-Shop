from django.db import models
from django.utils.text import slugify
from calendarapp.models import UnifiedBooking 


class Contact(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15, blank=True, null=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'little_heart_contacts'

    def __str__(self):
        return f"{self.name} - {self.subject}"

class Blog(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    image = models.ImageField(upload_to='blog_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)

    class Meta:
        db_table = 'little_heart_blogs'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

class GroomingBooking(models.Model):
    STATUS_CHOICES = (
        ('approved', 'Approved'),
        ('canceled', 'Canceled'),
    )
    full_name = models.CharField(max_length=100)
    contact_no = models.CharField(max_length=15)
    email = models.EmailField(max_length=50, blank=True, null=True)  # Made optional
    pet_size = models.CharField(max_length=10, choices=[('XS', 'Extra Small'), ('S', 'Small'), ('M', 'Medium'), ('L', 'Large'), ('XL', 'Extra Large'), ('XXL', 'Double Extra Large')])
    service_type = models.CharField(max_length=50, choices=[('wash_dry', 'Wash & Dry'), ('wash_tidy', 'Wash & Tidy'), ('full_groom', 'Full Groom'), ('puppy_intro', 'Puppy Intro')])
    add_ons = models.JSONField(default=list)
    date_time = models.DateTimeField()
    notes = models.TextField(blank=True, null=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='approved')
    created_at = models.DateTimeField(auto_now_add=True)
    estimated_time = models.IntegerField(null=True, blank=True)




    def __str__(self):
        return f"{self.full_name} - {self.date_time}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # 👇 Automatically create/update UnifiedBooking
        UnifiedBooking.objects.update_or_create(
            booking_type='grooming',
            user=None,
            date_time=self.date_time,
            defaults={
                'full_name': self.full_name,
                'contact_no': self.contact_no,
                'email': self.email,
                'pet_size': self.pet_size,
                'service_type': self.service_type,
                'add_ons': self.add_ons,
                'notes': self.notes,
                'status': self.status,
                'is_active': True,
                'is_deleted': False,
                'estimated_time': self.estimated_time
            }
        )