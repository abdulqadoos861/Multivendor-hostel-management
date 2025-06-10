from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Check user details in the database'

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            admin = User.objects.get(username='admin')
            self.stdout.write(self.style.SUCCESS('Admin user found:'))
            self.stdout.write(f'Username: {admin.username}')
            self.stdout.write(f'Email: {admin.email}')
            self.stdout.write(f'is_superuser: {admin.is_superuser}')
            self.stdout.write(f'is_staff: {admin.is_staff}')
            self.stdout.write(f'is_active: {admin.is_active}')
            
            # Check password
            self.stdout.write('\nChecking password...')
            if admin.check_password('admin123'):
                self.stdout.write(self.style.SUCCESS('Password is correct'))
            else:
                self.stdout.write(self.style.ERROR('Password is incorrect'))
                
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('Admin user not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
