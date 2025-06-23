from django.urls import path
from . import views

app_name = 'security'

urlpatterns = [
    path('login/', views.SecurityLoginView.as_view(), name='login'),
    path('logout/', views.security_logout, name='logout'),
    path('dashboard/', views.SecurityDashboardView.as_view(), name='dashboard'),
    path('student-movement/', views.StudentMovementView.as_view(), name='student_movement'),
    path('visitor/', views.VisitorManagementView.as_view(), name='visitor'),
    path('register-visitor/', views.RegisterVisitorView.as_view(), name='register_visitor'),
    path('emergency-alert/', views.EmergencyAlertView.as_view(), name='emergency_alert'),
]
