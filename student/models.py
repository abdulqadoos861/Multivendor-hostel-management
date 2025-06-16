from django.db import models
from django.contrib.auth.models import User
from coustom_admin.models import Hostels, BookingRequest

class RoomChangeRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Cancelled', 'Cancelled'),
    ]
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='room_change_requests')
    current_booking = models.ForeignKey(BookingRequest, on_delete=models.CASCADE, related_name='change_requests')
    requested_hostel = models.ForeignKey(Hostels, on_delete=models.CASCADE, null=True, blank=True, related_name='room_change_requests')
    requested_room_type = models.CharField(max_length=20, choices=[
        ('Single', 'Single'),
        ('Double', 'Double'),
        ('Shared', 'Shared')
    ])
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    request_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    admin_notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Room Change Request by {self.student.username} on {self.request_date.strftime('%Y-%m-%d')}"
    
    class Meta:
        ordering = ['-request_date']

class Complaint(models.Model):
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('In Progress', 'In Progress'),
        ('Resolved', 'Resolved'),
    ]
    
    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
    ]
    
    CATEGORY_CHOICES = [
        ('Maintenance', 'Maintenance'),
        ('Cleanliness', 'Cleanliness'),
        ('Other', 'Other'),
    ]
    
    complaint_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='complaints')
    hostel = models.ForeignKey(Hostels, on_delete=models.CASCADE, related_name='complaints', null=True, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    title = models.CharField(max_length=100)
    description = models.TextField()
    submitted_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='complaints_submitted_to')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Medium')
    submitted_to = models.CharField(max_length=10, choices=[('Admin', 'Admin'), ('Warden', 'Warden')], default='Admin')
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_complaints')
    
    def __str__(self):
        return f"Complaint #{self.complaint_id} by {self.user.username} - {self.title} on {self.created_at.strftime('%Y-%m-%d')}"
    
    class Meta:
        ordering = ['-created_at']
