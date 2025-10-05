from django.db import migrations, models
import django.db.models.deletion


def create_default_zones(apps, schema_editor):
    ClientProfile = apps.get_model('voting', 'ClientProfile')
    Zone = apps.get_model('voting', 'Zone')
    for cp in ClientProfile.objects.all():
        Zone.objects.get_or_create(client=cp, name='Sin asignar')


def assign_existing_voters_default_zone(apps, schema_editor):
    Voter = apps.get_model('voting', 'Voter')
    Zone = apps.get_model('voting', 'Zone')
    for voter in Voter.objects.all():
        if voter.zone_id is None:
            default_zone = Zone.objects.filter(client=voter.client, name='Sin asignar').first()
            if default_zone:
                voter.zone = default_zone
                voter.save(update_fields=['zone'])


class Migration(migrations.Migration):

    dependencies = [
        ('voting', '0004_alter_clientprofile_user_alter_voter_client_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Zone',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='zones', to='voting.clientprofile')),
            ],
            options={
                'ordering': ['name'],
                'unique_together': {('client', 'name')},
            },
        ),
        migrations.AddField(
            model_name='voter',
            name='zone',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='voters', to='voting.zone'),
        ),
        migrations.RunPython(create_default_zones, migrations.RunPython.noop),
        migrations.RunPython(assign_existing_voters_default_zone, migrations.RunPython.noop),
    ]
