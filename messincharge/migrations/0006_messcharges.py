# Generated by Django 5.2.1 on 2025-06-27 08:28

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coustom_admin', '0012_studentmonthlyfee'),
        ('messincharge', '0005_messattendance'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MessCharges',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('breakfast_rate', models.DecimalField(decimal_places=2, default=0.0, help_text='Daily charge for breakfast', max_digits=6)),
                ('lunch_rate', models.DecimalField(decimal_places=2, default=0.0, help_text='Daily charge for lunch', max_digits=6)),
                ('dinner_rate', models.DecimalField(decimal_places=2, default=0.0, help_text='Daily charge for dinner', max_digits=6)),
                ('effective_from', models.DateField(help_text='Date from which these rates are effective')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_mess_charges', to=settings.AUTH_USER_MODEL)),
                ('hostel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mess_charges', to='coustom_admin.hostels')),
            ],
            options={
                'verbose_name': 'Mess Charge',
                'verbose_name_plural': 'Mess Charges',
                'ordering': ['-effective_from'],
            },
        ),
    ]
