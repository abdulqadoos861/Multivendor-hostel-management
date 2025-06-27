from django.db import models
from coustom_admin.models import Hostels
from django.contrib.auth.models import User

class MessMenu(models.Model):
    menu_id = models.AutoField(primary_key=True)
    hostel_id = models.ForeignKey(Hostels, on_delete=models.CASCADE, related_name='mess_menus')
    day_of_week = models.CharField(max_length=10, choices=[
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
    ])
    meal_type = models.CharField(max_length=10, choices=[
        ('Breakfast', 'Breakfast'),
        ('Lunch', 'Lunch'),
        ('Dinner', 'Dinner'),
    ])
    items = models.JSONField(default=list, blank=True)
    week_start_date = models.DateField(null=True, blank=True, help_text="Start date of the week for this menu")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_menus')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('hostel_id', 'day_of_week', 'meal_type', 'week_start_date')
        verbose_name = 'Mess Menu'
        verbose_name_plural = 'Mess Menus'
    
    def __str__(self):
        return f"{self.day_of_week} {self.meal_type} Menu for {self.hostel_id.name}"


class Expenses(models.Model):
    expense_id = models.AutoField(primary_key=True)
    hostel_id = models.ForeignKey(Hostels, on_delete=models.CASCADE, related_name='mess_expenses')
    description = models.CharField(max_length=255, help_text="Description of the expense (e.g., Food Supplies, Utilities)")
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount spent")
    date_incurred = models.DateField(help_text="Date when the expense was incurred")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_expenses')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    receipt = models.FileField(upload_to='expenses_receipts/', null=True, blank=True, help_text="Upload receipt or proof of expense")

    class Meta:
        verbose_name = 'Expense'
        verbose_name_plural = 'Expenses'

    def __str__(self):
        return f"{self.description} - {self.amount} on {self.date_incurred} for {self.hostel_id.name}"


class MessStudent(models.Model):
    id = models.AutoField(primary_key=True)
    student = models.ForeignKey('coustom_admin.Student', on_delete=models.CASCADE, related_name='mess_enrollments')
    hostel = models.ForeignKey('coustom_admin.Hostels', on_delete=models.CASCADE, related_name='mess_students')
    enrolled_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='enrolled_mess_students')
    enrollment_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True, help_text="Indicates if the student is currently enrolled for mess services")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'hostel')
        verbose_name = 'Mess Student'
        verbose_name_plural = 'Mess Students'

    def __str__(self):
        return f"{self.student.user.get_full_name()} - Mess Enrollment for {self.hostel.name}"


class MessAttendance(models.Model):
    id = models.AutoField(primary_key=True)
    hostel = models.ForeignKey(Hostels, on_delete=models.CASCADE, related_name='mess_attendances')
    mess_student = models.ForeignKey(MessStudent, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(help_text="Date of attendance")
    breakfast = models.BooleanField(default=False, help_text="Attendance for Breakfast")
    lunch = models.BooleanField(default=False, help_text="Attendance for Lunch")
    dinner = models.BooleanField(default=False, help_text="Attendance for Dinner")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('mess_student', 'date')
        verbose_name = 'Mess Attendance'
        verbose_name_plural = 'Mess Attendances'

    def __str__(self):
        return f"Attendance for {self.mess_student.student.user.get_full_name()} on {self.date} at {self.mess_student.hostel.name}"


class MessCharges(models.Model):
    id = models.AutoField(primary_key=True)
    hostel = models.ForeignKey(Hostels, on_delete=models.CASCADE, related_name='mess_charges')
    breakfast_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0.00, help_text="Daily charge for breakfast")
    lunch_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0.00, help_text="Daily charge for lunch")
    dinner_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0.00, help_text="Daily charge for dinner")
    effective_from = models.DateField(help_text="Date from which these rates are effective")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_mess_charges')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Mess Charge'
        verbose_name_plural = 'Mess Charges'
        ordering = ['-effective_from']

    def __str__(self):
        return f"Mess Charges for {self.hostel.name} effective from {self.effective_from}"
