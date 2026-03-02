from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_customer_profile(sender, instance, created, **kwargs):
    """
    Automatically create a CustomerProfile when a new User is saved.
    Uses get_or_create to remain idempotent (safe even if called more than once).
    """
    if created:
        from accounts.models import CustomerProfile

        CustomerProfile.objects.get_or_create(user=instance)
