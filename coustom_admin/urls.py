from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    # Redirect root admin URL to login
    path('', RedirectView.as_view(url='login/', permanent=True)),

    # Authentication
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='admin_login'), name='admin_logout'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    path('warden_dashboard/', views.warden_dashboard, name='warden_dashboard'),
    path('api/dashboard-stats/', views.dashboard_stats_api, name='dashboard_stats_api'),
    
    # Hostel Management
    path('hostels/', views.hostels, name='hostels'),
    path('hostel_form/', views.hostellist, name='hostellist'),
    path('add_hostel/', views.Addhostel, name='Addhostel'),
    path('update_hostel/<int:id>/', views.updateHostel, name='updateHostel'),
    path('delete_hostel/<int:id>/', views.deleteHostel, name='deleteHostel'),

    # Room Management
    path('room_assignments/', views.room_assignments, name='room_assignments'),
    path('api/assignments/<int:assignment_id>/checkout/', views.checkout_assignment, name='checkout_assignment'),
    path('api/assignments/<int:assignment_id>/', views.get_assignment_details, name='get_assignment_details'),
    path('admin/api/assignments/<int:assignment_id>/', views.get_assignment_details, name='admin_get_assignment_details'),
    path('coustom_admin/api/assignments/<int:assignment_id>/', views.get_assignment_details, name='coustom_admin_get_assignment_details'),
    path('assignments/<int:assignment_id>/', views.get_assignment_details, name='simple_get_assignment_details'),
    path('add_room/', views.add_room, name='add_room'),
    path('update_room/<int:room_id>/', views.update_room, name='update_room'),
    path('delete_room/<int:room_id>/', views.delete_room, name='delete_room'),
    path('get_hostel_flats/<int:hostel_id>/', views.get_hostel_flats, name='get_hostel_flats'),
    path('get_room_rate/<int:hostel_id>/<str:room_type>/', views.get_room_rate, name='get_room_rate'),

    # Rates and Charges
    path('fixed_rates/', views.fixed_rates, name='fixed_rates'),
    path('hostel_charges/', views.hostel_charges, name='hostel_charges'),

    # Student Management
    path('manageStudent/', views.manageStudent, name='manageStudent'),
    path('manage_student/', views.manageStudent, name='manage_student'),
    path('edit_student/<int:user_id>/', views.edit_student, name='edit_student'),
    path('delete_student/<int:user_id>/', views.delete_student, name='delete_student'),
    path('search_students/', views.search_students, name='search_students'),

    # Warden Management
    path('manageWardens/', views.manageWardens, name='manageWardens'),
    path('wardenlist/', views.wardenlist, name='wardenlist'),
    path('add_warden/', views.addWarden, name='addWarden'),
    path('get_available_hostels/<int:warden_id>/', views.getAvailableHostels, name='getAvailableHostels'),
    path('assign_hostel/', views.assignHostel, name='assignHostel'),
    path('deleteWarden/<int:warden_id>/', views.deleteWarden, name='deleteWarden'),
    path('update_warden/<int:warden_id>/', views.updateWarden, name='updateWarden'),
    path('get_warden/<int:warden_id>/', views.getWarden, name='getWarden'),
    path('remove-warden/<int:hostel_id>/', views.removeWardenFromHostel, name='removeWardenFromHostel'),

    # User Management
    path('users/', views.users, name='users'),
    path('delete_user/<int:user_id>/', views.deleteUser, name='deleteUser'),
    path('update_user/<int:user_id>/', views.update_user, name='update_user'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),

    # Booking Management
    path('manage_booking/', views.manage_booking, name='manage_booking'),
    path('create_booking/', views.create_booking, name='create_booking'),
    path('approve_booking/<int:booking_id>/', views.approve_booking, name='approve_booking'),
    path('get_room_types/', views.get_room_types, name='get_room_types'),
    path('get_room_types_by_hostel/', views.get_room_types, name='get_room_types_by_hostel'),
    path('get_available_rooms/<int:booking_id>/', views.get_available_rooms, name='get_available_rooms'),
    path('approve_booking/<int:booking_id>/', views.approve_booking, name='approve_booking'),
    path('reject_booking/<int:booking_id>/', views.reject_booking, name='reject_booking'),
    path('cancel_booking/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('check_availability/', views.check_availability, name='check_availability'),
    path('get_room_types/', views.get_room_types, name='get_room_types'),
    path('get_hostels/', views.get_hostels, name='get_hostels'),
    
    # Payment Management - Removed payment functionality

    # Mess Incharge Management
    path('manageMessIncharge/', views.manage_mess_incharge, name='manage_mess_incharge'),
    path('add_mess_incharge/', views.add_mess_incharge, name='add_mess_incharge'),
    path('edit_mess_incharge/<int:mess_incharge_id>/', views.edit_mess_incharge, name='edit_mess_incharge'),
    path('delete_mess_incharge/<int:mess_incharge_id>/', views.delete_mess_incharge, name='delete_mess_incharge'),
    path('get_mess_incharge/<int:mess_incharge_id>/', views.get_mess_incharge, name='get_mess_incharge'),

    # Other
    path('complaints/', views.complaints, name='complaints'),
    path('expenses/', views.expenses, name='expenses'),
    path('profile/', views.profile, name='profile'),
    path('manageBooking/', views.manage_booking, name='manage_booking_camel'),
    path('mess_menu/', views.mess_menu, name='mess_menu'),
    path('feedbacks/', views.student_feedbacks, name='student_feedbacks'),
    
    # Security Guard Management
    path('manageSecurityGuards/', views.manage_security_guards, name='manage_security_guards'),
    path('add_security_guard/', views.add_security_guard, name='add_security_guard'),
    path('edit_security_guard/<int:guard_id>/', views.edit_security_guard, name='edit_security_guard'),
    path('delete_security_guard/<int:guard_id>/', views.delete_security_guard, name='delete_security_guard'),
    path('get_security_guards_data/', views.get_security_guards_data, name='get_security_guards_data'),
]
