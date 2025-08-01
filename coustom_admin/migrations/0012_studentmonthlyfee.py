# Generated by Django 5.2.1 on 2025-06-27 08:28

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('coustom_admin', '0011_securitydeposit_delete_payment'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentMonthlyFee',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('month', models.PositiveIntegerField(choices=[(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8), (9, 9), (10, 10), (11, 11), (12, 12)], help_text='Month of the fee (1-12)')),
                ('year', models.PositiveIntegerField(help_text='Year of the fee')),
                ('monthly_rent', models.DecimalField(decimal_places=2, default=0.0, help_text='Monthly rent amount', max_digits=10)),
                ('mess_expenses', models.DecimalField(decimal_places=2, default=0.0, help_text='Mess expenses for the month', max_digits=10)),
                ('electricity_bill', models.DecimalField(decimal_places=2, default=0.0, help_text='Electricity bill for the month', max_digits=10)),
                ('total_fee', models.DecimalField(decimal_places=2, default=0.0, help_text='Total fee (rent + mess + electricity)', max_digits=12)),
                ('payment_status', models.CharField(choices=[('Pending', 'Pending'), ('Paid', 'Paid'), ('Overdue', 'Overdue')], default='Pending', max_length=20)),
                ('due_date', models.DateField(help_text='Due date for payment')),
                ('payment_date', models.DateField(blank=True, help_text='Date when payment was made', null=True)),
                ('transaction_id', models.CharField(blank=True, help_text='Transaction ID for payment', max_length=100, null=True)),
                ('notes', models.TextField(blank=True, help_text='Additional notes about this fee', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('hostel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='student_fees', to='coustom_admin.hostels')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='monthly_fees', to='coustom_admin.student')),
            ],
            options={
                'verbose_name': 'Student Monthly Fee',
                'verbose_name_plural': 'Student Monthly Fees',
                'ordering': ['-year', '-month'],
                'unique_together': {('student', 'month', 'year')},
            },
        ),
    ]
