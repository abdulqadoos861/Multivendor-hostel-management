from django.urls import path
from . import views

urlpatterns = [
    path('', views.admin_login, name='admin_login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('hostels/', views.hostels, name='hostels'),
    path('Addhostel/', views.Addhostel, name='Addhostel'),
    path('deleteHostel/<int:id>/', views.deleteHostel, name='deleteHostel'),
    path('updateHostel/<int:id>/', views.updateHostel, name='updateHostel'),
    path('add_room/', views.add_room, name='add_room'),
    path('admin/add_room/', views.add_room, name='admin_add_room'),
    path('get_hostel_flats/<int:hostel_id>/', views.get_hostel_flats, name='get_hostel_flats'),
    path('update_room/<int:room_id>/', views.update_room, name='update_room'),
    path('delete_room/<int:room_id>/', views.delete_room, name='delete_room'),
    path('fixed_rates/', views.fixed_rates, name='fixed_rates'),
    path('get_room_rate/<int:hostel_id>/<str:room_type>/', views.get_room_rate, name='get_room_rate'),
    path('admin/hostel_charges/', views.hostel_charges, name='hostel_charges'),
    path('manageWardens/', views.manageWardens, name='manageWardens'),
    path('addWarden/', views.addWarden, name='addWarden'),
    path('wardens/update/<int:warden_id>/', views.updateWarden, name='updateWarden'),
    path('deleteWarden/<int:warden_id>/', views.deleteWarden, name='deleteWarden'),
    path('getAvailableHostels/<int:warden_id>/', views.getAvailableHostels, name='getAvailableHostels'),
    path('assignHostel/', views.assignHostel, name='assignHostel'),
    path('manageStudent/', views.manageStudent, name='manageStudent'),
    path('students/edit/<int:user_id>/', views.edit_student, name='edit_student'),
    path('students/delete/<int:user_id>/', views.delete_student, name='delete_student'),
    path('users/', views.users, name='users'),
    path('users/update/<int:user_id>/', views.update_user, name='update_user'),
    path('users/delete/<int:user_id>/', views.deleteUser, name='deleteUser'),
    path('complaints/', views.complaints, name='complaints'),
    path('expenses/', views.expenses, name='expenses'),
    path('profile/', views.profile, name='profile'),
    
    # Booking URLs
    path('bookings/', views.manage_booking, name='manage_booking'),
    path('bookings/create/', views.create_booking, name='create_booking'),
    path('bookings/approve/<int:booking_id>/', views.approve_booking, name='approve_booking'),
    path('bookings/reject/<int:booking_id>/', views.reject_booking, name='reject_booking'),
    path('bookings/cancel/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('check-availability/', views.check_availability, name='check_availability'),
    
    # Room type API
    path('get-room-types/', views.get_room_types, name='get_room_types'),
    
    # Legacy URL for backward compatibility
    path('manageBooking/', views.manage_booking, name='manage_booking'),
]