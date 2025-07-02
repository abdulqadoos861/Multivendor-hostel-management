from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'warden'

urlpatterns = [
    path('login/', views.WardenLoginView.as_view(), name='login'),
    path('logout/', views.warden_logout, name='logout'),
    path('dashboard/', views.WardenDashboardView.as_view(), name='dashboard'),
    path('students/', views.WardenManageStudentsView.as_view(), name='manage_students'),
    path('student/<int:student_id>/details/', views.student_details, name='student_details'),
    path('students/add/', views.WardenManageStudentsView.as_view(), name='add_student'),
    path('bookings/get-available-rooms/', views.get_available_rooms, name='get_available_rooms'),
    path('bookings/', views.manage_booking, name='manage_booking'),
    path('bookings/create/', views.create_booking, name='create_booking'),
    path('bookings/approve/', views.approve_booking, name='approve_booking'),
    path('bookings/reject/', views.reject_booking, name='reject_booking'),
    path('bookings/<int:booking_id>/details/', views.booking_details, name='booking_details'),
    path('room-assignments/', views.room_assignments, name='room_assignments'),
    path('room-assignments/checkout/<int:assignment_id>/', views.checkout_student, name='checkout_student'),
    path('room-assignments/<int:assignment_id>/details/', views.room_assignment_details, name='room_assignment_details'),
    path('rooms/', views.manage_rooms, name='manage_rooms'),
    path('search_student/', views.search_student, name='search_student'),
    path('complaints/', views.warden_complaints, name='warden_complaints'),
    path('security-deposits/', views.security_deposits, name='security_deposits'),
    path('security-deposit-details/<int:deposit_id>/', views.security_deposit_details, name='security_deposit_details'),
    path('monthly-fees/', views.monthly_fees, name='monthly_fees'),
    path('monthly-fees/generate/', views.generate_monthly_fees, name='generate_monthly_fees'),
    path('monthly-fees/collect/<int:fee_id>/', views.collect_monthly_fee, name='collect_monthly_fee'),
    path('change-room-requests/', views.change_room_requests, name='change_room_requests'),
    path('change-room-request-details/<int:request_id>/', views.change_room_request_details, name='change_room_request_details'),
    path('get-available-rooms-for-change/', views.get_available_rooms_for_change, name='get_available_rooms_for_change'),
    path('approve-room-change-request/', views.approve_room_change_request, name='approve_room_change_request'),
    path('reject-room-change-request/', views.reject_room_change_request, name='reject_room_change_request'),
    path('expenses/', views.manage_expenses, name='manage_expenses'),
    path('expenses/<int:expense_id>/details/', views.expense_details, name='expense_details'),
    # Password reset URLs
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='warden/password_reset.html'), name='password_reset'),
    # Add more URL patterns here as needed,
]
