from django.contrib import admin
from .models import MessMenu, Expenses, MessStudent, MessAttendance, MessCharges

# Register your models here.
admin.site.register(MessMenu)
admin.site.register(Expenses)
admin.site.register(MessStudent)
admin.site.register(MessAttendance)
admin.site.register(MessCharges)
