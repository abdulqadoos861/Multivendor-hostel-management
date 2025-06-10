from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'warden'

urlpatterns = [
    path('login/', views.WardenLoginView.as_view(), name='login'),
    path('logout/', views.warden_logout, name='logout'),
    path('dashboard/', views.WardenDashboardView.as_view(), name='dashboard'),
    path('students/', views.WardenManageStudentsView.as_view(), name='manage_students'),
    # Password reset URLs
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='warden/password_reset.html'), name='password_reset'),
    # Add more URL patterns here as needed
]