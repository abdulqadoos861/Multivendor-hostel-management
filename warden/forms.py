from django import forms
from django.contrib.auth.models import User
from coustom_admin.models import Student
import re

class StudentRegistrationForm(forms.Form):
    # Student Details
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    contact_number = forms.CharField(
        max_length=11,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    cnic = forms.CharField(
        max_length=15,
        required=True,
        help_text="Enter CNIC without dashes (e.g., 1234567890123)",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    street = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    area = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    district = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    gender = forms.ChoiceField(
        choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')],
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    institute = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    guardian_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    guardian_contact = forms.CharField(
        max_length=11,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    guardian_cnic = forms.CharField(
        max_length=15,
        required=False,
        help_text="Enter Guardian CNIC without dashes (e.g., 1234567890123)",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    guardian_relation = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
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

    def clean_guardian_contact(self):
        guardian_contact = self.cleaned_data['guardian_contact']
        if guardian_contact and not re.match(r'^\d{11}$', guardian_contact):
            raise forms.ValidationError("Guardian contact number must be 11 digits.")
        return guardian_contact

    def clean_guardian_cnic(self):
        guardian_cnic = self.cleaned_data['guardian_cnic']
        if guardian_cnic and not re.match(r'^\d{13}$', guardian_cnic):
            raise forms.ValidationError("Guardian CNIC must be 13 digits without dashes.")
        return guardian_cnic

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")

        return cleaned_data
