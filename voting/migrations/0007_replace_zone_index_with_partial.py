from django.db import migrations, models
from django.db.models import Q

class Migration(migrations.Migration):

    dependencies = [
        ('voting', '0006_voter_indexes'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='voter',
            name='voter_client_zone_voted_idx',
        ),
        migrations.AddIndex(
            model_name='voter',
            index=models.Index(
                fields=['client', 'zone'],
                name='voter_client_zone_notvoted_idx',
                condition=Q(voted=False),
            ),
        ),
    ]
