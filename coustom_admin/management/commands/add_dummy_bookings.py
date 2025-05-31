from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from coustom_admin.models import Hostels, bookingRequest
import random
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Adds dummy booking requests'

    def handle(self, *args, **kwargs):
        # Get all students and hostels
        students = User.objects.filter(is_staff=False, is_superuser=False)
        hostels = Hostels.objects.all()

        if not students.exists():
            self.stdout.write(
                self.style.ERROR('No students found. Please run add_dummy_students first.')
            )
            return

        if not hostels.exists():
            self.stdout.write(
                self.style.ERROR('No hostels found. Please add some hostels first.')
            )
            return

        # Create 20 booking requests
        for i in range(20):
            # Randomly select a student and hostel
            student = random.choice(students)
            hostel = random.choice(hostels)

            # Generate a random request date within the last 30 days
            request_date = datetime.now() - timedelta(days=random.randint(0, 30))

            # Randomly select room type and status
            room_type = random.choice(['Single', 'Double'])
            status = random.choice(['Pending', 'Approved', 'Rejected'])

            # Create booking request
            booking = bookingRequest.objects.create(
                user_id=student,
                hostel_id=hostel,
                room_type=room_type,
                request_date=request_date,
                status=status
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f'Created booking request for {student.username} at {hostel.name}'
                )
            ) 