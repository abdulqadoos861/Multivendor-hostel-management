from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.generic import View, ListView
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView
from django.contrib.auth.models import User, Group
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.http import JsonResponse, HttpResponseForbidden
from django.urls import reverse, reverse_lazy
from django.middleware.csrf import get_token, rotate_token
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from coustom_admin.models import Student, Rooms
from coustom_admin.models import Wardens

class WardenLoginView(View):
    template_name = 'warden/warden_login.html'
    
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, 'warden_profile'):
            return redirect('warden:dashboard')
        return render(request, self.template_name)
    
    def post(self, request, *args, **kwargs):
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')
        next_url = request.POST.get('next', reverse('warden:dashboard'))
        
        try:
            # Get user by email
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                messages.error(request, 'No account found with this email address.')
                return render(request, self.template_name, {'email': email})
            
            # Authenticate user
            user = authenticate(request, username=user.username, password=password)
            if user is None:
                messages.error(request, 'Invalid password.')
                return render(request, self.template_name, {'email': email})
                
            if not user.is_active:
                messages.error(request, 'This account is inactive.')
                return render(request, self.template_name, {'email': email})
            
            # Check if user is a warden
            if not hasattr(user, 'warden_profile'):
                messages.error(request, 'You are not authorized to access the warden panel.')
                return render(request, self.template_name, {'email': email})
            
            # Login successful
            login(request, user)
            
            # Set session expiry
            if remember_me:
                request.session.set_expiry(60 * 60 * 24 * 30)  # 30 days
            
            messages.success(request, 'Successfully logged in!')
            return redirect(next_url)
            
        except Exception as e:
            messages.error(request, 'An error occurred during login. Please try again.')
            return render(request, self.template_name, {'email': email})
        
        # Set CSRF token in response for AJAX
        if is_ajax:
            response.set_cookie('csrftoken', get_token(request), samesite='Lax', secure=request.is_secure())
            return response

class WardenDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'warden/warden_dashboard.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, 'warden_profile'):
            return redirect('warden:login')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Dashboard'
        
        # Add any additional context data here
        try:
            context['warden'] = self.request.user.warden_profile
        except ObjectDoesNotExist:
            pass
            
        return context


class WardenManageStudentsView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Student
    template_name = 'warden/warden_managestudents.html'
    context_object_name = 'students'
    paginate_by = 10
    
    def test_func(self):
        return self.request.user.is_authenticated and hasattr(self.request.user, 'warden_profile')
    
    def handle_no_permission(self):
        return redirect('warden:login')
    
    def get_queryset(self):
        # Get the current warden's assigned hostels
        warden = self.request.user.warden_profile
        assigned_hostels = warden.hostelwardens_set.values_list('hostel_id', flat=True)
        
        if not assigned_hostels.exists():
            return Student.objects.none()  # Return empty queryset if warden has no hostels
            
        # Get all active room assignments in the warden's hostels
        from coustom_admin.models import RoomAssignment
        
        # Get the user IDs of students with active room assignments in the warden's hostels
        student_user_ids = RoomAssignment.objects.filter(
            is_active=True,
            room__hostel_id__in=assigned_hostels
        ).values_list('booking__student_id', flat=True).distinct()
        
        # Start with base queryset of students with active assignments in warden's hostels
        queryset = Student.objects.filter(
            user_id__in=student_user_ids
        ).select_related('user').order_by('user__first_name')
        
        # Filter by search query
        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(user__username__icontains=search_query) |
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(user__email__icontains=search_query) |
                Q(contact_number__icontains=search_query) |
                Q(cnic__icontains=search_query)
            )
        
        # Filter by status
        status = self.request.GET.get('status', '').lower()
        if status == 'active':
            queryset = queryset.filter(user__is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(user__is_active=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Manage Students'
        
        # Get rooms only from the warden's assigned hostels
        warden = self.request.user.warden_profile
        assigned_hostels = warden.hostelwardens_set.values_list('hostel_id', flat=True)
        context['available_rooms'] = Rooms.objects.filter(hostel_id__in=assigned_hostels)
        
        # Add pagination context
        page_obj = context.get('page_obj')
        if page_obj:
            paginator = context.get('paginator')
            context['is_paginated'] = page_obj.has_other_pages()
            context['page_obj'] = page_obj
            context['paginator'] = paginator
            
        return context

def warden_logout(request):
    logout(request)
    return redirect('warden:login')