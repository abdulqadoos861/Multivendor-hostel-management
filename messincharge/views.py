from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth import logout
from coustom_admin.models import MessIncharge

def index(request):
    return render(request, 'messincharge/minc_dashboard.html')

def mess_incharge_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            try:
                mess_incharge = MessIncharge.objects.get(user=user)
                login(request, user)
                messages.success(request, 'Login successful.')
                return redirect('messincharge:index')  # Redirect to mess in-charge dashboard or index
            except MessIncharge.DoesNotExist:
                messages.error(request, 'You are not registered as a Mess Incharge.')
    return render(request, 'messincharge/mess_incharge_login.html')

def mess_incharge_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('messincharge:mess_incharge_login')
