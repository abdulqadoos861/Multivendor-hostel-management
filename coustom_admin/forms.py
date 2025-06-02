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


import logging
logger = logging.getLogger(__name__)

class BookingRequestForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        # Pop custom parameters before calling parent's __init__
        self.user = kwargs.pop('user', None)
        
        # Call parent's __init__ without our custom parameters
        super().__init__(*args, **kwargs)
        
        # Set initial dates
        today = timezone.now().date()
        self.fields['check_in_date'].initial = today
        self.fields['check_out_date'].initial = today + timedelta(days=30)
        
        # Set querysets
        self.fields['hostel'].queryset = Hostels.objects.all()
        
        # Check if user is staff
        is_staff = self.user and (self.user.is_staff or hasattr(self.user, 'warden'))
        
        # Add student field
        if is_staff:
            # For staff, show student dropdown
            self.fields['student'] = forms.ModelChoiceField(
                queryset=Student.objects.all(),
                required=True,
                label='Student',
                widget=forms.Select(attrs={'class': 'form-control'}),
                empty_label='Select a student'
            )
            
            # Set initial student from POST data if available
            if self.data and 'student' in self.data:
                try:
                    student_id = int(self.data.get('student'))
                    self.initial['student'] = Student.objects.get(id=student_id)
                except (ValueError, TypeError, Student.DoesNotExist):
                    pass
        elif hasattr(self.user, 'student'):
            # For students, set their student instance
            self.fields['student'] = forms.ModelChoiceField(
                queryset=Student.objects.filter(id=self.user.student.id),
                required=True,
                widget=forms.HiddenInput()
            )
            # Always set the student to the current user's student profile
            self.initial['student'] = self.user.student
            
            # Also set it in data if this is a POST request
            if self.data and hasattr(self.data, '_mutable'):
                self.data = self.data.copy()
                self.data['student'] = self.user.student
        
        # Add required attribute to required fields
        for field_name, field in self.fields.items():
            if field.required:
                field.widget.attrs['required'] = 'required'

    class Meta:
        model = BookingRequest
        fields = ['student', 'hostel', 'room_type', 'check_in_date', 'check_out_date', 'message']
        widgets = {
            'check_in_date': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control'
                }
            ),
            'check_out_date': forms.DateInput(
                attrs={
                    'type': 'date',
                    'class': 'form-control'
                }
            ),
            'hostel': forms.Select(attrs={'class': 'form-control'}),
            'room_type': forms.Select(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={
                'rows': 3, 
                'class': 'form-control',
                'placeholder': 'Any special requests or additional information...',
                'required': False
            }),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set initial dates
        today = timezone.now().date()
        self.fields['check_in_date'].initial = today
        self.fields['check_out_date'].initial = today + timedelta(days=30)
        
        # Set querysets
        self.fields['hostel'].queryset = Hostels.objects.all()
        
        # Add required attribute to required fields
        for field_name, field in self.fields.items():
            if field.required:
                field.widget.attrs['required'] = 'required'

    def clean(self):
        cleaned_data = super().clean()
        check_in_date = cleaned_data.get('check_in_date')
        check_out_date = cleaned_data.get('check_out_date')
        
        logger.debug(f"Form cleaned data: {cleaned_data}")
        
        if check_in_date and check_out_date:
            today = timezone.now().date()
            if check_in_date < today:
                self.add_error('check_in_date', 'Check-in date cannot be in the past.')
            if check_out_date <= check_in_date:
                self.add_error('check_out_date', 'Check-out date must be after check-in date.')
        
        return cleaned_data
    
    def save(self, commit=True):
        try:
            booking = super().save(commit=False)
            if self.user and hasattr(self.user, 'student'):
                booking.student = self.user.student
            booking.status = 'Pending'
            if commit:
                booking.save()
            return booking
        except Exception as e:
            logger.exception("Error saving booking:")
            raise