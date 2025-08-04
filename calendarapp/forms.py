from django import forms
from django.forms import ModelForm, DateInput
from calendarapp.models import Event, EventMember




class EventForm(ModelForm):
    customer_name = forms.CharField(max_length=255)
    customer_phone = forms.CharField(max_length=20)
    customer_email = forms.EmailField()
    class Meta:
        model = Event
        fields = ["size", "booking_date", "booking_time", "service_type", "addons"]
        widgets = {
            "size": forms.Select(
                attrs={"class": "form-control"}
            ),
            "booking_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "booking_time": forms.TimeInput(
                attrs={"type": "time", "class": "form-control"}
            ),
            "service_type": forms.Select(
                attrs={"class": "form-control"}
            ),
            "addons": forms.CheckboxSelectMultiple(),
        }


class AddMemberForm(forms.ModelForm):
    class Meta:
        model = EventMember
        fields = ["user"]

