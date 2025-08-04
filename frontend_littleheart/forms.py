from django import forms
from .models import Contact

class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['name', 'email', 'phone', 'subject', 'message']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4, 'class': 'form-control border-danger'}),
            'phone': forms.TextInput(attrs={'class': 'form-control border-danger'}),
        }

    def __init__(self, *args, **kwargs):
        super(ContactForm, self).__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name not in ['message', 'phone']:
                field.widget.attrs.update({'class': 'form-control border-danger'})