from django.urls import path
from . import views

app_name = 'messincharge'

urlpatterns = [
    # Add URL patterns here
    path('messincharge', views.messincharge, name='messincharge'),
    path('login/', views.mess_incharge_login, name='mess_incharge_login'),
    path('logout/', views.mess_incharge_logout, name='mess_incharge_logout'),
    path('menu/', views.mess_menu, name='mess_menu'),
    path('add_expenses/', views.add_expenses, name='add_expenses'),
    path('manage_students/', views.manage_students, name='manage_students'),
    path('add_mess_student/', views.add_mess_student, name='add_mess_student'),
    path('settings/', views.settings, name='settings'),
]
