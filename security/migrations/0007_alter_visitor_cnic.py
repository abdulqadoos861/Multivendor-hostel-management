# Generated by Django 5.2.1 on 2025-06-22 04:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('security', '0006_visitor_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='visitor',
            name='cnic',
            field=models.CharField(help_text='Enter CNIC without dashes (e.g., 1234567890123)', max_length=15),
        ),
    ]
