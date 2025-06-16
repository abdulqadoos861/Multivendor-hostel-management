from django.contrib import admin
from .models import Hostels, Wardens, HostelWardens, RoomTypeRate, Rooms, Student, BookingRequest, RoomAssignment, Payment, MessIncharge

# Register your models here.
admin.site.register(Hostels)
admin.site.register(Wardens)
admin.site.register(HostelWardens)
admin.site.register(RoomTypeRate)
admin.site.register(Rooms)
admin.site.register(Student)
admin.site.register(BookingRequest)
admin.site.register(RoomAssignment)
admin.site.register(Payment)
admin.site.register(MessIncharge)
