from django.contrib import admin
from .models import Hostels, Wardens, HostelWardens, RoomTypeRate, Rooms, Student, BookingRequest, RoomAssignment, SecurityDeposit, MessIncharge, StudentMonthlyFee

# Register your models here.
admin.site.register(Hostels)
admin.site.register(Wardens)
admin.site.register(HostelWardens)
admin.site.register(RoomTypeRate)
admin.site.register(Rooms)
admin.site.register(Student)
admin.site.register(BookingRequest)
admin.site.register(RoomAssignment)
admin.site.register(SecurityDeposit)
admin.site.register(MessIncharge)
admin.site.register(StudentMonthlyFee)
