from django import forms
from django.contrib.auth.models import User
from coustom_admin.models import Student, Hostels, BookingRequest
from django.utils import timezone
import re
from datetime import timedelta

class StudentRegistrationForm(forms.Form):
    # Student Details
    username = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    contact_number = forms.CharField(max_length=11, required=True)
    cnic = forms.CharField(max_length=15, required=True, help_text="Enter CNIC without dashes (e.g., 1234567890123)")
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}), required=True)
    gender = forms.ChoiceField(choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], required=True)
    institute = forms.CharField(max_length=100, required=True)
    
    # Booking Details
    apply_for_booking = forms.BooleanField(
        required=False,
        initial=False,
        label='Apply for Hostel Booking',
        widget=forms.CheckboxInput(attrs={'id': 'apply_booking_checkbox'})
    )
    hostel = forms.ModelChoiceField(
        queryset=Hostels.objects.all(),
        required=False,
        label='Hostel',
        widget=forms.Select(attrs={'class': 'form-control booking-field', 'disabled': 'disabled'})
    )
    room_type = forms.ChoiceField(
        choices=[],
        required=False,
        label='Room Type',
        widget=forms.Select(attrs={'class': 'form-control booking-field', 'disabled': 'disabled'})
    )
    check_in_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control booking-field', 'disabled': 'disabled'})
    )
    check_out_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control booking-field', 'disabled': 'disabled'})
    )
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control booking-field', 'disabled': 'disabled', 
                                   'placeholder': 'Any special requests or additional information...'})
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean_contact_number(self):
        contact_number = self.cleaned_data['contact_number']
        if not re.match(r'^\d{11}$', contact_number):
            raise forms.ValidationError("Contact number must be 11 digits.")
        return contact_number

    def clean_cnic(self):
        cnic = self.cleaned_data['cnic']
        if not re.match(r'^\d{13}$', cnic):
            raise forms.ValidationError("CNIC must be 13 digits without dashes.")
        if Student.objects.filter(cnic=cnic).exists():
            raise forms.ValidationError("This CNIC is already registered.")
        return cnic

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")

        return cleaned_data


class BookingRequestForm(forms.ModelForm):
    class Meta:
        model = BookingRequest
        fields = ['hostel', 'room_type', 'check_in_date', 'check_out_date', 'message']
        widgets = {
            'check_in_date': forms.DateInput(attrs={'type': 'date'}),
            'check_out_date': forms.DateInput(attrs={'type': 'date'}),
            'message': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Any special requests or additional information...'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['hostel'].queryset = Hostels.objects.all()
        self.fields['check_in_date'].initial = timezone.now().date()
        self.fields['check_out_date'].initial = (timezone.now() + timedelta(days=30)).date()

    def clean(self):
        cleaned_data = super().clean()
        check_in_date = cleaned_data.get('check_in_date')
        check_out_date = cleaned_data.get('check_out_date')
        
        if check_in_date and check_out_date:
            if check_in_date < timezone.now().date():
                self.add_error('check_in_date', 'Check-in date cannot be in the past.')
            if check_out_date <= check_in_date:
                self.add_error('check_out_date', 'Check-out date must be after check-in date.')
        
        return cleaned_data