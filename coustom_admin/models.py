from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.db.models import F, Q, Sum

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
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='warden_profile',
        primary_key=True
    )
    name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=11)
    gender = models.CharField(max_length=10)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def email(self):
        return self.user.email

class HostelWardens(models.Model):
    hostel = models.ForeignKey(Hostels, on_delete=models.CASCADE)
    warden = models.ForeignKey(Wardens, on_delete=models.CASCADE)

class RoomTypeRate(models.Model):
    hostel = models.ForeignKey(Hostels, on_delete=models.CASCADE)
    room_type = models.CharField(max_length=20, choices=[('Single', 'Single'), ('Double', 'Double'), ('Shared', 'Shared')])
    per_head_rent = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        unique_together = ('hostel', 'room_type')

    def __str__(self):
        return f"{self.hostel.name} - {self.room_type}: {self.per_head_rent}"

class Rooms(models.Model):
    ROOM_TYPES = [
        ('Single', 'Single'),
        ('Double', 'Double'),
        ('Triple', 'Triple'),
        ('Quad', 'Quad'),
    ]
    
    ROOM_STATUS = [
        ('Available', 'Available'),
        ('Occupied', 'Occupied'),
        ('Maintenance', 'Maintenance'),
    ]
    
    hostel = models.ForeignKey(Hostels, on_delete=models.CASCADE, related_name='rooms')
    room_number = models.CharField(max_length=10)
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES)
    capacity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(4)])
    current_occupants = models.PositiveIntegerField(default=0, editable=False)
    status = models.CharField(max_length=20, choices=ROOM_STATUS, default='Available')
    rent = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    description = models.TextField(blank=True, null=True)
    floor_number = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.room_number} - {self.get_room_type_display()}"
        
    @property
    def is_available(self):
        return self.current_occupants < self.capacity
    
    @property
    def available_beds(self):
        return self.capacity - self.current_occupants

    class Meta:
        verbose_name_plural = "Rooms"
        ordering = ['floor_number', 'room_number']
        unique_together = ['hostel', 'room_number']

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    contact_number = models.CharField(max_length=11)
    cnic = models.CharField(max_length=15, unique=True, help_text="Enter CNIC without dashes (e.g., 1234567890123)")
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])
    institute = models.CharField(max_length=100)
    guardian_name = models.CharField(max_length=100, blank=True, null=True)
    guardian_cnic = models.CharField(max_length=13, blank=True, null=True, help_text="Enter CNIC without dashes (e.g., 1234567890123)")
    guardian_relation = models.CharField(max_length=50, blank=True, null=True)
    guardian_contact = models.CharField(max_length=11, blank=True, null=True)
    street = models.CharField(max_length=100, blank=True, null=True)
    area = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    district = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.user.first_name} {self.user.last_name}"
class BookingRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Cancelled', 'Cancelled'),
        ('Completed', 'Completed')
    ]
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    hostel = models.ForeignKey('Hostels', on_delete=models.CASCADE, related_name='bookings')
    room_type = models.CharField(max_length=20, choices=[
        ('Single', 'Single'),
        ('Double', 'Double'),
        ('Shared', 'Shared')
    ])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    check_in_date = models.DateField()
    check_out_date = models.DateField(null=True, blank=True)
    request_date = models.DateTimeField(auto_now_add=True, help_text='When the booking was requested')

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['student'],
                condition=Q(status='Pending') | Q(status='Approved'),
                name='unique_active_booking_per_student'
            )
        ]
    updated_at = models.DateTimeField(auto_now=True)
    admin_notes = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.student.username} - {self.hostel.name} ({self.status})"
    
    @property
    def current_room(self):
        try:
            return self.room_assignment.room
        except RoomAssignment.DoesNotExist:
            return None
    
    @property
    def current_assignment(self):
        try:
            return self.room_assignment
        except RoomAssignment.DoesNotExist:
            return None
            
    @property
    def total_paid(self):
        return self.security_deposit.amount if hasattr(self, 'security_deposit') else 0
    
    @property
    def balance(self):
        return (self.total_amount or 0) - self.total_paid
        
    class Meta:
        ordering = ['-request_date']


class RoomAssignment(models.Model):
    booking = models.OneToOneField(
        BookingRequest,
        on_delete=models.CASCADE,
        related_name='room_assignment'
    )
    room = models.ForeignKey(
        Rooms,
        on_delete=models.CASCADE,
        related_name='assignments'
    )
    assigned_date = models.DateTimeField(auto_now_add=True)
    check_in_date = models.DateField(null=True, blank=True)
    check_out_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_rooms'
    )

    class Meta:
        ordering = ['-assigned_date']
        verbose_name = 'Room Assignment'
        verbose_name_plural = 'Room Assignments'
        
    def clean(self):
        # Only check for new active assignments or when reactivating an assignment
        if self.is_active:
            query = RoomAssignment.objects.filter(
                booking__student=self.booking.student,
                is_active=True
            )
            
            # If updating, exclude the current instance from the check
            if self.pk:
                query = query.exclude(pk=self.pk)
                
            if query.exists():
                raise ValidationError('This student already has an active room assignment.')
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.booking.student} - {self.room} ({self.assigned_date.date()})"

    def save(self, *args, **kwargs):
        # Set check_in_date to assigned_date if not set
        if not self.check_in_date:
            self.check_in_date = timezone.now().date()
        super().save(*args, **kwargs)
        
        # Update room occupancy
        self.update_room_occupancy()
    
    def delete(self, *args, **kwargs):
        # Mark as inactive instead of deleting
        self.is_active = False
        self.save()
        
    def update_room_occupancy(self):
        """Update the room's current_occupants count based on active assignments"""
        room = self.room
        active_assignments = room.assignments.filter(is_active=True).count()
        room.current_occupants = active_assignments
        
        # Update room status
        if room.current_occupants >= room.capacity:
            room.status = 'Occupied'
        else:
            room.status = 'Available'
            
        room.save(update_fields=['current_occupants', 'status'])
        
    def check_out(self, check_out_date=None):
        """Mark the assignment as checked out"""
        self.is_active = False
        self.check_out_date = check_out_date or timezone.now().date()
        self.save()
        # Update the booking status if needed
        self.booking.status = 'Completed'
        self.booking.save(update_fields=['status'])


class SecurityDeposit(models.Model):
    PAYMENT_METHODS = [
        ('Cash', 'Cash'),
        ('Bank Transfer', 'Bank Transfer'),
        ('JazzCash', 'JazzCash'),
        ('EasyPaisa', 'EasyPaisa'),
        ('Other', 'Other')
    ]
    
    PAYMENT_STATUS = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
        ('Refunded', 'Refunded')
    ]
    
    booking = models.OneToOneField(BookingRequest, on_delete=models.CASCADE, related_name='security_deposit')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='Completed')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_deposits')
    receipt_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            # Generate receipt number: SD-YYYYMMDD-XXXXX
            date_part = timezone.now().strftime('%Y%m%d')
            last_deposit = SecurityDeposit.objects.filter(receipt_number__startswith=f'SD-{date_part}').order_by('-id').first()
            
            if last_deposit and last_deposit.receipt_number:
                last_num = int(last_deposit.receipt_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
                
            self.receipt_number = f'SD-{date_part}-{new_num:05d}'
        
        super().save(*args, **kwargs)
    
    def verify_deposit(self, verified_by_user):
        if not self.is_verified:
            self.is_verified = True
            self.verified_by = verified_by_user
            self.verification_date = timezone.now()
            self.save()
            return True
        return False
    
    def __str__(self):
        return f"Security Deposit of {self.amount} for {self.booking}"
    
    class Meta:
        ordering = ['-payment_date']
        verbose_name = 'Security Deposit'
        verbose_name_plural = 'Security Deposits'

class MessIncharge(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='mess_incharge_profile',
        primary_key=True
    )
    name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=11)
    cnic = models.CharField(max_length=13, unique=True, blank=False, default='N/A', help_text="Enter CNIC without dashes (e.g., 1234567890123)")
    street = models.CharField(max_length=100, blank=True, null=True)
    area = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    district = models.CharField(max_length=50, blank=True, null=True)
    gender = models.CharField(max_length=10, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')])
    hostel = models.ForeignKey(Hostels, on_delete=models.CASCADE, related_name='mess_incharges')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def email(self):
        return self.user.email


class StudentMonthlyFee(models.Model):
    PAYMENT_STATUS = [
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Overdue', 'Overdue')
    ]
    
    id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='monthly_fees')
    hostel = models.ForeignKey(Hostels, on_delete=models.CASCADE, related_name='student_fees')
    month = models.PositiveIntegerField(choices=[(i, i) for i in range(1, 13)], help_text="Month of the fee (1-12)")
    year = models.PositiveIntegerField(help_text="Year of the fee")
    monthly_rent = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Monthly rent amount")
    mess_expenses = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Mess expenses for the month")
    electricity_bill = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Electricity bill for the month")
    total_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Total fee (rent + mess + electricity)")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='Pending')
    due_date = models.DateField(help_text="Due date for payment")
    payment_date = models.DateField(null=True, blank=True, help_text="Date when payment was made")
    transaction_id = models.CharField(max_length=100, blank=True, null=True, help_text="Transaction ID for payment")
    notes = models.TextField(blank=True, null=True, help_text="Additional notes about this fee")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'month', 'year')
        verbose_name = 'Student Monthly Fee'
        verbose_name_plural = 'Student Monthly Fees'
        ordering = ['-year', '-month']

    def __str__(self):
        return f"{self.student.user.get_full_name()} - Fee for {self.month}/{self.year} ({self.total_fee})"
    
    def save(self, *args, **kwargs):
        # Calculate total fee before saving
        self.total_fee = self.monthly_rent + self.mess_expenses + self.electricity_bill
        super().save(*args, **kwargs)
