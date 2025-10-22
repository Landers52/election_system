from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

class ClientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="clientprofile")
    visitor_user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="visitor_profile", null=True, blank=True
    )
    organization_name = models.CharField(max_length=255, default="radicales")
    # Denormalized totals for performance
    total_voters = models.IntegerField(default=0)
    voted_count = models.IntegerField(default=0)

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
    dni = models.CharField(max_length=20)
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
                condition=Q(voted=False),
            ),
        ]
        constraints = [
            models.UniqueConstraint(fields=["client", "dni"], name="voter_client_dni_uniq"),
        ]

@receiver(post_save, sender=User)
def create_client_profile(sender, instance, created, **kwargs):
    """Create a ClientProfile for each new client user (skip superusers and visitor/asiste users)."""
    if not created:
        return
    if instance.is_superuser:
        return
    # Skip auto-creation for shadow/visitor users
    if instance.username.startswith("visitor_") or instance.username.startswith("asiste"):
        return
    # Idempotent creation
    ClientProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def sync_visitor_account(sender, instance, created, **kwargs):
    """Ensure every client user keeps a mirrored visitor account with matching credentials."""
    if instance.is_superuser or instance.username.startswith("visitor_") or instance.username.startswith("asiste"):
        return

    visitor_username = f"asiste{instance.username}"[:150]
    profile, _ = ClientProfile.objects.get_or_create(user=instance)
    visitor = profile.visitor_user

    if visitor and visitor.username != visitor_username:
        # The visitor username should track the main username.
        visitor.username = visitor_username
        visitor.save(update_fields=["username"])

    if not visitor:
        visitor, _ = User.objects.get_or_create(username=visitor_username)

    fields_to_update = []
    if visitor.password != instance.password:
        visitor.password = instance.password
        fields_to_update.append("password")
    if visitor.first_name != instance.first_name:
        visitor.first_name = instance.first_name
        fields_to_update.append("first_name")
    if visitor.last_name != instance.last_name:
        visitor.last_name = instance.last_name
        fields_to_update.append("last_name")
    if visitor.email != instance.email:
        visitor.email = instance.email
        fields_to_update.append("email")
    if visitor.is_active != instance.is_active:
        visitor.is_active = instance.is_active
        fields_to_update.append("is_active")
    if visitor.is_staff:
        visitor.is_staff = False
        fields_to_update.append("is_staff")
    if visitor.is_superuser:
        visitor.is_superuser = False
        fields_to_update.append("is_superuser")

    if fields_to_update:
        visitor.save(update_fields=fields_to_update)

    if profile.visitor_user_id != visitor.id:
        profile.visitor_user = visitor
        profile.save(update_fields=["visitor_user"])

@receiver(post_delete, sender=ClientProfile)
def delete_visitor_user(sender, instance, **kwargs):
    """ Ensure the visitor user is deleted when the ClientProfile is deleted. """
    if instance.visitor_user:
        instance.visitor_user.delete()

class Zone(models.Model):
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name='zones')
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)
    # Denormalized counts for this zone
    total_voters = models.IntegerField(default=0)
    voted_count = models.IntegerField(default=0)

    class Meta:
        unique_together = ("client", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.client.organization_name})"
