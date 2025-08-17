from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.core.mail import send_mail
from django.conf import settings
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib import messages
import json
from datetime import timedelta
from .models import Contact, Blog, GroomingBooking
import logging
from django.utils import timezone
from .forms import ContactForm
import qrcode
from io import BytesIO
import base64
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime
from calendarapp.models import UnifiedBooking
logger = logging.getLogger(__name__)

def home(request):
    return render(request, 'frontend_littleheart/index.html')

def terms(request):
    return render(request, 'frontend_littleheart/terms_and_conditions.html')

def about(request):
    return render(request, 'frontend_littleheart/about.html')

def blog_list(request):
    blogs = Blog.objects.all()
    paginator = Paginator(blogs, 4)
    page = request.GET.get('page')
    try:
        blogs_page = paginator.page(page)
    except PageNotAnInteger:
        blogs_page = paginator.page(1)
    except EmptyPage:
        blogs_page = paginator.page(paginator.num_pages)
    return render(request, 'frontend_littleheart/blog.html', {'blogs': blogs_page})

def blog_detail(request, slug):
    blog = get_object_or_404(Blog, slug=slug)
    other_blogs = Blog.objects.exclude(id=blog.id).order_by('-created_at')[:4]
    return render(request, 'frontend_littleheart/blog_detail.html', {'blog': blog, 'other_blogs': other_blogs})

def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact = form.save()
            try:
                send_mail(
                    subject=f"New Contact Form Submission: {contact.subject}",
                    message=f"Name: {contact.name}\nEmail: {contact.email}\nPhone: {contact.phone or 'Not provided'}\nMessage: {contact.message}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.DEFAULT_FROM_EMAIL],
                    fail_silently=False,
                )
                messages.success(request, "Thank you! Your message has been sent successfully.")
            except Exception as e:
                logger.error(f"Email sending failed for contact {contact.id}: {str(e)}")
                messages.error(request, "Message saved, but email sending failed. Please contact support.")
            return redirect('contact')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = ContactForm()
    return render(request, 'frontend_littleheart/contact.html', {'form': form})

def grooming(request):
    return render(request, 'frontend_littleheart/grooming.html')

def regular_bathing(request):
    return render(request, 'frontend_littleheart/regular_bath.html')

def dog(request):
    return render(request, 'frontend_littleheart/dog.html')

def cat(request):
    return render(request, 'frontend_littleheart/cat.html')

@ensure_csrf_cookie
def get_time_slots(request):
    date_str = request.GET.get('date')
    if not date_str:
        logger.warning("No date parameter provided in get_time_slots")
        return JsonResponse({'success': False, 'message': 'Date parameter is required'}, status=400)

    try:
        date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
        today = timezone.now().date()
        max_date = today + timedelta(days=30)

        if date < today or date > max_date:
            logger.warning(f"Invalid date {date_str}: outside allowed range {today} to {max_date}")
            return JsonResponse({'success': False, 'message': 'Please select a date within the next 30 days from today.'}, status=400)

        time_slots = []
        for hour in range(9, 17):  # 9 AM to 4 PM
            for minute in [0, 15, 30, 45]:
                if hour == 16 and minute > 0:
                    continue
                time_str = f"{hour:02d}:{minute:02d}"
                display_time = f"{hour % 12 or 12}:{minute:02d} {'PM' if hour >= 12 else 'AM'}"
                time_slots.append({'time': time_str, 'display': display_time})

        bookings = UnifiedBooking.objects.filter(date_time__date=date, status='approved')
        booked_ranges = []

        for booking in bookings:
            base_durations = {
                'puppy_bath': {'XS': timedelta(minutes=60), 'S': timedelta(minutes=60), 'M': timedelta(minutes=60), 'L': timedelta(minutes=60)},
                'wash_dry': {'XS': timedelta(minutes=45), 'S': timedelta(hours=1), 'M': timedelta(minutes=90), 'L': timedelta(hours=2)},
                'wash_tidy': {'XS': timedelta(minutes=60), 'S': timedelta(minutes=75), 'M': timedelta(minutes=90), 'L': timedelta(hours=2)},
                'full_groom': {'XS': timedelta(minutes=90), 'S': timedelta(hours=2), 'M': timedelta(minutes=150), 'L': timedelta(minutes=210)}
            }
            duration = base_durations.get(booking.service_type, {}).get(booking.pet_size, timedelta(minutes=60))
            if 'dematting' in booking.add_ons:
                duration += timedelta(minutes=15)
            if 'deshedding' in booking.add_ons:
                duration += timedelta(minutes=15)
            additional_addons = [addon for addon in booking.add_ons if addon in ['nail_trim', 'anal_gland', 'teeth_brush']]
            duration += timedelta(minutes=5 * len(additional_addons))

            start_time = booking.date_time.time()
            end_time = (timezone.datetime.combine(date, start_time) + duration).time()
            booked_ranges.append((start_time, end_time))

        available_slots = []
        min_duration = timedelta(minutes=60)
        for slot in time_slots:
            slot_time = timezone.datetime.strptime(slot['time'], '%H:%M').time()
            slot_datetime = timezone.datetime.combine(date, slot_time)
            is_available = True
            slot_end = slot_datetime + min_duration

            for start_time, end_time in booked_ranges:
                start_datetime = timezone.datetime.combine(date, start_time)
                end_datetime = timezone.datetime.combine(date, end_time)
                if (slot_datetime < end_datetime and slot_end > start_datetime) or \
                   (slot_datetime >= start_datetime and slot_datetime < end_datetime):
                    is_available = False
                    break

            if is_available:
                available_slots.append(slot)

        logger.info(f"Available time slots for {date_str}: {available_slots}")
        return JsonResponse({'success': True, 'time_slots': available_slots})
    except ValueError:
        logger.error("Invalid date format received")
        return JsonResponse({'success': False, 'message': 'Invalid date format'}, status=400)
    except Exception as e:
        logger.error(f"Error in get_time_slots: {str(e)}")
        return JsonResponse({'success': False, 'message': 'An unexpected error occurred'}, status=500)


def convert_to_minutes(duration_str):
    duration_str = duration_str.lower().strip()
    hours = 0
    minutes = 0

    if "hr" in duration_str:
        parts = duration_str.split("hr")
        try:
            hours = int(parts[0].strip())
        except:
            hours = 0
        if "min" in parts[1]:
            try:
                minutes = int(parts[1].replace("min", "").strip())
            except:
                minutes = 0
    elif "min" in duration_str:
        try:
            minutes = int(duration_str.replace("min", "").strip())
        except:
            minutes = 0

    return hours * 60 + minutes

@csrf_exempt
def book_grooming_appointment(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            logger.info(f"Received booking data: {data}")
            full_name = data.get('full_name', '')
            contact_no = data.get('contact_no', '')
            email = data.get('email')  # Optional, can be None

            pet_size = data.get('pet_size')
            service_type = data.get('service_type')
            add_ons = data.get('add_ons', [])
            notes = data.get('notes', '')
            date_time_str = data.get('date_time')
            raw_duration = data.get('estimated_time', '0')
            estimated_time = convert_to_minutes(raw_duration)


            if not all([full_name, contact_no, pet_size, service_type, date_time_str]):
                return JsonResponse({'success': False, 'message': 'Required fields are missing'}, status=400)

            if service_type not in ['puppy_bath', 'wash_dry', 'wash_tidy', 'full_groom']:
                return JsonResponse({'success': False, 'message': 'Invalid service type'}, status=400)

            base_prices = {
                'puppy_bath': {'XS': 1600, 'S': 1600, 'M': 1600, 'L': 1600},
                'wash_dry': {'XS': 950, 'S': 1450, 'M': 1800, 'L': 2250},
                'wash_tidy': {'XS': 1200, 'S': 1870, 'M': 2350, 'L': 2600},
                'full_groom': {'XS': 1500, 'S': 2060, 'M': 2500, 'L': 2950}
            }
            total_price = base_prices.get(service_type, {}).get(pet_size, 0)
            add_on_prices = {
                'dematting': 500, 'deshedding': 500, 'special_shampoo': 500,
                'flea_tick_shampoo': 500, 'nail_trim': 250, 'teeth_brush': 250, 'anal_gland': 600
            }
            for add_on in add_ons:
                total_price += add_on_prices.get(add_on, 0)

            try:
                # date_time = timezone.make_aware(timezone.datetime.strptime(date_time_str, '%Y-%m-%d %H:%M'))
                date_time = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M')
            except ValueError:
                logger.error(f"Invalid date_time format: {date_time_str}")
                return JsonResponse({'success': False, 'message': 'Invalid date or time format'}, status=400)

            duration = {
                'puppy_bath': {'XS': timedelta(minutes=60), 'S': timedelta(minutes=60), 'M': timedelta(minutes=60), 'L': timedelta(minutes=60)},
                'wash_dry': {'XS': timedelta(minutes=45), 'S': timedelta(hours=1), 'M': timedelta(minutes=90), 'L': timedelta(hours=2)},
                'wash_tidy': {'XS': timedelta(minutes=60), 'S': timedelta(minutes=75), 'M': timedelta(minutes=90), 'L': timedelta(hours=2)},
                'full_groom': {'XS': timedelta(minutes=90), 'S': timedelta(hours=2), 'M': timedelta(minutes=150), 'L': timedelta(minutes=210)}
            }.get(service_type, {}).get(pet_size, timedelta(minutes=0))
            if 'dematting' in add_ons:
                duration += timedelta(minutes=15)
            if 'deshedding' in add_ons:
                duration += timedelta(minutes=15)
            end_time = date_time + duration

            # Improved overlap detection
            overlapping = UnifiedBooking.objects.filter(
                date_time__lt=end_time, date_time__gte=date_time,
                status='approved'
            ).exists() or UnifiedBooking.objects.filter(
                date_time__lte=date_time, date_time__gt=date_time - duration,
                status='approved'
            ).exists() or UnifiedBooking.objects.filter(
                date_time__range=(date_time, end_time),
                status='approved'
            ).exclude(id__in=[booking.id] if 'booking' in locals() else []).exists()

            if overlapping:
                return JsonResponse({'success': False, 'message': 'This date and time overlaps with an existing booking.'})

            today = timezone.now().date()
            max_date = today + timedelta(days=30)
            if date_time.date() < today or date_time.date() > max_date:
                return JsonResponse({'success': False, 'message': 'Please select a date within the next 30 days.'})

            logger.info(f"Booking processed for {full_name}")

            booking = UnifiedBooking(
                full_name=full_name,
                contact_no=contact_no,
                email=email,
                pet_size=pet_size,
                service_type=service_type,
                add_ons=add_ons,
                date_time=date_time,
                notes=notes,
                total_price=total_price,
                estimated_time=estimated_time,
                status='approved'
            )
            logger.info(f"Booking object before save: {booking.__dict__}")
            booking.save()
            logger.info(f"Booking saved: {booking.id}")

            service_type_display = service_type.replace('_', ' ').title() if service_type != 'puppy_bath' else "Puppy's First Bath"
            qr_data = (
                f"Booking ID: {booking.id}\n"
                f"Date & Time: {date_time.strftime('%Y-%m-%d %I:%M %p')}\n"
                f"Service Type: {service_type_display}\n"
                f"Pet Size: {pet_size}\n"
                f"Total Price: Rs. {total_price}\n"
                f"Status: {booking.status}\n"
                f"Add-ons: {', '.join(add_ons) if add_ons else 'None'}\n"
                f"Notes: {notes or 'None'}"
            )
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(qr_data)
            qr.make(fit=True)
            img = qr.make_image(fill='black', back_color='white')
            buffered = BytesIO()
            img.save(buffered, format='PNG')
            qr_code_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            logger.info(f"Generated QR code base64 length: {len(qr_code_base64)}")

            # Prepare HTML message with QR code (no plain text)
            html_message = (
                f"<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Booking Confirmation</title></head>"
                f"<body style='font-family: Arial, sans-serif; color: #333; background-color: #f9f9f9; padding: 20px;'>"
                f"<table width='100%' cellpadding='0' cellspacing='0' border='0'><tr><td align='center'>"
                f"<table width='600' cellpadding='0' cellspacing='0' border='0' style='background-color: #ffffff; border: 1px solid #ddd; border-radius: 5px;'>"
                f"<tr><td style='background-color: #D84315; color: #ffffff; padding: 10px 20px; text-align: center; border-top-left-radius: 5px; border-top-right-radius: 5px;'>"
                f"<h1 style='margin: 0;'>Booking Confirmation</h1></td></tr><tr><td style='padding: 20px;'>"
                f"<table width='100%' cellpadding='10' cellspacing='0' border='1' style='border-collapse: collapse; margin: 10px 0;'>"
                f"<tr style='background-color: #f2f2f2;'><th style='text-align: left; padding: 10px; color: #333;'>Detail</th>"
                f"<th style='text-align: left; padding: 10px; color: #333;'>Information</th></tr>"
                f"<tr><td style='padding: 10px; color: #333;'>Booking ID</td><td style='padding: 10px; color: #333;'>{booking.id}</td></tr>"
                f"<tr><td style='padding: 10px; color: #333;'>Date & Time</td><td style='padding: 10px; color: #333;'>{date_time.strftime('%Y-%m-%d %I:%M %p')}</td></tr>"
                f"<tr><td style='padding: 10px; color: #333;'>Service Type</td><td style='padding: 10px; color: #333;'>{service_type_display}</td></tr>"
                f"<tr><td style='padding: 10px; color: #333;'>Pet Size</td><td style='padding: 10px; color: #333;'>{pet_size}</td></tr>"
                f"<tr><td style='padding: 10px; color: #333;'>Total Price</td><td style='padding: 10px; color: #333;'>Rs. {total_price}</td></tr>"
                f"<tr><td style='padding: 10px; color: #333;'>Status</td><td style='padding: 10px; color: #333;'>{booking.status}</td></tr>"
                f"<tr><td style='padding: 10px; color: #333;'>Add-ons</td><td style='padding: 10px; color: #333;'>{', '.join(add_ons) if add_ons else 'None'}</td></tr>"
                f"<tr><td style='padding: 10px; color: #333;'>Notes</td><td style='padding: 10px; color: #333;'>{notes or 'None'}</td></tr>"
                f"</table>"
                f"<div style='text-align: center; margin-top: 20px;'><img src='cid:booking_qr' alt='Booking QR Code' style='max-width: 200px; border: 1px solid #ccc; border-radius: 8px;'></div>"
                f"<p style='color: #333; text-align: center; margin-top: 20px;'>Note: Please arrive 10 minutes early to ensure a smooth appointment.</p>"
                f"<p style='color: #333; text-align: center; margin-top: 20px;'>If you need to cancel, please contact the pet shop ASAP.</p>"
                f"<p style='color: #333; text-align: center; margin-top: 20px;'>Thank you for choosing Little Heart Pet Shop!</p></td></tr>"
                f"</table></td></tr></table></body></html>"
            )

            # Create email message with only HTML part
            msg = MIMEMultipart()
            msg['Subject'] = 'Your Grooming Booking Confirmation'
            msg['From'] = settings.EMAIL_HOST_USER
            msg['To'] = email or settings.DEFAULT_FROM_EMAIL
            # msg['To'] = email
            # msg['Bcc'] = "magarsafal16@gmail.com"
            
            # HTML part with inline image
            msg.attach(MIMEText(html_message, 'html'))

            # Attach QR code image
            img_data = base64.b64decode(qr_code_base64)
            image = MIMEImage(img_data, name=f"booking_qr_{booking.id}.png")
            image.add_header('Content-ID', '<booking_qr>')
            image.add_header('Content-Disposition', 'inline', filename=f"booking_qr_{booking.id}.png")
            msg.attach(image)

            try:
                with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
                    server.starttls()
                    server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                    server.send_message(msg)
                logger.info(f"Email sent successfully for booking {booking.id}")
            except Exception as e:
                logger.error(f"Failed to send booking email for booking {booking.id}: {str(e)}")
                messages.error(request, f"Booking saved, but email failed to send: {str(e)}. Contact support.")

            scheduled_date = date_time.strftime('%Y-%m-%d')
            messages.success(request, f'Dear {full_name}, booking successfully done. Your appointment is scheduled on {scheduled_date} with phone number {contact_no}.')
            return JsonResponse({
                'success': True,
                'qr_code': qr_code_base64,
                'redirect_url': '/grooming-booking/'
            })

        except json.JSONDecodeError:
            logger.error("Invalid JSON data received")
            return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)
        except ValueError as e:
            logger.error(f"Invalid data format: {str(e)}")
            return JsonResponse({'success': False, 'message': f'Invalid data format: {str(e)}'}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error in book_grooming_appointment: {str(e)}")
            return JsonResponse({'success': False, 'message': 'An unexpected error occurred. Please try again.'}, status=500)
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)

@ensure_csrf_cookie
def grooming_booking(request):
    today = timezone.now().date()
    max_date = today + timedelta(days=30)
    return render(request, 'frontend_littleheart/grooming_booking.html', {
        'today': today,
        'max_date': max_date,
        'messages': messages.get_messages(request)
    })