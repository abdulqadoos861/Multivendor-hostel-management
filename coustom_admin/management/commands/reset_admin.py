from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings

class Command(BaseCommand):
    help = 'Reset admin password and check authentication'

    def handle(self, *args, **options):
        User = get_user_model()
        email = 'admin@example.com'
        password = 'admin123'
        
        # Create or update admin user
        admin, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': 'admin',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True
            }
        )
        
        if not created:
            self.stdout.write(self.style.SUCCESS(f'Admin user already exists: {admin}'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Created new admin user: {admin}'))
        
        # Set password
        admin.set_password(password)
        admin.save()
        self.stdout.write(self.style.SUCCESS('Password has been set to: admin123'))
        
        # Verify authentication
        from django.contrib.auth import authenticate
        user = authenticate(email=email, password=password)
        if user is not None:
            self.stdout.write(self.style.SUCCESS('Authentication successful!'))
            self.stdout.write(f'User: {user}')
            self.stdout.write(f'is_authenticated: {user.is_authenticated}')
            self.stdout.write(f'is_superuser: {user.is_superuser}')
            self.stdout.write(f'is_staff: {user.is_staff}')
            self.stdout.write(f'is_active: {user.is_active}')
        else:
            self.stdout.write(self.style.ERROR('Authentication failed!'))
            
        # Check if user can be found by email
        try:
            user_by_email = User.objects.get(email=email)
            self.stdout.write(self.style.SUCCESS(f'Found user by email: {user_by_email}'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'No user found with email: {email}'))
            
        # Check if user can be found by username
        try:
            user_by_username = User.objects.get(username='admin')
            self.stdout.write(self.style.SUCCESS(f'Found user by username: {user_by_username}'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('No user found with username: admin'))
