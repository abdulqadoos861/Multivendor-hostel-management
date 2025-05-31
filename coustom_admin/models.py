from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
# Create your models here.
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

class bookingRequest(models.Model):
    user_id = models.ForeignKey(User,on_delete=models.CASCADE)
    hostel_id = models.ForeignKey(Hostels,on_delete=models.CASCADE)
    room_type = models.CharField(default="Single", choices=[('Single', 'Single'), ('Double', 'Double')])
    request_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(default="Pending", choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')])
