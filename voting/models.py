from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

class ClientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="clientprofile")
    visitor_user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="visitor_profile", null=True, blank=True
    )
    organization_name = models.CharField(max_length=255, default="radicales")

    def delete(self, *args, **kwargs):
        """ Ensure the visitor account is deleted when the client profile is deleted. """
        if self.visitor_user:
            self.visitor_user.delete()
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.organization_name

class Voter(models.Model):
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name='voters')
    name = models.CharField(max_length=255)
    dni = models.CharField(max_length=20, unique=True)
    voted = models.BooleanField(default=False)
    # Zone will be added via new Zone model; nullable for backward compatibility then enforced logically
    zone = models.ForeignKey('Zone', on_delete=models.SET_NULL, null=True, blank=True, related_name='voters')

    def __str__(self):
        return f"{self.name} ({'Voted' if self.voted else 'Not Voted'})"

    class Meta:
        indexes = [
            models.Index(fields=["client", "voted"], name="voter_client_voted_idx"),
            # Partial index for pending (not voted) lookups per zone
            models.Index(
                fields=["client", "zone"],
                name="voter_client_zone_notvoted_idx",
                condition=models.Q(voted=False),
            ),
        ]

@receiver(post_save, sender=User)
def create_client_profile(sender, instance, created, **kwargs):
    """ Create a ClientProfile for each new User (excluding superusers and visitor users). """
    if created and not instance.is_superuser and not instance.username.startswith("visitor_"):
        # Create the ClientProfile for the main user
        ClientProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def create_visitor(sender, instance, created, **kwargs):
    if created and not instance.is_superuser:
        # Ensure it's not creating visitors for visitors
        if instance.username.startswith("visitor_"):
            return  # Exit to avoid recursion

        visitor_username = f"visitor_{instance.username}"[:150]  # Trim if needed

        if not User.objects.filter(username=visitor_username).exists():
            visitor = User.objects.create_user(
                username=visitor_username,
                password=instance.password  # Use the same password as the main user
            )
            visitor.save()

            # Link the visitor user to the ClientProfile
            if hasattr(instance, 'clientprofile'):
                client_profile = instance.clientprofile
                client_profile.visitor_user = visitor
                client_profile.save()

@receiver(post_delete, sender=ClientProfile)
def delete_visitor_user(sender, instance, **kwargs):
    """ Ensure the visitor user is deleted when the ClientProfile is deleted. """
    if instance.visitor_user:
        instance.visitor_user.delete()

class Zone(models.Model):
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name='zones')
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("client", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.client.organization_name})"
