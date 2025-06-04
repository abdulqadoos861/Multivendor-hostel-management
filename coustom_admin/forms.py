from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import F
import re
import logging
from .models import Student, Hostels, BookingRequest, RoomAssignment, Rooms

logger = logging.getLogger(__name__)

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
    class Meta:
        model = BookingRequest
        fields = ['student', 'hostel', 'room_type', 'check_in_date', 'check_out_date', 'admin_notes']
        widgets = {
            'check_in_date': forms.DateInput(attrs={'type': 'date'}),
            'check_out_date': forms.DateInput(attrs={'type': 'date'}),
            'admin_notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'student': forms.HiddenInput(),
        }
    
    def __init__(self, *args, **kwargs):
        # Pop custom parameters before calling parent's __init__
        self.user = kwargs.pop('user', None)
        hostel_id = kwargs.pop('hostel_id', None)
        
        # Call parent's __init__ without our custom parameters
        super().__init__(*args, **kwargs)
        
        # Set initial values and filter hostels if needed
        if hostel_id:
            self.fields['hostel'].queryset = Hostels.objects.filter(id=hostel_id)
            
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if field_name != 'admin_notes':  # Already has form-control class
                field.widget.attrs['class'] = 'form-control'
                
    def clean(self):
        cleaned_data = super().clean()
        check_in_date = cleaned_data.get('check_in_date')
        check_out_date = cleaned_data.get('check_out_date')
        student = cleaned_data.get('student')
        
        # Validate check-in and check-out dates
        if check_in_date and check_out_date and check_in_date >= check_out_date:
            self.add_error('check_out_date', 'Check-out date must be after check-in date')
            
        # Check if student already has an active room assignment
        if student:
            from .models import RoomAssignment
            active_assignment = RoomAssignment.objects.filter(
                booking__student=student,
                is_active=True
            ).exists()
            
            if active_assignment:
                self.add_error(None, 'This student already has an active room assignment and cannot book another room.')
            
        return cleaned_data


class RoomAssignmentForm(forms.ModelForm):
    class Meta:
        model = RoomAssignment
        fields = ['room', 'check_in_date', 'check_out_date', 'notes']
        widgets = {
            'room': forms.Select(attrs={'class': 'form-control'}),
            'check_in_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'check_out_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.booking = kwargs.pop('booking', None)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.booking:
            # Only show available rooms of the requested type
            self.fields['room'].queryset = Rooms.objects.filter(
                hostel=self.booking.hostel,
                room_type=self.booking.room_type,
                status='Available',
                current_occupants__lt=F('capacity')
            )
            
            # Set initial check-in date from booking if not set
            if not self.instance.pk and not self.data.get('check_in_date'):
                self.initial['check_in_date'] = self.booking.check_in_date
        
        # Set initial dates if not set
        if not self.instance.pk and not self.initial.get('check_in_date'):
            self.initial['check_in_date'] = timezone.now().date()
        
        # Make check_out_date not required
        self.fields['check_out_date'].required = False
        
        # Set assigned_by to current user if available
        if user and user.is_authenticated:
            self.fields['assigned_by'] = forms.ModelChoiceField(
                queryset=User.objects.filter(id=user.id),
                widget=forms.HiddenInput(),
                initial=user.id
            )
        
        # Add required attribute to required fields
        for field_name, field in self.fields.items():
            if field.required and field_name != 'check_out_date':  # Skip check_out_date
                field.widget.attrs['required'] = 'required'

    def clean(self):
        cleaned_data = super().clean()
        room = cleaned_data.get('room')
        check_in_date = cleaned_data.get('check_in_date')
        check_out_date = cleaned_data.get('check_out_date')
        
        if check_in_date and check_out_date and check_in_date >= check_out_date:
            self.add_error('check_out_date', 'Check-out date must be after check-in date')
            
        if room and room.current_occupants >= room.capacity:
            self.add_error('room', 'Selected room is already full')
            
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set the booking if not set
        if not instance.booking_id and hasattr(self, 'booking'):
            instance.booking = self.booking
            
        if commit:
            instance.save()
            
            # Update room occupancy if needed
            if instance.room:
                instance.room.current_occupants = instance.room.assignments.filter(
                    is_active=True
                ).count()
                instance.room.save(update_fields=['current_occupants'])
        
        return instance