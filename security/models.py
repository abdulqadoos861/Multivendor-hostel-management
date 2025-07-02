from django.db import models
from django.contrib.auth.models import User
from coustom_admin.models import Hostels
from coustom_admin.models import Student, Hostels
class SecurityGuard(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='security_profile')
    name = models.CharField(max_length=100, blank=True, null=True)
    contact_number = models.CharField(max_length=15, blank=True)
    cnic = models.CharField(max_length=15, unique=True, blank=True, help_text="Enter CNIC without dashes (e.g., 1234567890123)")
    street = models.CharField(max_length=100, blank=True)
    area = models.CharField(max_length=100, blank=True) 
    city = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], blank=True, null=True)
    hostel = models.ForeignKey(Hostels, on_delete=models.CASCADE, related_name='security_guards', blank=True, null=True)
    shift = models.CharField(max_length=20, choices=[('Morning', 'Morning'), ('Evening', 'Evening'), ('Night', 'Night')], blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name or 'Unnamed'} (Security Guard)"

    class Meta:
        verbose_name = "Security Guard"
        verbose_name_plural = "Security Guards"

class StudentMovement(models.Model):
    student = models.ForeignKey('coustom_admin.Student', on_delete=models.CASCADE, related_name='movements')
    security_guard = models.ForeignKey('SecurityGuard', on_delete=models.CASCADE, related_name='recorded_movements')
    movement_type = models.CharField(max_length=3, choices=[('IN', 'In'), ('OUT', 'Out')])
    hostel = models.ForeignKey(Hostels, on_delete=models.CASCADE, related_name='movements', blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.student} - {self.movement_type} at {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

    class Meta:
        verbose_name = "Student Movement"
        verbose_name_plural = "Student Movements"
        ordering = ['-timestamp']


class Visitor(models.Model):
    name = models.CharField(max_length=100)
    cnic = models.CharField(max_length=15, unique=False, help_text="Enter CNIC without dashes (e.g., 1234567890123)")
    contact_number = models.CharField(max_length=15)
    relationship = models.CharField(max_length=50, null=True, blank=True, help_text="Relationship to the student (e.g., Parent, Guardian)")
    purpose = models.CharField(max_length=200)
    TO_VISITED_CHOICES = (
        ('warden', 'Warden'),
        ('security_guard', 'Security Guard'),
        ('student', 'Student'),
        ('other', 'Other'),
    )
    to_visted = models.CharField(max_length=100, choices=TO_VISITED_CHOICES, default='warden', help_text="Who the visitor is visiting")
    student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True, related_name='visitors')
    timestamp = models.DateTimeField(auto_now_add=True)
    security_guard = models.ForeignKey(SecurityGuard, on_delete=models.SET_NULL, null=True, related_name='recorded_visitors')
    hostel = models.ForeignKey(Hostels, on_delete=models.SET_NULL, null=True, related_name='visitors')
    STATUS_CHOICES = (
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('pending', 'Pending'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', help_text="Status of the visit")
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} visited on {self.timestamp.strftime('%Y-%m-%d %H:%M')} - Status: {self.status.title()}"

    class Meta:
        verbose_name = "Visitor"
        verbose_name_plural = "Visitors"
        ordering = ['-timestamp']

class EmergencyAlert(models.Model):
    security_guard = models.ForeignKey(SecurityGuard, on_delete=models.SET_NULL, null=True, related_name='emergency_alerts')
    hostel = models.ForeignKey(Hostels, on_delete=models.SET_NULL, null=True, related_name='emergency_alerts')
    alert_type = models.CharField(max_length=50, choices=[
        ('fire', 'Fire Emergency'),
        ('medical', 'Medical Emergency'),
        ('security_breach', 'Security Breach'),
        ('natural_disaster', 'Natural Disaster'),
        ('other', 'Other Emergency')
    ])
    location = models.CharField(max_length=200)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('active', 'Active'),
        ('resolved', 'Resolved'),
        ('cancelled', 'Cancelled')
    ], default='active')
    notify_all = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.get_alert_type_display()} at {self.location} on {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        verbose_name = "Emergency Alert"
        verbose_name_plural = "Emergency Alerts"
        ordering = ['-timestamp']
