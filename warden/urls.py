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
    path('rooms/', views.manage_rooms, name='manage_rooms'),
    path('search_student/', views.search_student, name='search_student'),
    path('complaints/', views.warden_complaints, name='warden_complaints'),
    # Password reset URLs
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='warden/password_reset.html'), name='password_reset'),
    # Add more URL patterns here as needed,
]
