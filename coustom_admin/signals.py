from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Wardens

User = get_user_model()

@receiver(post_save, sender=User)
def create_warden_profile(sender, instance, created, **kwargs):
    """
    Create a Warden profile when a new user is created and is_staff is True
    """
    if created and instance.is_staff:
        # Create a Warden profile with default values
        # These can be updated later through the admin or a profile form
        Wardens.objects.create(
            user=instance,
            name=f"{instance.first_name} {instance.last_name}".strip() or instance.username,
            contact_number='',
            gender='',
        )

@receiver(post_save, sender=User)
def save_warden_profile(sender, instance, **kwargs):
    """
    Save the Warden profile when the user is saved
    """
    if hasattr(instance, 'warden_profile'):
        # Update the warden's name if the user's name changes
        instance.warden_profile.name = f"{instance.first_name} {instance.last_name}".strip() or instance.username
        instance.warden_profile.save()
