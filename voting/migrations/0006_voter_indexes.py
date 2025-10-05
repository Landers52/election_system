from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('voting', '0005_zone_voter_zone'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='voter',
            index=models.Index(fields=['client', 'voted'], name='voter_client_voted_idx'),
        ),
        migrations.AddIndex(
            model_name='voter',
            index=models.Index(fields=['client', 'zone', 'voted'], name='voter_client_zone_voted_idx'),
        ),
    ]
