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

        # Create 30 dummy students
        for i in range(30):
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
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created student user "{username}"')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'User "{username}" already exists')
                ) 