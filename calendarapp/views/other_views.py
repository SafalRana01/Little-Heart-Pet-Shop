
import decimal
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.views import generic
from django.utils.safestring import mark_safe
from datetime import timedelta, datetime, date
import calendar
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib import messages
from calendarapp.models import EventMember, Event
from calendarapp.utils import Calendar
from calendarapp.forms import EventForm, AddMemberForm
from calendarapp.models import UnifiedBooking
from calendarapp.utils import is_slot_available, is_slot_available_with_duration
from django.views.decorators.csrf import csrf_exempt
import json
from django.utils.dateparse import parse_date, parse_time

from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import logging
from io import BytesIO
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
import base64, smtplib, qrcode
from django.conf import settings
from django.utils.timezone import now
from django.contrib import messages
from django.shortcuts import render, redirect
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def get_date(req_day):
    if req_day:
        year, month = (int(x) for x in req_day.split("-"))
        return date(year, month, day=1)
    return datetime.today()


def prev_month(d):
    first = d.replace(day=1)
    prev_month = first - timedelta(days=1)
    month = "month=" + str(prev_month.year) + "-" + str(prev_month.month)
    return month


def next_month(d):
    days_in_month = calendar.monthrange(d.year, d.month)[1]
    last = d.replace(day=days_in_month)
    next_month = last + timedelta(days=1)
    month = "month=" + str(next_month.year) + "-" + str(next_month.month)
    return month


class CalendarView(LoginRequiredMixin, generic.ListView):
    login_url = "accounts:signin"
    model = Event
    template_name = "calendar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        d = get_date(self.request.GET.get("month", None))
        cal = Calendar(d.year, d.month)
        html_cal = cal.formatmonth(withyear=True)
        context["calendar"] = mark_safe(html_cal)
        context["prev_month"] = prev_month(d)
        context["next_month"] = next_month(d)
        return context


@login_required(login_url="signup")
def create_event(request):
    form = EventForm(request.POST or None)
    if request.POST and form.is_valid():
        event = form.save(commit=False)
        event.user = request.user
        addons = request.POST.getlist('addons')
        event.addons = ','.join(addons)  # Save as comma separated
        event.save()
        return HttpResponseRedirect(reverse("calendarapp:calendar"))
    return render(request, "event.html", {"form": form})


class EventEdit(generic.UpdateView):
    model = Event
    fields = ["size", "booking_date", "booking_time", "service_type", "addons"]
    template_name = "event.html"


@login_required(login_url="signup")
def event_details(request, event_id):
    event = Event.objects.get(id=event_id)
    eventmember = EventMember.objects.filter(event=event)
    context = {"event": event, "eventmember": eventmember}
    return render(request, "event-details.html", context)


def add_eventmember(request, event_id):
    forms = AddMemberForm()
    if request.method == "POST":
        forms = AddMemberForm(request.POST)
        if forms.is_valid():
            member = EventMember.objects.filter(event=event_id)
            event = Event.objects.get(id=event_id)
            if member.count() <= 9:
                user = forms.cleaned_data["user"]
                EventMember.objects.create(event=event, user=user)
                return redirect("calendarapp:calendar")
            else:
                print("--------------User limit exceed!-----------------")
    context = {"form": forms}
    return render(request, "add_member.html", context)


class EventMemberDeleteView(generic.DeleteView):
    model = EventMember
    template_name = "event_delete.html"
    success_url = reverse_lazy("calendarapp:calendar")



def format_service_name(service_type):
    return service_type.replace('_', ' ').title() if service_type != 'puppy_bath' else "Puppy's First Bath"


class CalendarViewNew(LoginRequiredMixin, generic.View):
    login_url = "accounts:signin"
    template_name = "calendarapp/calendar.html"
    form_class = EventForm

    def get(self, request, *args, **kwargs):
        forms = self.form_class()
        bookings = UnifiedBooking.objects.filter(is_deleted=False)

        event_list = []
        for booking in bookings:
            event_list.append({
                "id": booking.id,
                "title": str(booking.service_type),
                "start": booking.local_date_time.isoformat(),
                "contact_no": str(booking.contact_no),
                "customer_name": str(booking.full_name),
                "size": str(booking.size) if booking.size else str(booking.pet_size),
                "service": str(booking.service_type),
                "addons": ", ".join([addon.replace("_", " ") for addon in booking.add_ons]) if booking.add_ons else "",
            })

        context = {
            "form": forms,
            # "events": event_list,
            'events': json.dumps(event_list),
            "events_month": UnifiedBooking.get_running_events(request.user),
            "booked_slots": list(UnifiedBooking.objects.filter(is_deleted=False).values("date_time", "estimated_time")),
        }

        # import pprint
        # pprint.pprint(event_list)

        # pprint.pprint(event_list)
        print("booked_slots:", context["booked_slots"])
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        forms = self.form_class(request.POST)
        if forms.is_valid():
            booking_date = forms.cleaned_data["booking_date"]
            booking_time = forms.cleaned_data["booking_time"]
            start_datetime = datetime.combine(booking_date, booking_time)
            service_type = forms.cleaned_data["service_type"]
            size = forms.cleaned_data["size"]
            add_ons = request.POST.getlist("addons")

            full_name = request.POST.get("customer_name")
            contact_no = request.POST.get("customer_phone")
            email = request.POST.get("customer_email")
            # total_price = request.POST.get("total_price")
            # estimated_time = request.POST.get("estimated_time")

            # example inside your view:
            estimated_time = int(request.POST.get('estimated_time', 0))
            total_price = decimal.Decimal(request.POST.get('total_price', '0.00'))

            if not is_slot_available_with_duration(start_datetime, service_type, size, add_ons):
                messages.error(request, "This time slot is already booked. Please choose another.")
                return redirect("calendarapp:calendar")

            # Create booking
            booking = UnifiedBooking.objects.create(
                user=request.user,
                size=size,
                service_type=service_type,
                add_ons=add_ons,
                date_time=start_datetime,
                booking_type="event" if request.user.is_staff else "grooming",
                full_name=full_name,
                contact_no=contact_no,
                email=email,
                estimated_time=estimated_time,
                total_price=total_price,
            )

            logger.info(f"Booking created: {booking.id}")

            # === QR Code Data ===
            service_type_display = format_service_name(service_type)
            qr_data = (
                f"Booking ID: {booking.id}\n"
                f"Date & Time: {start_datetime.strftime('%Y-%m-%d %I:%M %p')}\n"
                f"Service Type: {service_type_display}\n"
                f"Size: {size}\n"
                f"Status: {booking.status}\n"
                f"Add-ons: {', '.join(add_ons) if add_ons else 'None'}"
            )

            # === Generate QR Code ===
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(qr_data)
            qr.make(fit=True)
            img = qr.make_image(fill='black', back_color='white')
            buffered = BytesIO()
            img.save(buffered, format='PNG')
            qr_code_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

            # === Email Setup ===
            html_message = (
                f"<html><body>"
                f"<h2>Appointment Confirmation</h2>"
                f"<p><strong>Booking ID:</strong> </p>"
                f"<p><strong>Date & Time:</strong> </p>"
                f"<p><strong>Service:</strong> </p>"
                f"<p><strong>Size:</strong> </p>"
                f"<p><strong>Add-ons:</strong> </p>"
                f"<br><p>Thank you for booking with us!</p>"
                f"<img src='cid:booking_qr' alt='Booking QR Code' style='max-width:200px;'>"
                f"</body></html>"
            )

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
                f"<tr><td style='padding: 10px; color: #333;'>Date & Time</td><td style='padding: 10px; color: #333;'>{start_datetime.strftime('%Y-%m-%d %I:%M %p')}</td></tr>"
                f"<tr><td style='padding: 10px; color: #333;'>Service Type</td><td style='padding: 10px; color: #333;'>{service_type_display}</td></tr>"
                f"<tr><td style='padding: 10px; color: #333;'>Pet Size</td><td style='padding: 10px; color: #333;'>{size}</td></tr>"
                f"<tr><td style='padding: 10px; color: #333;'>Total Price</td><td style='padding: 10px; color: #333;'>Rs. {total_price}</td></tr>"
                f"<tr><td style='padding: 10px; color: #333;'>Status</td><td style='padding: 10px; color: #333;'>{booking.status}</td></tr>"
                f"<tr><td style='padding: 10px; color: #333;'>Add-ons</td><td style='padding: 10px; color: #333;'>{', '.join(add_ons) if add_ons else 'None'}</td></tr>"
                # f"<tr><td style='padding: 10px; color: #333;'>Notes</td><td style='padding: 10px; color: #333;'>{notes or 'None'}</td></tr>"
                f"</table>"
                f"<div style='text-align: center; margin-top: 20px;'><img src='cid:booking_qr' alt='Booking QR Code' style='max-width: 200px; border: 1px solid #ccc; border-radius: 8px;'></div>"
                f"<p style='color: #333; text-align: center; margin-top: 20px;'>Note: Please arrive 10 minutes early to ensure a smooth appointment.</p>"
                f"<p style='color: #333; text-align: center; margin-top: 20px;'>If you need to cancel, please contact the pet shop ASAP.</p>"
                f"<p style='color: #333; text-align: center; margin-top: 20px;'>Thank you for choosing Little Heart Pet Shop!</p></td></tr>"
                f"</table></td></tr></table></body></html>"
            )

            msg = MIMEMultipart()
            msg['Subject'] = 'Your Appointment Confirmation'
            msg['From'] = settings.EMAIL_HOST_USER
            msg['To'] = email or settings.DEFAULT_FROM_EMAIL
            # msg['To'] = email
            # msg['Bcc'] = "magarsafal16@gmail.com"
            # msg['To'] = ", ".join([email, "magarsafal16@gmail.com"])
            msg.attach(MIMEText(html_message, 'html'))

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
                logger.info(f"Confirmation email sent for booking {booking.id}")
            except Exception as e:
                logger.error(f"Email send failed: {e}")
                messages.warning(request, f"Booking saved but email failed to send: {str(e)}")

            messages.success(request, f"Appointment booked successfully. QR code sent to {email}")
            return redirect("calendarapp:calendar")

        else:
            messages.error(request, "Invalid form data submitted.")
            logger.warning(f"Form errors: {forms.errors}")
            return self.get(request, *args, **kwargs)



@login_required
def delete_booking(request, booking_id):
    booking = get_object_or_404(UnifiedBooking, id=booking_id)
    
    if request.method == 'POST':
        # Directly perform soft delete without permission check
        booking.is_deleted = True
        booking.save()
        return JsonResponse({'message': 'Booking successfully deleted.'})
    
    return JsonResponse({'message': 'Invalid request method.'}, status=400)


def next_week(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == 'POST':
        next_event = Event(
            user=event.user,
            size=event.size,
            booking_date=event.booking_date + timedelta(days=7),
            booking_time=event.booking_time,
            service_type=event.service_type,
            addons=event.addons
        )
        next_event.save()
        return JsonResponse({'message': 'Success!'})
    else:
        return JsonResponse({'message': 'Error!'}, status=400)
    


@require_POST
@login_required
def next_month(request, booking_id):
    try:
        booking = get_object_or_404(UnifiedBooking, id=booking_id, is_deleted=False)

        # Calculate the new datetime (same day and time, next month)
        current_datetime = booking.date_time
        # Add one month; handle varying month lengths and leap years
        next_month_datetime = current_datetime + timedelta(days=30)  # Approximate 1 month
        # Adjust to the same day of the next month if possible
        target_day = current_datetime.day
        next_month_datetime = next_month_datetime.replace(day=1)  # Start at first of next month
        days_in_next_month = calendar.monthrange(next_month_datetime.year, next_month_datetime.month)[1]
        # Use the same day if possible, otherwise use the last day of the month
        new_day = min(target_day, days_in_next_month)
        next_month_datetime = next_month_datetime.replace(day=new_day)

        # Preserve the original time
        next_month_datetime = next_month_datetime.replace(
            hour=current_datetime.hour,
            minute=current_datetime.minute,
            second=current_datetime.second
        )

        # Check for slot availability
        if not is_slot_available_with_duration(
            next_month_datetime,
            booking.service_type,
            booking.size,
            booking.add_ons
        ):
            return JsonResponse(
                {'message': 'The selected time slot in the next month is already booked.'},
                status=400
            )

        # Create a new booking with the same details
        new_booking = UnifiedBooking.objects.create(
            user=booking.user,
            size=booking.size,
            service_type=booking.service_type,
            add_ons=booking.add_ons,
            date_time=next_month_datetime,
            booking_type=booking.booking_type,
            full_name=booking.full_name,
            contact_no=booking.contact_no,
            email=booking.email,
            estimated_time=booking.estimated_time,
            total_price=booking.total_price,
            status=booking.status,  # Preserve the original status
        )

        logger.info(f"New booking created for next month: {new_booking.id}")

        # Send email notification for the new booking
        service_type_display = format_service_name(new_booking.service_type)
        qr_data = (
            f"Booking ID: {new_booking.id}\n"
            f"Date & Time: {next_month_datetime.strftime('%Y-%m-%d %I:%M %p')}\n"
            f"Service Type: {service_type_display}\n"
            f"Size: {new_booking.size}\n"
            f"Status: {new_booking.status}\n"
            f"Add-ons: {', '.join(new_booking.add_ons) if new_booking.add_ons else 'None'}"
        )

        # Generate QR Code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')
        buffered = BytesIO()
        img.save(buffered, format='PNG')
        qr_code_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

        # Email Setup
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
            f"<tr><td style='padding: 10px; color: #333;'>Booking ID</td><td style='padding: 10px; color: #333;'>{new_booking.id}</td></tr>"
            f"<tr><td style='padding: 10px; color: #333;'>Date & Time</td><td style='padding: 10px; color: #333;'>{next_month_datetime.strftime('%Y-%m-%d %I:%M %p')}</td></tr>"
            f"<tr><td style='padding: 10px; color: #333;'>Service Type</td><td style='padding: 10px; color: #333;'>{service_type_display}</td></tr>"
            f"<tr><td style='padding: 10px; color: #333;'>Pet Size</td><td style='padding: 10px; color: #333;'>{new_booking.size}</td></tr>"
            f"<tr><td style='padding: 10px; color: #333;'>Total Price</td><td style='padding: 10px; color: #333;'>Rs. {new_booking.total_price}</td></tr>"
            f"<tr><td style='padding: 10px; color: #333;'>Status</td><td style='padding: 10px; color: #333;'>{new_booking.status}</td></tr>"
            f"<tr><td style='padding: 10px; color: #333;'>Add-ons</td><td style='padding: 10px; color: #333;'>{', '.join(new_booking.add_ons) if new_booking.add_ons else 'None'}</td></tr>"
            f"</table>"
            f"<div style='text-align: center; margin-top: 20px;'><img src='cid:booking_qr' alt='Booking QR Code' style='max-width: 200px; border: 1px solid #ccc; border-radius: 8px;'></div>"
            f"<p style='color: #333; text-align: center; margin-top: 20px;'>Note: Please arrive 10 minutes early to ensure a smooth appointment.</p>"
            f"<p style='color: #333; text-align: center; margin-top: 20px;'>If you need to cancel, please contact the pet shop ASAP.</p>"
            f"<p style='color: #333; text-align: center; margin-top: 20px;'>Thank you for choosing Little Heart Pet Shop!</p></td></tr>"
            f"</table></td></tr></table></body></html>"
        )

        msg = MIMEMultipart()
        msg['Subject'] = 'New Booking Confirmation'
        msg['From'] = settings.EMAIL_HOST_USER
        msg['To'] = new_booking.email or settings.DEFAULT_FROM_EMAIL
        msg.attach(MIMEText(html_message, 'html'))

        img_data = base64.b64decode(qr_code_base64)
        image = MIMEImage(img_data, name=f"booking_qr_{new_booking.id}.png")
        image.add_header('Content-ID', '<booking_qr>')
        image.add_header('Content-Disposition', 'inline', filename=f"booking_qr_{new_booking.id}.png")
        msg.attach(image)

        try:
            with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
                server.starttls()
                server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                server.send_message(msg)
            logger.info(f"Confirmation email sent for new booking {new_booking.id}")
        except Exception as e:
            logger.error(f"Email send failed for new booking {new_booking.id}: {e}")
            return JsonResponse(
                {'message': 'New booking created successfully, but email failed to send.'},
                status=200
            )

        return JsonResponse({'message': 'New booking successfully created for the next month.'})

    except UnifiedBooking.DoesNotExist:
        return JsonResponse({'message': 'Original booking not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'message': f'Error: {str(e)}'}, status=500)



@require_POST
@login_required
def next_day(request, booking_id):
    try:
        booking = get_object_or_404(UnifiedBooking, id=booking_id, is_deleted=False)

        # Calculate the new datetime (next day, same time)
        current_datetime = booking.date_time
        next_day_datetime = current_datetime + timedelta(days=1)

        # Check for slot availability
        if not is_slot_available_with_duration(
            next_day_datetime,
            booking.service_type,
            booking.size,
            booking.add_ons
        ):
            return JsonResponse(
                {'message': 'The selected time slot on the next day is already booked.'},
                status=400
            )

        # Update the booking's date_time while preserving other fields
        booking.date_time = next_day_datetime
        booking.save()

        logger.info(f"Booking rescheduled to next day: {booking.id}")

        # === QR Code Data ===
        service_type_display = format_service_name(booking.service_type)
        qr_data = (
            f"Booking ID: {booking.id}\n"
            f"Date & Time: {next_day_datetime.strftime('%Y-%m-%d %I:%M %p')}\n"
            f"Service Type: {service_type_display}\n"
            f"Size: {booking.size}\n"
            f"Status: {booking.status}\n"
            f"Add-ons: {', '.join(booking.add_ons) if booking.add_ons else 'None'}"
        )

        # === Generate QR Code ===
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')  # Fixed from qrcode.make_image
        buffered = BytesIO()
        img.save(buffered, format='PNG')
        qr_code_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

        # === Email Setup ===
        html_message = (
            f"<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Booking Rescheduled Confirmation</title></head>"
            f"<body style='font-family: Arial, sans-serif; color: #333; background-color: #f9f9f9; padding: 20px;'>"
            f"<table width='100%' cellpadding='0' cellspacing='0' border='0'><tr><td align='center'>"
            f"<table width='600' cellpadding='0' cellspacing='0' border='0' style='background-color: #ffffff; border: 1px solid #ddd; border-radius: 5px;'>"
            f"<tr><td style='background-color: #D84315; color: #ffffff; padding: 10px 20px; text-align: center; border-top-left-radius: 5px; border-top-right-radius: 5px;'>"
            f"<h1 style='margin: 0;'>Booking Rescheduled Confirmation</h1></td></tr><tr><td style='padding: 20px;'>"
            f"<table width='100%' cellpadding='10' cellspacing='0' border='1' style='border-collapse: collapse; margin: 10px 0;'>"
            f"<tr style='background-color: #f2f2f2;'><th style='text-align: left; padding: 10px; color: #333;'>Detail</th>"
            f"<th style='text-align: left; padding: 10px; color: #333;'>Information</th></tr>"
            f"<tr><td style='padding: 10px; color: #333;'>Booking ID</td><td style='padding: 10px; color: #333;'>{booking.id}</td></tr>"
            f"<tr><td style='padding: 10px; color: #333;'>Date & Time</td><td style='padding: 10px; color: #333;'>{next_day_datetime.strftime('%Y-%m-%d %I:%M %p')}</td></tr>"
            f"<tr><td style='padding: 10px; color: #333;'>Service Type</td><td style='padding: 10px; color: #333;'>{service_type_display}</td></tr>"
            f"<tr><td style='padding: 10px; color: #333;'>Pet Size</td><td style='padding: 10px; color: #333;'>{booking.size}</td></tr>"
            f"<tr><td style='padding: 10px; color: #333;'>Total Price</td><td style='padding: 10px; color: #333;'>Rs. {booking.total_price}</td></tr>"
            f"<tr><td style='padding: 10px; color: #333;'>Status</td><td style='padding: 10px; color: #333;'>{booking.status}</td></tr>"
            f"<tr><td style='padding: 10px; color: #333;'>Add-ons</td><td style='padding: 10px; color: #333;'>{', '.join(booking.add_ons) if booking.add_ons else 'None'}</td></tr>"
            f"</table>"
            f"<div style='text-align: center; margin-top: 20px;'><img src='cid:booking_qr' alt='Booking QR Code' style='max-width: 200px; border: 1px solid #ccc; border-radius: 8px;'></div>"
            f"<p style='color: #333; text-align: center; margin-top: 20px;'>Note: Please arrive 10 minutes early to ensure a smooth appointment.</p>"
            f"<p style='color: #333; text-align: center; margin-top: 20px;'>If you need to cancel, please contact the pet shop ASAP.</p>"
            f"<p style='color: #333; text-align: center; margin-top: 20px;'>Thank you for choosing Little Heart Pet Shop!</p></td></tr>"
            f"</table></td></tr></table></body></html>"
        )

        msg = MIMEMultipart()
        msg['Subject'] = 'Booking Rescheduled Confirmation'
        msg['From'] = settings.EMAIL_HOST_USER
        msg['To'] = booking.email or settings.DEFAULT_FROM_EMAIL
        msg.attach(MIMEText(html_message, 'html'))

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
            logger.info(f"Reschedule email sent for booking {booking.id}")
        except Exception as e:
            logger.error(f"Email send failed for booking {booking.id}: {e}")
            messages.warning(request, f"Booking rescheduled successfully, but email failed to send: {str(e)}")
            return JsonResponse(
                {'message': 'Booking successfully rescheduled to the next day, but email failed to send.'},
                status=200
            )

        messages.success(request, f"Booking successfully rescheduled to the next day. Confirmation sent to {booking.email or settings.DEFAULT_FROM_EMAIL}")
        return JsonResponse({'message': 'Booking successfully rescheduled to the next day.'})

    except UnifiedBooking.DoesNotExist:
        return JsonResponse({'message': 'Booking not found.'}, status=404)
    except Exception as e:
        logger.error(f"Error in next_day view for booking {booking_id}: {str(e)}")
        return JsonResponse({'message': f'Error: {str(e)}'}, status=500)


@login_required
def book_unified_appointment(request):
    form = EventForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            booking_date = form.cleaned_data["booking_date"]
            booking_time = form.cleaned_data["booking_time"]

            # Check for time slot conflict in UnifiedBooking (not Event anymore)
            if not is_slot_available(booking_date, booking_time):
                messages.error(request, "This time slot is already booked. Please choose another.")
                return redirect("calendarapp:calendar")

            UnifiedBooking.objects.create(
                user=request.user,
                size=form.cleaned_data["size"],
                booking_date=booking_date,
                booking_time=booking_time,
                service_type=form.cleaned_data["service_type"],
                addons=form.cleaned_data["addons"],
                source='admin' if request.user.is_staff else 'frontend'
            )

            messages.success(request, "Appointment booked successfully.")
            return redirect("calendarapp:calendar")  # or wherever you want to send them

    return render(request, "calendarapp/unified_booking.html", {"form": form})
    