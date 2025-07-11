from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.student_login, name='student_login'),
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    path('profile/', views.student_profile, name='student_profile'),
    path('booking/', views.student_booking, name='student_booking'),
    path('complaint/', views.student_complaint, name='student_complaint'),
    path('feedback/', views.student_feedback, name='student_feedback'),
    path('fee_details/', views.student_fee_details, name='student_fee_details'),
    path('pay_fee/', views.pay_fee, name='pay_fee'),
    path('logout/', views.student_logout, name='student_logout'),
]
