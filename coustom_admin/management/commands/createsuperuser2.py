from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Create a superuser with a password non-interactively'

    def handle(self, *args, **options):
        User = get_user_model()
        username = 'admin'
        email = 'admin@example.com'
        password = 'admin123'  # You should change this in production
        
        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(self.style.SUCCESS(f'Successfully created superuser: {username}'))
        else:
            self.stdout.write(self.style.WARNING(f'User {username} already exists'))
