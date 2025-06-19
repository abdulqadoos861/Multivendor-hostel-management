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
