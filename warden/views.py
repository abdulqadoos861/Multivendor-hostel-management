from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.generic import View, ListView, TemplateView
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User, Group
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.http import JsonResponse, HttpResponseForbidden
from django.urls import reverse, reverse_lazy
from django.middleware.csrf import get_token, rotate_token
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods
from django.db.models import Count, Prefetch, F, Q
from django.utils import timezone
from datetime import datetime, timedelta, date
from django.db import transaction
from django.utils.safestring import mark_safe
import logging
import json

from coustom_admin.models import Student, Rooms, Wardens, BookingRequest, HostelWardens, RoomAssignment, Hostels, RoomTypeRate
from .forms import StudentRegistrationForm
from coustom_admin.forms import BookingRequestForm


logger = logging.getLogger(__name__)

# Create your views here.

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
        # if is_ajax:
        #     response.set_cookie('csrftoken', get_token(request), samesite='Lax', secure=request.is_secure())
        #     return response

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
    template_name = 'warden/managestudents.html'
    context_object_name = 'students'
    
    def test_func(self):
        return hasattr(self.request.user, 'warden_profile')
    
    def get_queryset(self):
        queryset = Student.objects.all()
        
        # Handle search
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(user__username__icontains=search_query) |
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(user__email__icontains=search_query) |
                Q(contact_number__icontains=search_query) |
                Q(cnic__icontains=search_query)
            )
        
        # Handle status filter
        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(user__is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(user__is_active=False)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Manage Students'
        if 'form' not in context:
            context['form'] = StudentRegistrationForm()
        return context

    def post(self, request, *args, **kwargs):
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            try:
                # Create User
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name']
                )

                # Create Student Profile
                student = Student.objects.create(
                    user=user,
                    contact_number=form.cleaned_data['contact_number'],
                    cnic=form.cleaned_data['cnic'],
                    address=form.cleaned_data['address'],
                    gender=form.cleaned_data['gender'],
                    institute=form.cleaned_data['institute']
                )

                messages.success(request, 'Student registered successfully!')
                return redirect('warden:manage_students')

            except Exception as e:
                messages.error(request, f'Error registering student: {str(e)}')
                if 'user' in locals():
                    user.delete()
        else:
            messages.error(request, 'Please correct the errors below.')

        return self.get(request, *args, **kwargs)

@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
def student_details(request, student_id):
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return HttpResponseForbidden()
        
    try:
        student = Student.objects.select_related('user').get(id=student_id)
        data = {
            'username': student.user.username,
            'first_name': student.user.first_name,
            'last_name': student.user.last_name,
            'email': student.user.email,
            'contact_number': student.contact_number,
            'institute': student.institute,
            'cnic': student.cnic,
            'address': student.address,
            'gender': student.gender,
            'is_active': student.user.is_active
        }
        return JsonResponse(data)
    except Student.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)

@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
def get_available_rooms(request):
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return HttpResponseForbidden()

    booking_id = request.GET.get('booking_id')
    if not booking_id:
        logger.warning("Booking ID not provided in get_available_rooms request")
        return JsonResponse({'error': 'Booking ID is required'}, status=400)

    try:
        booking = BookingRequest.objects.get(id=booking_id)
        logger.debug(f"Found booking {booking_id} for hostel {booking.hostel.id if booking.hostel else 'None'} and room type {booking.room_type}")
    except BookingRequest.DoesNotExist:
        logger.error(f"Booking not found with ID {booking_id}")
        return JsonResponse({'error': 'Booking not found'}, status=404)
    except Exception as e:
        logger.exception(f"Unexpected error fetching booking with ID {booking_id}: {str(e)}")
        return JsonResponse({'error': f'Unexpected error fetching booking: {str(e)}'}, status=500)

    try:
        if not booking.hostel:
            logger.error(f"Booking {booking_id} has no associated hostel")
            return JsonResponse({'error': 'Booking has no associated hostel'}, status=400)

        if not booking.room_type:
            logger.error(f"Booking {booking_id} has no associated room type")
            return JsonResponse({'error': 'Booking has no associated room type'}, status=400)

        # Filter rooms by hostel and room type from the booking request, and ensure there is at least one vacant position
        available_rooms = Rooms.objects.filter(
            hostel=booking.hostel,
            room_type=booking.room_type,
            current_occupants__lt=F('capacity')
        ).values('id', 'room_number', 'room_type', 'current_occupants', 'capacity')

        logger.debug(f"Found {len(available_rooms)} available rooms for booking {booking_id}")

        # Data structure for JSON response including capacity and occupants
        rooms_data = []
        for room in available_rooms:
            rooms_data.append({
                'id': room['id'],
                'room_number': room['room_number'],
                'room_type_name': room['room_type'],
                'current_occupants': room['current_occupants'],
                'capacity': room['capacity']
            })

        return JsonResponse({'available_rooms': rooms_data})
    except Exception as e:
        logger.exception(f"Error fetching available rooms for booking ID {booking_id}: {str(e)}")
        return JsonResponse({'error': f'Error fetching available rooms: {str(e)}'}, status=500)


@login_required
def manage_booking(request):
    # Helper function to check if the user is a student
    def is_student(user):
        return hasattr(user, 'student')

    if is_student(request.user):
        # For students, show only their bookings
        bookings = BookingRequest.objects.filter(student=request.user.student.user).select_related('student')
    else:
        # For admins/wardens, show bookings for their assigned hostel
        bookings = BookingRequest.objects.all().select_related('student')
        if hasattr(request.user, 'warden_profile'):
            warden_profile = request.user.warden_profile
            assigned_hostel = HostelWardens.objects.filter(warden=warden_profile).first()
            if assigned_hostel:
                bookings = bookings.filter(hostel=assigned_hostel.hostel)
    
    # Apply filters from GET parameters
    status_filter = request.GET.get('status')
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    
    search_query = request.GET.get('search')
    if search_query:
        bookings = bookings.filter(
            Q(student__first_name__icontains=search_query) |
            Q(student__last_name__icontains=search_query) |
            Q(student__email__icontains=search_query)
        )
    
    # Add status counts for summary
    status_counts = bookings.values('status').annotate(count=Count('status'))
    
    # Get all hostels with their room types and rates
    hostels_data_queryset = Hostels.objects.prefetch_related(
        Prefetch('roomtyperate_set', 
                queryset=RoomTypeRate.objects.all().only('room_type', 'per_head_rent'),
                to_attr='room_types')
    ).all()
    
    # Prepare hostels data with room types for JavaScript
    hostels_data = []
    for hostel in hostels_data_queryset:
        hostel_data = {
            'id': hostel.id,
            'name': hostel.name,
            'room_types': [
                {
                    'room_type': rt.room_type,
                    'per_head_rent': float(rt.per_head_rent) if rt.per_head_rent else 0.0
                } for rt in hostel.room_types
            ]
        }
        hostels_data.append(hostel_data)
    
    # Convert hostels_data to JSON for JavaScript
    hostels_json = mark_safe(json.dumps(hostels_data, ensure_ascii=False))
    
    # Prepare context
    context = {
        'bookings': bookings.order_by('-request_date'),
        'status_counts': {item['status']: item['count'] for item in status_counts},
        'total_bookings': bookings.count(),
        'hostels': hostels_data_queryset,  # Pass the QuerySet for template iteration
        'hostels_json': hostels_json,  # Pass the JSON string for JavaScript
        'today': date.today(),    # For setting min date on date picker
        'status_filter': status_filter,
        'search_query': search_query,
    }
    return render(request, 'warden/warden_managebookings.html', context)

@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
def approve_booking(request):
    if request.method == 'POST':
        # Log request headers for debugging
        logger.debug(f"Request headers: {dict(request.headers)}")
        logger.debug(f"Request POST data: {request.POST}")

        booking_id = request.POST.get('booking_id')
        room_id = request.POST.get('room_assignment') or request.POST.get('room_id')
        check_in_date_str = request.POST.get('check_in_date')
        check_out_date_str = request.POST.get('check_out_date')
        admin_notes = request.POST.get('admin_notes', '')

        if not all([booking_id, room_id]):
            error_msg = 'Missing required fields for approval.'
            messages.error(request, error_msg)
            logger.warning(f"Missing required fields in approve_booking: booking_id={booking_id}, room_id={room_id}")
            return JsonResponse({'status': 'error', 'message': error_msg}, status=400)

        try:
            booking = BookingRequest.objects.get(id=booking_id)
            room = Rooms.objects.get(id=room_id)
            check_in_date = datetime.strptime(check_in_date_str, '%Y-%m-%d').date() if check_in_date_str else booking.check_in_date
            check_out_date = datetime.strptime(check_out_date_str, '%Y-%m-%d').date() if check_out_date_str else booking.check_out_date

            with transaction.atomic():
                # Check if the room has capacity
                if room.current_occupants >= room.capacity:
                    error_msg = 'Selected room is already full.'
                    messages.error(request, error_msg)
                    logger.warning(f"Room {room_id} is full: current_occupants={room.current_occupants}, capacity={room.capacity}")
                    return JsonResponse({'status': 'error', 'message': error_msg}, status=400)

                # Check if student already has an active booking or room assignment
                if RoomAssignment.objects.filter(booking__student=booking.student, is_active=True).exists():
                    error_msg = 'Student already has an active room assignment.'
                    messages.error(request, error_msg)
                    logger.warning(f"Student {booking.student.id} already has an active room assignment")
                    return JsonResponse({'status': 'error', 'message': error_msg}, status=400)

                if BookingRequest.objects.filter(student=booking.student, status__in=['Approved', 'Pending']).exclude(id=booking_id).exists():
                    error_msg = 'Student already has another pending or approved booking.'
                    messages.error(request, error_msg)
                    logger.warning(f"Student {booking.student.id} already has another pending or approved booking")
                    return JsonResponse({'status': 'error', 'message': error_msg}, status=400)

                # Update booking status and assign room
                booking.status = 'Approved'
                booking.assigned_room = room
                booking.admin_notes = admin_notes
                booking.save()

                # Create RoomAssignment
                RoomAssignment.objects.create(
                    booking=booking,
                    room=room,
                    check_in_date=check_in_date,
                    check_out_date=check_out_date,
                    assigned_by=request.user,
                    is_active=True
                )

                # Increment current occupants for the room
                room.current_occupants = F('current_occupants') + 1
                room.save()

            success_msg = 'Booking approved and room assigned successfully!'
            messages.success(request, success_msg)
            logger.info(f"Booking {booking_id} approved successfully for student {booking.student.id}")
            return JsonResponse({'status': 'success', 'message': success_msg})

        except BookingRequest.DoesNotExist:
            error_msg = 'Booking not found.'
            messages.error(request, error_msg)
            logger.error(f"Booking not found for ID {booking_id}")
            return JsonResponse({'status': 'error', 'message': error_msg}, status=404)
        except Rooms.DoesNotExist:
            error_msg = 'Room not found.'
            messages.error(request, error_msg)
            logger.error(f"Room not found for ID {room_id}")
            return JsonResponse({'status': 'error', 'message': error_msg}, status=404)
        except ValueError as ve:
            error_msg = f'Invalid date format: {str(ve)}'
            messages.error(request, error_msg)
            logger.error(f"Date format error in approve_booking for booking ID {booking_id}: {str(ve)}")
            return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
        except Exception as e:
            error_msg = f'Error approving booking: {str(e)}'
            messages.error(request, error_msg)
            logger.exception(f"Unexpected error in approve_booking for booking ID {booking_id}: {str(e)}")
            return JsonResponse({'status': 'error', 'message': error_msg}, status=500)

    error_msg = 'Invalid request method.'
    logger.warning(f"Invalid request method for approve_booking: {request.method}")
    return JsonResponse({'status': 'error', 'message': error_msg}, status=405)

@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
def reject_booking(request):
    if request.method == 'POST':
        booking_id = request.POST.get('booking_id')
        rejection_reason = request.POST.get('rejection_reason')

        if not all([booking_id, rejection_reason]):
            return JsonResponse({'success': False, 'error': 'Missing required fields for rejection.'})

        try:
            booking = BookingRequest.objects.get(id=booking_id)
            booking.status = 'Rejected'
            booking.admin_notes = rejection_reason  # Store rejection reason in admin_notes field
            booking.save()
            return JsonResponse({'success': True, 'message': 'Request rejected successfully!'})
        except BookingRequest.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Booking not found.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Error rejecting booking: {e}'})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})

@login_required
def create_booking(request):
    logger.info(f"Processing booking request. Method: {request.method}")
    
    try:
        is_staff = request.user.is_staff or hasattr(request.user, 'warden')
        
        if request.method != 'POST':
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid request method'
            }, status=405)
        
        logger.debug(f"POST data: {request.POST}")
        
        # Create a mutable copy of the POST data
        form_data = request.POST.copy()
        
        # For staff users, get the student from the form data
        student = None
        if is_staff:
            student_id = form_data.get('student_id')
            logger.debug(f"Processing student_id: {student_id}, type: {type(student_id) if student_id else 'None'}")
            
            if not student_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Student selection is required'
                }, status=400)
                
            try:
                # Convert student_id to int in case it's a string
                student_id = int(student_id)
                # Look up student by user_id since we're receiving the user ID from the frontend
                student = Student.objects.select_related('user').get(user_id=student_id)
                logger.debug(f"Found student: {student.id} - {student.user.get_full_name()}")
                
                # Check if student already has an approved booking
                existing_approved_booking = BookingRequest.objects.filter(
                    student=student.user,
                    status__in=['Approved', 'Pending']
                ).exists()
                
                if existing_approved_booking:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'This student already has an approved booking.'
                    }, status=400)
                
                # Double-check if student already has an active room assignment
                active_assignment = RoomAssignment.objects.filter(
                    booking__student=student.user,
                    is_active=True
                ).select_related('room').first()
                
                if active_assignment:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Student already has an active room assignment in room {active_assignment.room.room_number}.'
                    }, status=400)
                
                # Set the student's user ID in the form data
                form_data['student'] = str(student.user.id)
                
            except (ValueError, TypeError) as e:
                logger.error(f"Invalid student ID format: {e}")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid student ID format'
                }, status=400)
            except Student.DoesNotExist:
                logger.error(f"Student not found with ID: {student_id}")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Selected student not found'
                }, status=400)
        # For students, use their own student profile
        elif hasattr(request.user, 'student'):
            student = request.user.student
            form_data['student'] = str(student.user.id)
            
            # Check if student already has an approved booking
            existing_approved_booking = BookingRequest.objects.filter(
                student=student.user,
                status__in=['Approved', 'Pending']
            ).exists()
            
            if existing_approved_booking:
                return JsonResponse({
                    'status': 'error',
                    'message': 'You already have an approved booking.'
                }, status=400)
            
            # Check for existing active room assignments for this student
            active_assignment = RoomAssignment.objects.filter(
                booking__student=student.user,
                is_active=True
            ).select_related('room').first()
            
            if active_assignment:
                return JsonResponse({
                    'status': 'error',
                    'message': f'You already have an active room assignment in room {active_assignment.room.room_number}.'
                }, status=400)
        
        # Set default hostel for wardens
        if is_staff and hasattr(request.user, 'warden_profile'):
            warden_profile = request.user.warden_profile
            assigned_hostel = HostelWardens.objects.filter(warden=warden_profile).first()
            if assigned_hostel:
                form_data['hostel'] = str(assigned_hostel.hostel.id)
                logger.debug(f"Set default hostel to {assigned_hostel.hostel.name} for warden {request.user.username}")
            else:
                logger.warning(f"No hostel assigned to warden {request.user.username}")
                return JsonResponse({
                    'status': 'error',
                    'message': 'No hostel assigned to your warden profile. Please contact an administrator.'
                }, status=400)
        
        logger.debug(f"Form data with student and hostel: {form_data}")
        
        # Initialize the form with the updated data
        form = BookingRequestForm(data=form_data, user=request.user)
        
        if not form.is_valid():
            logger.warning(f"Form validation failed. Errors: {form.errors}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {}
                for field, field_errors in form.errors.items():
                    field_label = form.fields[field].label if field in form.fields and hasattr(form.fields[field], 'label') else field
                    errors[field] = [str(e) for e in field_errors]
                
                return JsonResponse({
                    'status': 'error',
                    'message': 'Please correct the errors below.',
                    'errors': errors
                }, status=400)
            
            # Handle non-AJAX form submission
            for field, field_errors in form.errors.items():
                for error in field_errors:
                    messages.error(request, f"{field}: {error}")
            return redirect('warden:manage_booking')
        
        # If we get here, form is valid
        try:
            with transaction.atomic():
                booking = form.save(commit=False)
                
                # Set the student
                if is_staff and student:
                    booking.student = student.user
                elif hasattr(request.user, 'student'):
                    booking.student = request.user.student.user
                else:
                    error_msg = 'Student profile not found. Please complete your student profile before making a booking.'
                    logger.error(error_msg)
                    raise ValueError(error_msg)
                
                # Triple-check for existing active bookings for this student (in case of race condition)
                active_assignment = RoomAssignment.objects.filter(
                    booking__student=booking.student,
                    is_active=True
                ).exists()
                
                if active_assignment:
                    error_msg = 'This student already has an active room assignment.'
                    logger.warning(error_msg)
                    raise ValueError(error_msg)
                
                # Set default check_out_date if not provided
                if not booking.check_out_date:
                    duration = int(request.POST.get('duration', 1))
                    booking.check_out_date = booking.check_in_date + timedelta(days=30 * duration)
                    logger.debug(f"Set default check_out_date: {booking.check_out_date} based on duration: {duration} months")
                
                booking.status = 'Pending'
                logger.debug(f"Attempting to save booking with data: student={booking.student.id}, hostel={booking.hostel.id if booking.hostel else None}, room_type={booking.room_type}, check_in_date={booking.check_in_date}, check_out_date={booking.check_out_date}")
                booking.save()
                
                logger.info(f"Booking {booking.id} created successfully for student {booking.student.username}")
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Booking created successfully!',
                        'booking_id': booking.id
                    })
                
                messages.success(request, 'Booking request has been submitted successfully!')
                return redirect('warden:manage_booking')
                
        except Exception as e:
            logger.exception(f"Error saving booking: {str(e)}")
            error_message = f"Error saving booking: {str(e)}. Please check the data and try again."
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': error_message
                }, status=500)
            
            messages.error(request, error_message)
            return redirect('warden:manage_booking')
            
    except Exception as e:
        logger.exception(f"Unexpected error in create_booking: {str(e)}")
        error_message = f"Unexpected error in create_booking: {str(e)}. Please try again or contact support."
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': error_message
            }, status=500)
        
        messages.error(request, error_message)
        return redirect('warden_manage_booking')
    
    # If we get here, it's a GET request or form was invalid
    initial_data = {}
    if hasattr(request.user, 'student') and not is_staff:
        initial_data['student'] = request.user.student
    
    # Set default hostel for wardens in initial data for GET request
    if is_staff and hasattr(request.user, 'warden_profile'):
        warden_profile = request.user.warden_profile
        assigned_hostel = HostelWardens.objects.filter(warden=warden_profile).first()
        if assigned_hostel:
            initial_data['hostel'] = assigned_hostel.hostel
            logger.debug(f"Set initial hostel to {assigned_hostel.hostel.name} for warden {request.user.username} in GET request")
    
    form = BookingRequestForm(user=request.user, initial=initial_data)
    
    # Get available hostels for the form
    hostels = Hostels.objects.prefetch_related(
        Prefetch('roomtyperate_set', 
                queryset=RoomTypeRate.objects.all().only('room_type', 'per_head_rent'),
                to_attr='room_types')
    ).all()
    
    # Prepare hostels JSON for JavaScript
    hostels_data = [
        {
            'id': hostel.id,
            'name': hostel.name,
            'room_types': [
                {
                    'room_type': rt.room_type,
                    'per_head_rent': float(rt.per_head_rent) if rt.per_head_rent else 0.0
                } for rt in hostel.room_types
            ]
        } for hostel in hostels
    ]
    hostels_json = mark_safe(json.dumps(hostels_data, ensure_ascii=False))
    
    return render(request, 'warden/warden_create_booking.html', {
        'form': form,
        'hostels': hostels,  # Pass QuerySet for template
        'hostels_json': hostels_json,  # Pass JSON for JavaScript
        'is_staff': is_staff,
        'min_date': timezone.now().strftime('%Y-%m-%d'),
        'default_check_out': (timezone.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    })

@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
def booking_details(request, booking_id):
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return HttpResponseForbidden()

    try:
        booking = get_object_or_404(BookingRequest.objects.select_related('student', 'hostel', 'room_assignment'), id=booking_id)
        
        # Ensure warden is authorized to view this booking
        warden_profile = request.user.warden_profile
        assigned_hostel = HostelWardens.objects.filter(warden=warden_profile).first().hostel
        
        if not assigned_hostel or booking.hostel != assigned_hostel:
            return JsonResponse({'error': 'You are not authorized to view this booking.'}, status=403)

        student_cnic = 'N/A'
        if hasattr(booking.student, 'student'):
            student_cnic = booking.student.student.cnic
        elif hasattr(booking.student, 'cnic'):
            student_cnic = booking.student.cnic

        assigned_room = 'N/A'
        if hasattr(booking, 'room_assignment') and booking.room_assignment:
            assigned_room = booking.room_assignment.room.room_number if booking.room_assignment.room else 'N/A'
        elif hasattr(booking, 'assigned_room') and booking.assigned_room:
            assigned_room = booking.assigned_room.room_number if booking.assigned_room else 'N/A'

        data = {
            'id': booking.id,
            'student_name': booking.student.get_full_name() if hasattr(booking.student, 'get_full_name') else f"{booking.student.first_name} {booking.student.last_name}",
            'student_email': booking.student.email,
            'student_cnic': student_cnic,
            'hostel_name': booking.hostel.name,
            'room_type': booking.room_type,
            'check_in_date': booking.check_in_date.strftime('%Y-%m-%d') if booking.check_in_date else 'N/A',
            'request_date': booking.request_date.strftime('%Y-%m-%d %H:%M') if booking.request_date else 'N/A',
            'status': booking.status,
            'assigned_room': assigned_room,
            'admin_notes': booking.admin_notes if booking.admin_notes else 'N/A'
        }
        return JsonResponse(data)
    except BookingRequest.DoesNotExist:
        return JsonResponse({'error': 'Booking not found'}, status=404)
    except Exception as e:
        logger.exception(f"Error fetching booking details for booking_id={booking_id}: {str(e)}")
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)

# The duplicate approve_booking function has been removed and merged into the primary function above.

# This duplicate function has been removed as it was causing conflicts with the primary reject_booking function

@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
def manage_rooms(request):
    warden_profile = request.user.warden_profile
    assigned_hostel = HostelWardens.objects.filter(warden=warden_profile).first().hostel if HostelWardens.objects.filter(warden=warden_profile).exists() else None
    
    if not assigned_hostel:
        messages.error(request, 'You are not assigned to any hostel.')
        return redirect('warden:dashboard')
    
    rooms = Rooms.objects.filter(hostel=assigned_hostel).order_by('room_number')
    
    # Calculate available and occupied rooms based on current_occupants and capacity
    available_rooms_count = sum(1 for room in rooms if room.current_occupants < room.capacity)
    total_rooms_count = rooms.count()
    occupied_rooms_count = total_rooms_count - available_rooms_count
    
    context = {
        'page_title': 'Manage Rooms',
        'hostel': assigned_hostel,
        'rooms': rooms,
        'total_rooms': total_rooms_count,
        'available_rooms': available_rooms_count,
        'occupied_rooms': occupied_rooms_count,
    }
    return render(request, 'warden/warden_rooms.html', context)

@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
def search_student(request):
    query = request.GET.get('q', '')
    if not query:
        return JsonResponse({'students': []})
        
    students = Student.objects.filter(
        Q(user__first_name__icontains=query) |
        Q(user__last_name__icontains=query) |
        Q(cnic__icontains=query)
    )[:10]  # Limit to 10 results for performance
    
    students_data = []
    for student in students:
        students_data.append({
            'id': student.user.id,
            'name': student.user.get_full_name(),
            'cnic': student.cnic
        })
        
    return JsonResponse({'students': students_data})

@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
def room_assignments(request):
    warden_profile = request.user.warden_profile
    assigned_hostel = HostelWardens.objects.filter(warden=warden_profile).first().hostel if HostelWardens.objects.filter(warden=warden_profile).exists() else None
    
    if not assigned_hostel:
        messages.error(request, 'You are not assigned to any hostel.')
        return redirect('warden:dashboard')
    
    assignments = RoomAssignment.objects.filter(
        room__hostel=assigned_hostel,
        is_active=True
    ).select_related('booking__student', 'room')
    
    # Apply filters from GET parameters
    student_name = request.GET.get('student_name')
    if student_name:
        assignments = assignments.filter(
            Q(booking__student__first_name__icontains=student_name) |
            Q(booking__student__last_name__icontains=student_name)
        )
    
    room_number = request.GET.get('room_number')
    if room_number:
        assignments = assignments.filter(room__room_number__icontains=room_number)
    
    room_type = request.GET.get('room_type')
    if room_type:
        assignments = assignments.filter(room__room_type__icontains=room_type)
    
    assignments = assignments.order_by('room__room_number')
    
    context = {
        'page_title': 'Room Assignments',
        'hostel': assigned_hostel,
        'assignments': assignments,
        'total_assignments': assignments.count(),
        'student_name_filter': student_name,
        'room_number_filter': room_number,
        'room_type_filter': room_type,
    }
    return render(request, 'warden/warden_room_assignments.html', context)

def warden_logout(request):
    logout(request)
    return redirect('warden:login')
