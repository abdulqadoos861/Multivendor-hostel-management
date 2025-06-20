from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
import random
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Adds dummy student users with Pakistani names'

    def handle(self, *args, **kwargs):
        # List of Pakistani first names
        first_names = [
            'Ahmed', 'Ali', 'Usman', 'Hassan', 'Hamza', 'Muhammad', 'Zain', 'Bilal', 'Omar', 'Ibrahim',
            'Fatima', 'Ayesha', 'Sana', 'Hira', 'Mariam', 'Zainab', 'Amina', 'Sara', 'Layla', 'Noor'
        ]

        # List of Pakistani last names
        last_names = [
            'Khan', 'Ali', 'Ahmed', 'Hussain', 'Malik', 'Raza', 'Shah', 'Butt', 'Chaudhry', 'Sheikh',
            'Hashmi', 'Qureshi', 'Siddiqui', 'Mirza', 'Baig', 'Rizvi', 'Zaidi', 'Jafri', 'Naqvi', 'Kazmi'
        ]

        # List of domains for email
        domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']

        # Create 50 dummy students
        for i in range(50):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            username = f"{first_name.lower()}{last_name.lower()}{random.randint(1, 999)}"
            email = f"{username}@{random.choice(domains)}"
            
            # Create user if username doesn't exist
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password='student123',  # Default password
                    first_name=first_name,
                    last_name=last_name,
                    is_staff=False,
                    is_superuser=False
                )
                # Create associated Student object
                from coustom_admin.models import Student
                student = Student.objects.create(
                    user=user,
                    contact_number=f"03{random.randint(0, 9)}{random.randint(0, 9)}{random.randint(1000000, 9999999)}",
                    cnic=f"{random.randint(1000000000000, 9999999999999)}",
                    gender=random.choice(['Male', 'Female', 'Other']),
                    institute=random.choice(['University of Punjab', 'Lahore University of Management Sciences', 'National University of Sciences and Technology', 'Quaid-i-Azam University']),
                    street=f"Street {random.randint(1, 100)}",
                    area=random.choice(['Gulberg', 'Model Town', 'Johar Town', 'DHA']),
                    city=random.choice(['Lahore', 'Karachi', 'Islamabad', 'Rawalpindi']),
                    district=random.choice(['Lahore', 'Karachi', 'Islamabad', 'Rawalpindi']),
                    guardian_name=f"{random.choice(first_names)} {random.choice(last_names)}",
                    guardian_contact=f"03{random.randint(0, 9)}{random.randint(0, 9)}{random.randint(1000000, 9999999)}",
                    guardian_cnic=f"{random.randint(1000000000000, 9999999999999)}",
                    guardian_relation=random.choice(['Father', 'Mother', 'Brother', 'Sister', 'Uncle', 'Aunt'])
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created student user "{username}" with Student profile')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'User "{username}" already exists')
                )
