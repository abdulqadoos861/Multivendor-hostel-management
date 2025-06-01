from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('', views.admin_login, name='admin_login'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Hostel Management
    path('hostels/', views.hostels, name='hostels'),
    path('Addhostel/', views.Addhostel, name='Addhostel'),
    path('updateHostel/<int:id>/', views.updateHostel, name='updateHostel'),
    path('deleteHostel/<int:id>/', views.deleteHostel, name='deleteHostel'),

    # Room Management
    path('add_room/', views.add_room, name='add_room'),
    path('admin/add_room/', views.add_room, name='admin_add_room'),
    path('get_hostel_flats/<int:hostel_id>/', views.get_hostel_flats, name='get_hostel_flats'),
    path('update_room/<int:room_id>/', views.update_room, name='update_room'),
    path('delete_room/<int:room_id>/', views.delete_room, name='delete_room'),

    # Rate Management
    path('fixed_rates/', views.fixed_rates, name='fixed_rates'),
    path('get_room_rate/<int:hostel_id>/<str:room_type>/', views.get_room_rate, name='get_room_rate'),
    path('admin/hostel_charges/', views.hostel_charges, name='hostel_charges'),

    # Warden Management
    path('manageWardens/', views.manageWardens, name='manageWardens'),
    path('addWarden/', views.addWarden, name='addWarden'),
    path('wardens/update/<int:warden_id>/', views.updateWarden, name='updateWarden'),
    path('deleteWarden/<int:warden_id>/', views.deleteWarden, name='deleteWarden'),
    path('getAvailableHostels/<int:warden_id>/', views.getAvailableHostels, name='getAvailableHostels'),
    path('assignHostel/', views.assignHostel, name='assignHostel'),

    # Booking Management
    path('manageBookings/', views.manageBookings, name='manageBookings'),
    path('approveBooking/<int:booking_id>/', views.approveBooking, name='approveBooking'),
    path('rejectBooking/<int:booking_id>/', views.rejectBooking, name='rejectBooking'),

    # User Management
    path('users/', views.users, name='users'),
    path('users/update/<int:user_id>/', views.updateUser, name='updateUser'),
    path('users/delete/<int:user_id>/', views.deleteUser, name='deleteUser'),

    # Other Pages
    path('complaints/', views.complaints, name='complaints'),
    path('expenses/', views.expenses, name='expenses'),
    path('manageStudent/', views.manageStudent, name='manageStudent'),
    path('profile/', views.profile, name='profile'),
]