from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.generic import View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.http import JsonResponse
from .models import StudentMovement, Visitor
from coustom_admin.models import Student, Hostels

class SecurityLoginView(View):
    template_name = 'security/security_login.html'
    
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, 'security_profile'):
            return redirect('security:dashboard')
        return render(request, self.template_name)
     
    def post(self, request, *args, **kwargs):
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')
        next_url = request.POST.get('next', reverse('security:dashboard'))
        
        try:
            # Get user by email
            try:
                from django.contrib.auth.models import User
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
            
            # Check if user is a security guard
            if not hasattr(user, 'security_profile'):
                messages.error(request, 'You are not authorized to access the security panel.')
                return render(request, self.template_name, {'email': email})
            
            # Login successful
            login(request, user)
            
            # Set session expiry
            if remember_me:
                request.session.set_expiry(60 * 60 * 24 * 30)  # 30 days
            
            messages.success(request, 'Successfully logged in!')
            return redirect(reverse('security:dashboard'))
            
        except Exception as e:
            messages.error(request, 'An error occurred during login. Please try again.')
            return render(request, self.template_name, {'email': email})

class SecurityDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'security/security_dashboard.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, 'security_profile'):
            return redirect('security:login')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        from datetime import datetime, date
        from .models import EmergencyAlert, Visitor
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Dashboard'
        
        try:
            security_guard = self.request.user.security_profile
            context['security_guard'] = security_guard
            
            # Get recent student movements
            if security_guard.hostel:
                recent_movements = StudentMovement.objects.filter(hostel=security_guard.hostel).select_related('student__user').order_by('-timestamp')[:5]
                today_movements = StudentMovement.objects.filter(hostel=security_guard.hostel, timestamp__date=date.today()).count()
                visitors_today = Visitor.objects.filter(hostel=security_guard.hostel, timestamp__date=date.today()).count()
                active_alerts = EmergencyAlert.objects.filter(hostel=security_guard.hostel, status='active').count()
            else:
                recent_movements = StudentMovement.objects.all().select_related('student__user').order_by('-timestamp')[:5]
                today_movements = StudentMovement.objects.filter(timestamp__date=date.today()).count()
                visitors_today = Visitor.objects.filter(timestamp__date=date.today()).count()
                active_alerts = EmergencyAlert.objects.filter(status='active').count()
                
            context['recent_movements'] = recent_movements
            context['today_movements'] = today_movements
            context['visitors_today'] = visitors_today
            context['active_alerts'] = active_alerts
            
            # Placeholder for announcements (removed static content)
            context['announcements'] = []
        except ObjectDoesNotExist:
            context['error_message'] = 'Security profile not found. Please contact an administrator.'
            
        return context

class StudentMovementView(LoginRequiredMixin, TemplateView):
    template_name = 'security/security_student_movement.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, 'security_profile'):
            return redirect('security:login')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        from coustom_admin.models import Student, Hostels, RoomAssignment
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Student Movement Record'
        
        try:
            security_guard = self.request.user.security_profile
            context['security_guard'] = security_guard
            if security_guard.hostel:
                context['hostel'] = security_guard.hostel
                # Filter students who have active room assignments in the security guard's hostel
                assigned_student_ids = RoomAssignment.objects.filter(room__hostel=security_guard.hostel, is_active=True).values_list('booking__student', flat=True)
                context['students'] = Student.objects.filter(id__in=assigned_student_ids).order_by('user__first_name', 'user__last_name')
                context['movements'] = StudentMovement.objects.filter(hostel=security_guard.hostel).select_related('student__user', 'security_guard__user').order_by('-timestamp')[:50]
            else:
                context['students'] = Student.objects.all().order_by('user__first_name', 'user__last_name')
                context['movements'] = StudentMovement.objects.all().select_related('student__user', 'security_guard__user').order_by('-timestamp')[:50]
                context['hostels'] = Hostels.objects.all().order_by('name')
        except ObjectDoesNotExist:
            context['error_message'] = 'Security profile not found. Please contact an administrator.'
            context['students'] = []
            context['movements'] = []
            
        return context
    
    def post(self, request, *args, **kwargs):
        from coustom_admin.models import Student, Hostels
        try:
            security_guard = request.user.security_profile
            student_id = request.POST.get('student_id')
            movement_type = request.POST.get('movement_type')
            notes = request.POST.get('notes', '')
            hostel_id = request.POST.get('hostel_id', None)
            
            if not student_id or not movement_type:
                return JsonResponse({'status': 'error', 'message': 'Student and movement type are required.'}, status=400)
                
            if movement_type not in ['IN', 'OUT']:
                return JsonResponse({'status': 'error', 'message': 'Invalid movement type.'}, status=400)
                
            student = Student.objects.get(id=student_id)
            hostel = None
            if hostel_id:
                hostel = Hostels.objects.get(id=hostel_id)
            elif security_guard.hostel:
                hostel = security_guard.hostel
                
            movement = StudentMovement(
                student=student,
                security_guard=security_guard,
                movement_type=movement_type,
                notes=notes,
                hostel=hostel
            )
            movement.save()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Student {movement_type} recorded successfully.',
                'movement': {
                    'id': movement.id,
                    'student_name': f"{student.user.first_name} {student.user.last_name}",
                    'movement_type': movement_type,
                    'timestamp': movement.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'notes': notes
                }
            })
        except Student.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Student not found.'}, status=404)
        except Hostels.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Hostel not found.'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error recording movement: {str(e)}'}, status=500)

@login_required
@user_passes_test(lambda u: hasattr(u, 'security_profile'))
def security_logout(request):
    logout(request)
    return redirect('security:login')

class VisitorManagementView(LoginRequiredMixin, TemplateView):
    template_name = 'security/security_visitor.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, 'security_profile'):
            return redirect('security:login')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        from coustom_admin.models import Student, Hostels, RoomAssignment
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Visitor Management'
        
        try:
            security_guard = self.request.user.security_profile
            context['security_guard'] = security_guard
            if security_guard.hostel:
                context['hostel'] = security_guard.hostel
                # Filter students who have active room assignments in the security guard's hostel
                assigned_student_ids = RoomAssignment.objects.filter(room__hostel=security_guard.hostel, is_active=True).values_list('booking__student', flat=True)
                context['students'] = Student.objects.filter(id__in=assigned_student_ids).order_by('user__first_name', 'user__last_name')
                context['visitors'] = Visitor.objects.filter(hostel=security_guard.hostel).select_related('student__user', 'security_guard__user').order_by('-timestamp')[:50]
            else:
                context['students'] = Student.objects.all().order_by('user__first_name', 'user__last_name')
                context['visitors'] = Visitor.objects.all().select_related('student__user', 'security_guard__user').order_by('-timestamp')[:50]
                context['hostels'] = Hostels.objects.all().order_by('name')
        except ObjectDoesNotExist:
            context['error_message'] = 'Security profile not found. Please contact an administrator.'
            context['students'] = []
            context['visitors'] = []
            
        return context

class RegisterVisitorView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, 'security_profile'):
            return redirect('security:login')
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request, *args, **kwargs):
        try:
            security_guard = request.user.security_profile
            visitor_name = request.POST.get('visitor_name')
            visitor_contact = request.POST.get('visitor_contact')
            cnic = request.POST.get('cnic')
            relationship = request.POST.get('relationship', '')
            purpose = request.POST.get('purpose')
            to_visted = request.POST.get('to_visted', 'student')
            status = request.POST.get('status', 'pending')
            student_id = request.POST.get('student_id', None)
            staff_name = request.POST.get('staff_name', '')
            notes = request.POST.get('notes', '')
            hostel_id = request.POST.get('hostel_id', None)
            
            if not visitor_name or not visitor_contact or not cnic or not purpose:
                return JsonResponse({'status': 'error', 'message': 'Visitor name, contact number, CNIC, and purpose are required.'}, status=400)
            if to_visted not in ['warden', 'security_guard', 'student', 'other']:
                return JsonResponse({'status': 'error', 'message': 'Invalid visiting type.'}, status=400)
            if to_visted in ['warden', 'security_guard'] and not staff_name:
                return JsonResponse({'status': 'error', 'message': 'Staff name is required when visiting a staff member.'}, status=400)
            if status not in ['accepted', 'rejected', 'pending']:
                return JsonResponse({'status': 'error', 'message': 'Invalid status type.'}, status=400)
                
            student = None
            if student_id:
                try:
                    student = Student.objects.get(id=student_id)
                except Student.DoesNotExist as e:
                    return JsonResponse({'status': 'error', 'message': f'Student not found: {str(e)}'}, status=404)
                
            hostel = None
            if hostel_id:
                try:
                    hostel = Hostels.objects.get(id=hostel_id)
                except Hostels.DoesNotExist as e:
                    return JsonResponse({'status': 'error', 'message': f'Hostel not found: {str(e)}'}, status=404)
            elif security_guard.hostel:
                hostel = security_guard.hostel
                
            visitor = Visitor(
                name=visitor_name,
                contact_number=visitor_contact,
                cnic=cnic,
                relationship=relationship,
                purpose=purpose,
                to_visted=to_visted,
                status=status,
                student=student if to_visted == 'student' else None,
                security_guard=security_guard,
                hostel=hostel,
                notes=notes + (f"\nVisiting Staff: {staff_name}" if to_visted in ['warden', 'security_guard'] and staff_name else "")
            )
            try:
                visitor.save()
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': f'Error saving visitor: {str(e)}'}, status=500)
            
            return JsonResponse({
                'status': 'success',
                'message': 'Visitor registered successfully.',
                'visitor': {
                    'name': visitor.name,
                    'cnic': visitor.cnic,
                    'contact': visitor.contact_number,
                    'relationship': visitor.relationship if visitor.relationship else '-',
                    'purpose': visitor.purpose,
                    'student': f"{student.user.first_name} {student.user.last_name}" if student and to_visted == 'student' else '-',
                    'to_visted': to_visted.title(),
                    'status': visitor.status.title(),
                    'timestamp': visitor.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'security_guard': visitor.security_guard.name if visitor.security_guard else '-',
                    'notes': visitor.notes if visitor.notes else '-'
                }
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Unexpected error registering visitor: {str(e)}'}, status=500)

class EmergencyAlertView(LoginRequiredMixin, TemplateView):
    template_name = 'security/security_emergency_alert.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, 'security_profile'):
            return redirect('security:login')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        from .models import EmergencyAlert
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Emergency Alert'
        
        try:
            security_guard = self.request.user.security_profile
            context['security_guard'] = security_guard
            if security_guard.hostel:
                context['hostel'] = security_guard.hostel
                context['alerts'] = EmergencyAlert.objects.filter(hostel=security_guard.hostel).order_by('-timestamp')[:50]
            else:
                context['alerts'] = EmergencyAlert.objects.all().order_by('-timestamp')[:50]
                context['hostels'] = Hostels.objects.all().order_by('name')
        except ObjectDoesNotExist:
            context['error_message'] = 'Security profile not found. Please contact an administrator.'
            context['alerts'] = []
            
        return context
    
    def post(self, request, *args, **kwargs):
        from .models import EmergencyAlert
        try:
            security_guard = request.user.security_profile
            alert_type = request.POST.get('alert_type')
            location = request.POST.get('location')
            description = request.POST.get('description')
            notify_all = request.POST.get('notify_all') == 'on'
            
            if not alert_type or not location or not description:
                return JsonResponse({'status': 'error', 'message': 'Alert type, location, and description are required.'}, status=400)
                
            if alert_type not in ['fire', 'medical', 'security_breach', 'natural_disaster', 'other']:
                return JsonResponse({'status': 'error', 'message': 'Invalid alert type.'}, status=400)
                
            hostel = security_guard.hostel if security_guard.hostel else None
            
            alert = EmergencyAlert(
                security_guard=security_guard,
                hostel=hostel,
                alert_type=alert_type,
                location=location,
                description=description,
                notify_all=notify_all
            )
            alert.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Emergency alert sent successfully.',
                'alert': {
                    'alert_type': alert.get_alert_type_display(),
                    'location': alert.location,
                    'description': alert.description,
                    'timestamp': alert.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                    'reported_by': security_guard.name if hasattr(security_guard, 'name') else 'Security Guard',
                    'status': alert.get_status_display()
                }
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error sending emergency alert: {str(e)}'}, status=500)
