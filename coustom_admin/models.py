from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Hostels(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField(max_length=250)
    gender = models.CharField(default="Male", choices=[('Male', 'Male'), ('Female', 'Female')])
    contact_number = models.CharField(max_length=11)
    total_floors = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Wardens(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=11)
    gender = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class HostelWardens(models.Model):
    hostel = models.ForeignKey(Hostels, on_delete=models.CASCADE)
    warden = models.ForeignKey(Wardens, on_delete=models.CASCADE)

class RoomTypeRate(models.Model):
    hostel = models.ForeignKey(Hostels, on_delete=models.CASCADE)
    room_type = models.CharField(max_length=20, choices=[('Single', 'Single'), ('Double', 'Double'), ('Shared', 'Shared')])
    per_head_rent = models.IntegerField()
    
    class Meta:
        unique_together = ('hostel', 'room_type')

    def __str__(self):
        return f"{self.hostel.name} - {self.room_type}: {self.per_head_rent}"

class Rooms(models.Model):
    hostel_id = models.ForeignKey(Hostels, on_delete=models.CASCADE)
    room_number = models.CharField(max_length=50, unique=True)
    floor_number = models.IntegerField(default=0)
    room_type = models.CharField(max_length=20, choices=[('Single', 'Single'), ('Double', 'Double'), ('Shared', 'Shared')])
    capacity = models.IntegerField()
    current_occupants = models.IntegerField(default=0)
    rent = models.IntegerField(null=True, blank=True)  # Nullable for auto-calculation
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=[('Available', 'Available'), ('Occupied', 'Occupied')], default='Available')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.room_number} ({self.hostel_id.name})"

class bookingRequest(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    hostel_id = models.ForeignKey(Hostels, on_delete=models.CASCADE)
    room_type = models.CharField(default="Single", choices=[('Single', 'Single'), ('Double', 'Double'), ('Shared', 'Shared')])
    request_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(default="Pending", choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')])