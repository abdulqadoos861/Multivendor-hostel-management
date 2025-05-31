from django.urls import path
from . import views

urlpatterns = [
    path("", views.admin_login, name="admin_login"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("hostels/", views.hostels, name="hostels"),
    path("complaints/", views.complaints, name="complaints"),
    path("expenses/", views.expenses, name="expenses"),
    path("manageStudent/", views.manageStudent, name="manageStudent"),
    path("manageWardens/", views.manageWardens, name="manageWardens"),
    path("manageBookings/", views.manageBookings, name="manageBookings"),
    path("users/", views.users, name="users"),
    path("profile/", views.profile, name="profile"),
    path("Addhostel/", views.Addhostel, name="Addhostel"),
    path("updateHostel/<int:id>/", views.updateHostel, name="updateHostel"),
    path("deleteHostel/<int:id>/", views.deleteHostel, name="deleteHostel"),
    path("addWarden/", views.addWarden, name="addWarden"),
    path("getAvailableHostels/<int:warden_id>/", views.getAvailableHostels, name="getAvailableHostels"),
    path("assignHostel/", views.assignHostel, name="assignHostel"),
    path("deleteWarden/<int:warden_id>/", views.deleteWarden, name="deleteWarden"),
    path('approveBooking/<int:booking_id>/', views.approveBooking, name='approveBooking'),
    path('rejectBooking/<int:booking_id>/', views.rejectBooking, name='rejectBooking'),
    path('wardens/update/<int:warden_id>/', views.updateWarden, name='updateWarden'),
    path('users/update/<int:user_id>/', views.updateUser, name='updateUser'),
]
