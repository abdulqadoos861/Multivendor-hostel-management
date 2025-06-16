from django.urls import path
from . import views

app_name = 'messincharge'

urlpatterns = [
    # Add URL patterns here
    path('', views.index, name='index'),
    path('login/', views.mess_incharge_login, name='mess_incharge_login'),
    path('logout/', views.mess_incharge_logout, name='mess_incharge_logout'),
]
