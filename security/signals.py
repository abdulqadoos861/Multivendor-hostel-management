from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User, Group
from .models import SecurityGuard

@receiver(post_save, sender=User)
def create_security_profile(sender, instance, created, **kwargs):
    if created:
        security_group, _ = Group.objects.get_or_create(name='Security')
        if security_group in instance.groups.all():
            SecurityGuard.objects.create(user=instance)

@receiver(post_save, sender=User)
def update_security_profile(sender, instance, **kwargs):
    security_group, _ = Group.objects.get_or_create(name='Security')
    if security_group in instance.groups.all():
        if not hasattr(instance, 'security_profile'):
            SecurityGuard.objects.create(user=instance)
    else:
        if hasattr(instance, 'security_profile'):
            instance.security_profile.delete()
