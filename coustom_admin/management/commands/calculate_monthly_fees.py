from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models
from django.db.models import Count, Sum
from coustom_admin.models import Student, Hostels, RoomAssignment, RoomTypeRate, StudentMonthlyFee
from messincharge.models import MessAttendance, MessCharges, MessStudent
from datetime import datetime, date
from decimal import Decimal
import calendar

class Command(BaseCommand):
    help = 'Calculate and store monthly fees for students including rent, mess expenses, and electricity bills'

    def add_arguments(self, parser):
        parser.add_argument('--month', type=int, help='Month for which to calculate fees (1-12). Defaults to previous month if not specified.')
        parser.add_argument('--year', type=int, help='Year for which to calculate fees. Defaults to current year if not specified.')
        parser.add_argument('--electricity', type=int, default=0, help='Electricity bill amount to apply for all students. Default is 0.')
        parser.add_argument('--hostel', type=int, help='Hostel ID for which to calculate fees. If not specified, fees for all hostels will be calculated.')

    def handle(self, *args, **options):
        # Determine the month and year to process
        now = datetime.now()
        month = options.get('month', now.month - 1 if now.month > 1 else 12)
        year = now.year  # Always use current year
        electricity_bill = options.get('electricity', 0.0)

        if month < 1 or month > 12:
            self.stdout.write(self.style.ERROR(f"Invalid month: {month}. Month must be between 1 and 12."))
            return

        # Check if the selected month is not the previous month of the current year
        selected_date = date(year, month, 1)
        current_date = date(now.year, now.month, 1)
        previous_month_date = date(now.year, now.month - 1, 1) if now.month > 1 else date(now.year - 1, 12, 1)
        if selected_date >= current_date:
            self.stdout.write(self.style.ERROR(f"Cannot calculate fees for current or future months. Selected: {month}/{year}"))
            return
        elif selected_date != previous_month_date:
            self.stdout.write(self.style.ERROR(f"Can only calculate fees for the previous month. Selected: {month}/{year}"))
            return

        self.stdout.write(self.style.SUCCESS(f"Calculating monthly fees for {month}/{year}..."))

        # Get all students with active room assignments
        hostel_id = options.get('hostel')
        if hostel_id:
            hostels = Hostels.objects.filter(id=hostel_id)
        else:
            hostels = Hostels.objects.all()
        
        processed_students = 0
        created_fees = 0

        for hostel in hostels:
            # Check if any fee records already exist for this hostel for the specified month/year
            if StudentMonthlyFee.objects.filter(hostel=hostel, month=month, year=year).exists():
                self.stdout.write(self.style.WARNING(f"Fee records already exist for hostel {hostel.name} for {month}/{year}. Skipping this hostel."))
                continue

            active_assignments = RoomAssignment.objects.filter(is_active=True, room__hostel=hostel)
            for assignment in active_assignments:
                student = assignment.booking.student.student

                # Check if fee record already exists for this student for the specified month/year
                if StudentMonthlyFee.objects.filter(student=student, month=month, year=year).exists():
                    self.stdout.write(self.style.WARNING(f"Fee record already exists for {student.user.get_full_name()} for {month}/{year}. Skipping."))
                    continue

            # Calculate monthly rent
            room_type = assignment.room.room_type
            if room_type == 'Triple' or room_type == 'Quad':
                room_type = 'Shared'  # Map to Shared for rate lookup
            try:
                rate = RoomTypeRate.objects.get(hostel=hostel, room_type=room_type)
                monthly_rent = int(rate.per_head_rent)
            except RoomTypeRate.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"No rate found for {room_type} in {hostel.name} for {student.user.get_full_name()}. Using room rent."))
                monthly_rent = int(assignment.room.rent)

            # Calculate mess expenses
            try:
                mess_student = MessStudent.objects.get(student=student, hostel=hostel, is_active=True)
                # Get attendance records for the specified month/year
                last_day = calendar.monthrange(year, month)[1]
                start_date = date(year, month, 1)
                end_date = date(year, month, last_day)
                attendance_records = MessAttendance.objects.filter(
                    mess_student=mess_student,
                    date__range=[start_date, end_date]
                ).aggregate(
                    breakfast_count=Sum('breakfast', output_field=models.IntegerField()),
                    lunch_count=Sum('lunch', output_field=models.IntegerField()),
                    dinner_count=Sum('dinner', output_field=models.IntegerField())
                )

                breakfast_count = attendance_records['breakfast_count'] or 0
                lunch_count = attendance_records['lunch_count'] or 0
                dinner_count = attendance_records['dinner_count'] or 0

                # Get the latest mess charges effective for the month
                try:
                    charges = MessCharges.objects.filter(
                        hostel=hostel,
                        effective_from__lte=end_date
                    ).order_by('-effective_from').first()
                    if charges:
                        mess_expenses = int(
                            breakfast_count * 60 +
                            lunch_count * 60 +
                            dinner_count * 60
                        )
                    else:
                        self.stdout.write(self.style.WARNING(f"No mess charges found for {hostel.name} for {student.user.get_full_name()}. Setting mess expenses to 0."))
                        mess_expenses = 0
                except MessCharges.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"No mess charges found for {hostel.name} for {student.user.get_full_name()}. Setting mess expenses to 0."))
                    mess_expenses = 0
            except MessStudent.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"{student.user.get_full_name()} is not enrolled in mess for {hostel.name}. Setting mess expenses to 0."))
                mess_expenses = 0

            # Set electricity bill (manual input via argument for now)
            electricity = electricity_bill

            # Calculate due date (e.g., 10th of the next month)
            next_month = month + 1 if month < 12 else 1
            next_year = year if month < 12 else year + 1
            due_date = date(next_year, next_month, 10)

            # Create the fee record
            fee = StudentMonthlyFee(
                student=student,
                hostel=hostel,
                month=month,
                year=year,
                monthly_rent=monthly_rent,
                mess_expenses=mess_expenses,
                electricity_bill=electricity,
                due_date=due_date
            )
            fee.save()  # This will calculate total_fee automatically via the save method

            self.stdout.write(self.style.SUCCESS(f"Created fee record for {student.user.get_full_name()}: Rent={monthly_rent}, Mess={mess_expenses}, Electricity={electricity}, Total={fee.total_fee}"))
            created_fees += 1
            processed_students += 1

        self.stdout.write(self.style.SUCCESS(f"Processed {processed_students} students. Created {created_fees} new fee records for {month}/{year}."))
