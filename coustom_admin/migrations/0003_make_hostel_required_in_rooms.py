from django.db import migrations, models
import django.db.models.deletion


def make_hostel_required(apps, schema_editor):
    # Get the Rooms model
    Rooms = apps.get_model('coustom_admin', 'Rooms')
    # Get the first hostel to set as default (you may need to adjust this logic)
    Hostels = apps.get_model('coustom_admin', 'Hostels')
    first_hostel = Hostels.objects.first()
    
    if first_hostel:
        # Update all rooms with null hostel to the first hostel
        Rooms.objects.filter(hostel__isnull=True).update(hostel=first_hostel)


class Migration(migrations.Migration):
    dependencies = [
        ('coustom_admin', '0002_add_room_assignment'),
    ]

    operations = [
        # First, make the field nullable=False in the database
        migrations.RunPython(make_hostel_required, reverse_code=migrations.RunPython.noop),
        
        # Then, alter the field to be required
        migrations.AlterField(
            model_name='rooms',
            name='hostel',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='rooms',
                to='coustom_admin.hostels',
                null=False,
                blank=False
            ),
        ),
    ]
