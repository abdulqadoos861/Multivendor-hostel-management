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
from django.db.models import Count, Prefetch, F, Q, Sum
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
        
        try:
            warden = self.request.user.warden_profile
            context['warden'] = warden
            
            # Get the hostel assigned to this warden
            assigned_hostel = HostelWardens.objects.filter(warden=warden).first()
            if assigned_hostel:
                hostel = assigned_hostel.hostel
                context['hostel'] = hostel
                
                # Calculate room statistics for the assigned hostel
                total_rooms = Rooms.objects.filter(hostel=hostel).count()
                available_rooms = Rooms.objects.filter(hostel=hostel, current_occupants__lt=F('capacity')).count()
                occupied_rooms = total_rooms - available_rooms
                
                context['total_rooms'] = total_rooms
                context['available_rooms'] = available_rooms
                context['occupied_rooms'] = occupied_rooms
                
                # Calculate booking statistics for the assigned hostel
                total_bookings = BookingRequest.objects.filter(hostel=hostel).count()
                pending_bookings = BookingRequest.objects.filter(hostel=hostel, status='Pending').count()
                approved_bookings = BookingRequest.objects.filter(hostel=hostel, status='Approved').count()
                rejected_bookings = BookingRequest.objects.filter(hostel=hostel, status='Rejected').count()
                
                context['total_bookings'] = total_bookings
                context['pending_bookings'] = pending_bookings
                context['approved_bookings'] = approved_bookings
                context['rejected_bookings'] = rejected_bookings
                
                # Calculate active room assignments for the assigned hostel
                active_assignments = RoomAssignment.objects.filter(room__hostel=hostel, is_active=True).count()
                context['active_assignments'] = active_assignments
                
                # Calculate total students currently assigned to rooms in this hostel
                total_students_assigned = RoomAssignment.objects.filter(
                    room__hostel=hostel,
                    is_active=True
                ).values('booking__student').distinct().count()
                context['total_students_assigned'] = total_students_assigned
                
                # Calculate total security deposits collected for this hostel
                from coustom_admin.models import SecurityDeposit
                total_security_deposits = SecurityDeposit.objects.filter(
                    booking__hostel=hostel
                ).count()
                total_security_amount = SecurityDeposit.objects.filter(
                    booking__hostel=hostel
                ).aggregate(total_amount=Sum('amount'))['total_amount'] or 0.0
                context['total_security_deposits'] = total_security_deposits
                context['total_security_amount'] = total_security_amount
                
                # Calculate total monthly fees collected for this hostel
                from coustom_admin.models import StudentMonthlyFee
                total_monthly_fees = StudentMonthlyFee.objects.filter(
                    hostel=hostel, payment_status='Paid'
                ).count()
                total_monthly_fees_amount = StudentMonthlyFee.objects.filter(
                    hostel=hostel, payment_status='Paid'
                ).aggregate(total_amount=Sum('total_fee'))['total_amount'] or 0.0
                context['total_monthly_fees'] = total_monthly_fees
                context['total_monthly_fees_amount'] = total_monthly_fees_amount
                
                # Calculate complaints statistics if applicable
                try:
                    from student.models import Complaint
                    total_complaints = Complaint.objects.filter(hostel=hostel, submitted_to='Warden').count()
                    pending_complaints = Complaint.objects.filter(hostel=hostel, submitted_to='Warden', status='Pending').count()
                    resolved_complaints = Complaint.objects.filter(hostel=hostel, submitted_to='Warden', status='Resolved').count()
                    
                    context['total_complaints'] = total_complaints
                    context['pending_complaints'] = pending_complaints
                    context['resolved_complaints'] = resolved_complaints
                except ImportError:
                    context['total_complaints'] = 0
                    context['pending_complaints'] = 0
                    context['resolved_complaints'] = 0
            else:
                context['error_message'] = 'No hostel assigned to your profile. Please contact an administrator.'
        except ObjectDoesNotExist:
            context['error_message'] = 'Warden profile not found. Please contact an administrator.'
            
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
                    street=form.cleaned_data['street'],
                    area=form.cleaned_data['area'],
                    city=form.cleaned_data['city'],
                    district=form.cleaned_data['district'],
                    gender=form.cleaned_data['gender'],
                    institute=form.cleaned_data['institute'],
                    guardian_name=form.cleaned_data['guardian_name'],
                    guardian_contact=form.cleaned_data['guardian_contact'],
                    guardian_cnic=form.cleaned_data['guardian_cnic'],
                    guardian_relation=form.cleaned_data['guardian_relation']
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
        # Construct full address from individual components if available
        address_parts = []
        if student.street:
            address_parts.append(student.street)
        if student.area:
            address_parts.append(student.area)
        if student.city:
            address_parts.append(student.city)
        if student.district:
            address_parts.append(student.district)
        full_address = ", ".join(address_parts) if address_parts else "N/A"
        
        data = {
            'first_name': student.user.first_name,
            'last_name': student.user.last_name,
            'email': student.user.email,
            'contact_number': student.contact_number,
            'institute': student.institute,
            'cnic': student.cnic,
            'address': full_address,
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
        security_deposit_amount = request.POST.get('security_deposit_amount', '')
        payment_method = request.POST.get('payment_method', 'Cash')  # Default to 'Cash' if not provided
        transaction_id = request.POST.get('transaction_id', '')

        if not all([booking_id, room_id]):
            error_msg = 'Missing required fields for approval.'
            messages.error(request, error_msg)
            logger.warning(f"Missing required fields in approve_booking: booking_id={booking_id}, room_id={room_id}")
            return JsonResponse({'status': 'error', 'message': error_msg}, status=400)

        if not security_deposit_amount:
            error_msg = 'Missing security deposit amount.'
            messages.error(request, error_msg)
            logger.warning(f"Missing security deposit amount: amount={security_deposit_amount}")
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

                # Update booking status
                booking.status = 'Approved'
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

                # Create SecurityDeposit record
                from coustom_admin.models import SecurityDeposit
                SecurityDeposit.objects.create(
                    booking=booking,
                    amount=float(security_deposit_amount) if security_deposit_amount else 0.0,
                    payment_date=timezone.now().date(),
                    payment_method=payment_method,
                    transaction_id=transaction_id if transaction_id else None,
                    payment_status='Completed',  # Align with model default
                    received_by=request.user
                )
                logger.info(f"Security deposit created for booking {booking_id} with amount {security_deposit_amount}")

            success_msg = 'Booking approved, room assigned, and security deposit recorded successfully!'
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
            error_msg = f'Invalid date format or security deposit amount: {str(ve)}'
            messages.error(request, error_msg)
            logger.error(f"Value error in approve_booking for booking ID {booking_id}: {str(ve)}")
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
        
        # Set fixed hostel for wardens
        if is_staff and hasattr(request.user, 'warden_profile'):
            warden_profile = request.user.warden_profile
            assigned_hostel = HostelWardens.objects.filter(warden=warden_profile).first()
            if assigned_hostel:
                form_data['hostel'] = str(assigned_hostel.hostel.id)
                logger.debug(f"Set fixed hostel to {assigned_hostel.hostel.name} for warden {request.user.username}")
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
        return redirect('warden:manage_booking')
    
    # If we get here, it's a GET request or form was invalid
    initial_data = {}
    if hasattr(request.user, 'student') and not is_staff:
        initial_data['student'] = request.user.student
    
    # Set fixed hostel for wardens in initial data for GET request
    if is_staff and hasattr(request.user, 'warden_profile'):
        warden_profile = request.user.warden_profile
        assigned_hostel = HostelWardens.objects.filter(warden=warden_profile).first()
        if assigned_hostel:
            initial_data['hostel'] = assigned_hostel.hostel
            logger.debug(f"Set fixed hostel to {assigned_hostel.hostel.name} for warden {request.user.username} in GET request")
    
    form = BookingRequestForm(user=request.user, initial=initial_data)
    
    # For wardens, do not pass hostels for selection
    if is_staff and hasattr(request.user, 'warden_profile'):
        return render(request, 'warden/warden_create_booking.html', {
            'form': form,
            'is_staff': is_staff,
            'min_date': timezone.now().strftime('%Y-%m-%d'),
            'default_check_out': (timezone.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        })
    else:
        # Get available hostels for the form (for non-wardens if applicable)
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
        room__hostel=assigned_hostel
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
    
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        assignments = assignments.filter(is_active=True)
    elif status_filter == 'inactive':
        assignments = assignments.filter(is_active=False)
    
    assignments = assignments.order_by('-is_active', 'room__room_number')
    
    context = {
        'page_title': 'Room Assignments',
        'hostel': assigned_hostel,
        'assignments': assignments,
        'total_assignments': assignments.count(),
        'student_name_filter': student_name,
        'room_number_filter': room_number,
        'room_type_filter': room_type,
        'status_filter': status_filter,
    }
    return render(request, 'warden/warden_room_assignments.html', context)

@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
def checkout_student(request, assignment_id):
    if request.method == 'POST':
        try:
            assignment = RoomAssignment.objects.get(id=assignment_id, is_active=True)
            room = assignment.room
            
            # Ensure warden is authorized to checkout from this hostel
            warden_profile = request.user.warden_profile
            assigned_hostel = HostelWardens.objects.filter(warden=warden_profile).first().hostel
            if room.hostel != assigned_hostel:
                messages.error(request, 'You are not authorized to perform this action.')
                return redirect('warden:room_assignments')
            
            with transaction.atomic():
                # Mark assignment as inactive and set checkout date
                assignment.is_active = False
                assignment.check_out_date = timezone.now().date()
                assignment.save()
                
                # Update booking status if needed
                booking = assignment.booking
                booking.status = 'Completed'
                booking.save()
                
                # Update security deposit status to refunded
                from coustom_admin.models import SecurityDeposit
                security_deposit = SecurityDeposit.objects.filter(booking=booking).first()
                if security_deposit:
                    security_deposit.payment_status = 'Refunded'
                    security_deposit.save()
                    logger.info(f"Security deposit status updated to Refunded for booking {booking.id}")
                
                # Decrement current occupants for the room
                if room.current_occupants > 0:
                    room.current_occupants = F('current_occupants') - 1
                    room.save()
            
            messages.success(request, f'Student checked out from room {room.room_number} successfully.')
        except RoomAssignment.DoesNotExist:
            messages.error(request, 'Room assignment not found or already checked out.')
        except Exception as e:
            messages.error(request, f'Error during checkout: {str(e)}')
    else:
        messages.error(request, 'Invalid request method for checkout.')
    
    return redirect('warden:room_assignments')

@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
def room_assignment_details(request, assignment_id):
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return HttpResponseForbidden()
        
    try:
        assignment = RoomAssignment.objects.select_related(
            'booking__student', 'room__hostel', 'assigned_by'
        ).get(id=assignment_id)
        
        # Ensure warden is authorized to view this assignment
        warden_profile = request.user.warden_profile
        try:
            assigned_hostel = HostelWardens.objects.filter(warden=warden_profile).first().hostel
        except AttributeError:
            logger.error(f"No hostel assigned to warden for assignment_id={assignment_id}")
            return JsonResponse({'error': 'No hostel assigned to your profile. Please contact an administrator.'}, status=403)
            
        if assignment.room.hostel != assigned_hostel:
            return JsonResponse({'error': 'You are not authorized to view this assignment.'}, status=403)
        
        student = assignment.booking.student
        room = assignment.room
        hostel = room.hostel
        booking = assignment.booking
        
        # Calculate duration if possible
        duration = "N/A"
        try:
            if assignment.check_in_date and assignment.check_out_date:
                delta = assignment.check_out_date - assignment.check_in_date
                duration = f"{delta.days // 30} months" if delta.days > 30 else f"{delta.days} days"
        except Exception as e:
            logger.error(f"Error calculating duration for assignment_id={assignment_id}: {str(e)}")
        
        # Safely access user data with detailed error logging
        student_name = "N/A"
        student_email = "N/A"
        student_contact = "N/A"
        try:
            student_name = f"{student.first_name} {student.last_name}" if student.first_name or student.last_name else student.username
            student_email = student.email if student.email else "N/A"
        except Exception as e:
            logger.error(f"Error accessing student data for assignment_id={assignment_id}: {str(e)}")
        
        try:
            # Attempt to access student contact through a related Student profile if it exists
            if hasattr(student, 'student'):
                student_contact = getattr(student.student, 'contact_number', "N/A") or "N/A"
            else:
                student_contact = "N/A"
        except Exception as e:
            logger.error(f"Error accessing student contact for assignment_id={assignment_id}: {str(e)}")
        
        # Safely access assigned_by data
        assigned_by_name = "N/A"
        try:
            if assignment.assigned_by:
                assigned_by_name = f"{assignment.assigned_by.first_name} {assignment.assigned_by.last_name}" if assignment.assigned_by.first_name or assignment.assigned_by.last_name else assignment.assigned_by.username
        except Exception as e:
            logger.error(f"Error accessing assigned_by for assignment_id={assignment_id}: {str(e)}")
        
        # Safely access room floor_number
        floor = "N/A"
        try:
            floor = getattr(room, 'floor_number', "N/A")
            if floor is None:
                floor = "N/A"
        except Exception as e:
            logger.error(f"Error accessing room floor_number for assignment_id={assignment_id}: {str(e)}")
        
        # Safely access hostel name
        hostel_name = "N/A"
        try:
            hostel_name = getattr(hostel, 'name', "N/A")
        except Exception as e:
            logger.error(f"Error accessing hostel name for assignment_id={assignment_id}: {str(e)}")
        
        # Safely access room info
        room_info = "N/A"
        try:
            room_info = f"{getattr(room, 'room_number', 'N/A')} ({getattr(room, 'room_type', 'N/A')})"
        except Exception as e:
            logger.error(f"Error accessing room info for assignment_id={assignment_id}: {str(e)}")
        
        # Safely access dates with robust error handling
        assigned_on = "N/A"
        try:
            if hasattr(assignment, 'check_in_date') and assignment.check_in_date is not None:
                assigned_on = assignment.check_in_date.strftime('%m/%d/%Y')
        except Exception as e:
            logger.error(f"Error formatting assigned_on for assignment_id={assignment_id}: {str(e)}")
        
        check_in = "N/A"
        try:
            if hasattr(booking, 'check_in_date') and booking.check_in_date is not None:
                check_in = booking.check_in_date.strftime('%m/%d/%Y')
        except Exception as e:
            logger.error(f"Error formatting check_in for assignment_id={assignment_id}: {str(e)}")
        
        check_out = "N/A"
        try:
            if hasattr(booking, 'check_out_date') and booking.check_out_date is not None:
                check_out = booking.check_out_date.strftime('%m/%d/%Y')
        except Exception as e:
            logger.error(f"Error formatting check_out for assignment_id={assignment_id}: {str(e)}")
        
        data = {
            # Student Information
            'student_name': student_name,
            'student_email': student_email,
            'student_contact': student_contact,
            # Room Information
            'hostel_name': hostel_name,
            'room_info': room_info,
            'floor': floor,
            # Assignment Details
            'assigned_on': assigned_on,
            'assigned_by': assigned_by_name,
            'status': "Active" if assignment.is_active else "Inactive",
            # Booking Information
            'check_in': check_in,
            'check_out': check_out,
            'duration': duration
        }
        return JsonResponse(data)
    except RoomAssignment.DoesNotExist:
        return JsonResponse({'error': 'Room assignment not found'}, status=404)
    except AttributeError as ae:
        logger.exception(f"AttributeError fetching room assignment details for assignment_id={assignment_id}: {str(ae)}")
        return JsonResponse({'error': f'Attribute error occurred: {str(ae)}'}, status=500)
    except Exception as e:
        logger.exception(f"Unexpected error fetching room assignment details for assignment_id={assignment_id}: {str(e)}")
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)

def warden_logout(request):
    logout(request)
    return redirect('warden:login')

from django.views.decorators.csrf import csrf_protect

from django.views.decorators.csrf import csrf_exempt

@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
def change_room_requests(request):
    warden_profile = request.user.warden_profile
    assigned_hostel = HostelWardens.objects.filter(warden=warden_profile).first().hostel if HostelWardens.objects.filter(warden=warden_profile).exists() else None
    
    if not assigned_hostel:
        messages.error(request, 'You are not assigned to any hostel.')
        return redirect('warden:dashboard')
    
    from student.models import RoomChangeRequest
    requests = RoomChangeRequest.objects.filter(
        current_booking__hostel=assigned_hostel
    ).select_related('student', 'current_booking', 'current_booking__room_assignment').order_by('-request_date')
    
    # Apply filters from GET parameters
    student_name = request.GET.get('student_name')
    if student_name:
        requests = requests.filter(
            Q(student__first_name__icontains=student_name) |
            Q(student__last_name__icontains=student_name)
        )
    
    room_number = request.GET.get('room_number')
    if room_number:
        requests = requests.filter(current_booking__assigned_room__room_number__icontains=room_number)
    
    status_filter = request.GET.get('status')
    if status_filter == 'pending':
        requests = requests.filter(status='Pending')
    elif status_filter == 'approved':
        requests = requests.filter(status='Approved')
    elif status_filter == 'rejected':
        requests = requests.filter(status='Rejected')
    
    context = {
        'page_title': 'Change Room Requests',
        'hostel': assigned_hostel,
        'requests': requests,
        'total_requests': requests.count(),
        'student_name_filter': student_name,
        'room_number_filter': room_number,
        'status_filter': status_filter,
    }
    
    return render(request, 'warden/warden_change_room_requests.html', context)

@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
def change_room_request_details(request, request_id):
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return HttpResponseForbidden()
        
    try:
        from student.models import RoomChangeRequest
        change_request = RoomChangeRequest.objects.select_related(
            'student', 'current_booking', 'current_booking__room_assignment', 'current_booking__hostel'
        ).get(id=request_id)
        
        # Ensure warden is authorized to view this request
        warden_profile = request.user.warden_profile
        assigned_hostel = HostelWardens.objects.filter(warden=warden_profile).first().hostel
        if change_request.current_booking.hostel != assigned_hostel:
            return JsonResponse({'error': 'You are not authorized to view this request.'}, status=403)
        
        student = change_request.student
        current_booking = change_request.current_booking
        hostel = current_booking.hostel if current_booking else None
        room_assignment = current_booking.room_assignment if current_booking else None
        room = room_assignment.room if room_assignment else None
        
        # Safely access student data
        student_name = f"{student.first_name} {student.last_name}" if student.first_name or student.last_name else student.username
        student_email = student.email if student.email else "N/A"
        student_contact = "N/A"
        if hasattr(student, 'student'):
            student_contact = getattr(student.student, 'contact_number', "N/A") or "N/A"
        
        # Safely access room information
        hostel_name = hostel.name if hostel else "N/A"
        room_info = f"{room.room_number} ({room.room_type})" if room else "N/A"
        floor = getattr(room, 'floor_number', "N/A") if room else "N/A"
        
        # Request details
        request_date = change_request.request_date.strftime('%Y-%m-%d') if change_request.request_date else "N/A"
        requested_room_type = change_request.requested_room_type if change_request.requested_room_type else "Any"
        status = change_request.status
        reason = change_request.reason if change_request.reason else "Not provided"
        
        data = {
            'student_name': student_name,
            'student_email': student_email,
            'student_contact': student_contact,
            'hostel_name': hostel_name,
            'room_info': room_info,
            'floor': floor,
            'request_date': request_date,
            'requested_room_type': requested_room_type,
            'status': status,
            'reason': reason
        }
        return JsonResponse(data)
    except RoomChangeRequest.DoesNotExist:
        return JsonResponse({'error': 'Room change request not found'}, status=404)
    except Exception as e:
        logger.exception(f"Error fetching room change request details for request_id={request_id}: {str(e)}")
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)

@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
@csrf_exempt
def approve_room_change_request(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)
        
    try:
        logger.info("Entering approve_room_change_request function")
        request_id = request.POST.get('request_id')
        new_room_id = request.POST.get('room_id')
        admin_notes = request.POST.get('admin_notes', '')
        
        logger.debug(f"Received request_id: {request_id}, room_id: {new_room_id}, admin_notes: {admin_notes}")
        if not request_id or not new_room_id:
            logger.warning("Missing required fields in approve_room_change_request")
            return JsonResponse({'status': 'error', 'message': 'Missing required fields'}, status=400)
            
        from student.models import RoomChangeRequest
        from coustom_admin.models import Rooms, RoomAssignment
        
        logger.info("Starting transaction for room change approval")
        with transaction.atomic():
            change_request = RoomChangeRequest.objects.get(id=request_id)
            logger.debug(f"Retrieved RoomChangeRequest with id: {request_id}")
            
            # Ensure warden is authorized
            warden_profile = request.user.warden_profile
            assigned_hostel = HostelWardens.objects.filter(warden=warden_profile).first().hostel
            if change_request.current_booking.hostel != assigned_hostel:
                logger.warning(f"Unauthorized access attempt for hostel by warden {request.user.username}")
                return JsonResponse({'status': 'error', 'message': 'You are not authorized to perform this action'}, status=403)
                
            if change_request.status != 'Pending':
                logger.warning(f"Room change request {request_id} already processed with status: {change_request.status}")
                return JsonResponse({'status': 'error', 'message': 'This request has already been processed'}, status=400)
                
            new_room = Rooms.objects.get(id=new_room_id)
            logger.debug(f"Retrieved new room with id: {new_room_id}")
            
            # Check if the new room has capacity
            if new_room.current_occupants >= new_room.capacity:
                logger.warning(f"New room {new_room_id} is already full: occupants={new_room.current_occupants}, capacity={new_room.capacity}")
                return JsonResponse({'status': 'error', 'message': 'Selected room is already full'}, status=400)
                
            # Update all current active room assignments for this booking
            current_assignments = RoomAssignment.objects.filter(booking=change_request.current_booking, is_active=True)
            if current_assignments.exists():
                for assignment in current_assignments:
                    current_room = assignment.room
                    logger.debug(f"Retrieved current assignment for booking {change_request.current_booking.id}, current room: {current_room.id}")
                    
                    # Mark old assignment as inactive
                    assignment.is_active = False
                    assignment.check_out_date = timezone.now().date()
                    assignment.save()
                    logger.info(f"Marked old assignment as inactive for room {current_room.id}")
                    
                    # Decrease occupants in old room
                    if current_room.current_occupants > 0:
                        current_room.current_occupants = F('current_occupants') - 1
                        current_room.save()
                        logger.info(f"Decreased occupant count in old room {current_room.id}")
            else:
                logger.warning(f"No active room assignment found for booking {change_request.current_booking.id}")
                
            # Check if a RoomAssignment already exists for this booking
            existing_assignment = RoomAssignment.objects.filter(booking=change_request.current_booking).first()
            if existing_assignment:
                # Update existing assignment
                existing_assignment.room = new_room
                existing_assignment.check_in_date = timezone.now().date()
                existing_assignment.assigned_by = request.user
                existing_assignment.is_active = True
                existing_assignment.check_out_date = None  # Reset check_out_date since it's a new assignment
                existing_assignment.save()
                logger.info(f"Updated existing assignment for room {new_room.id}")
            else:
                # Create new room assignment if none exists
                new_assignment = RoomAssignment.objects.create(
                    booking=change_request.current_booking,
                    room=new_room,
                    check_in_date=timezone.now().date(),
                    assigned_by=request.user,
                    is_active=True
                )
                logger.info(f"Created new assignment for room {new_room.id}")
            
            # Increase occupants in new room
            new_room.current_occupants = F('current_occupants') + 1
            new_room.save()
            logger.info(f"Increased occupant count in new room {new_room.id}")
            
            # Update booking with new room
            change_request.current_booking.assigned_room = new_room
            change_request.current_booking.save()
            logger.info(f"Updated booking with new room {new_room.id}")
            
            # Update the request status
            change_request.status = 'Approved'
            change_request.admin_notes = admin_notes
            change_request.new_room = new_room
            change_request.processed_date = timezone.now()
            change_request.processed_by = request.user
            change_request.save()
            logger.info(f"Updated room change request {request_id} to Approved status")
            
        logger.info(f"Successfully approved room change request {request_id}")
        return JsonResponse({'status': 'success', 'message': 'Room change request approved successfully'})
    except RoomChangeRequest.DoesNotExist:
        logger.error(f"Room change request not found for id: {request_id}")
        return JsonResponse({'status': 'error', 'message': 'Room change request not found'}, status=404)
    except Rooms.DoesNotExist:
        logger.error(f"Selected room not found for id: {new_room_id}")
        return JsonResponse({'status': 'error', 'message': 'Selected room not found'}, status=404)
    except RoomAssignment.DoesNotExist:
        logger.error(f"Current room assignment not found for booking related to request {request_id}")
        return JsonResponse({'status': 'error', 'message': 'Current room assignment not found'}, status=404)
    except Exception as e:
        logger.exception(f"Error approving room change request: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Error approving request: {str(e)}'}, status=500)

@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
@csrf_exempt
def reject_room_change_request(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)
        
    try:
        request_id = request.POST.get('request_id')
        admin_notes = request.POST.get('admin_notes', '')
        
        if not request_id:
            return JsonResponse({'status': 'error', 'message': 'Missing required fields'}, status=400)
            
        from student.models import RoomChangeRequest
        
        with transaction.atomic():
            change_request = RoomChangeRequest.objects.get(id=request_id)
            
            # Ensure warden is authorized
            warden_profile = request.user.warden_profile
            assigned_hostel = HostelWardens.objects.filter(warden=warden_profile).first().hostel
            if change_request.current_booking.hostel != assigned_hostel:
                return JsonResponse({'status': 'error', 'message': 'You are not authorized to perform this action'}, status=403)
                
            if change_request.status != 'Pending':
                return JsonResponse({'status': 'error', 'message': 'This request has already been processed'}, status=400)
                
            # Update the request status
            change_request.status = 'Rejected'
            change_request.admin_notes = admin_notes
            change_request.processed_date = timezone.now()
            change_request.processed_by = request.user
            change_request.save()
            
        return JsonResponse({'status': 'success', 'message': 'Room change request rejected successfully'})
    except RoomChangeRequest.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Room change request not found'}, status=404)
    except Exception as e:
        logger.exception(f"Error rejecting room change request: {str(e)}")
        return JsonResponse({'status': 'error', 'message': f'Error rejecting request: {str(e)}'}, status=500)

@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
def get_available_rooms_for_change(request):
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return HttpResponseForbidden()
        
    try:
        request_id = request.GET.get('request_id')
        if not request_id:
            return JsonResponse({'error': 'Request ID is required'}, status=400)
            
        from student.models import RoomChangeRequest
        change_request = RoomChangeRequest.objects.select_related('current_booking', 'current_booking__hostel').get(id=request_id)
        
        # Ensure warden is authorized
        warden_profile = request.user.warden_profile
        assigned_hostel = HostelWardens.objects.filter(warden=warden_profile).first().hostel
        if change_request.current_booking.hostel != assigned_hostel:
            return JsonResponse({'error': 'You are not authorized to perform this action'}, status=403)
            
        hostel = change_request.current_booking.hostel
        requested_room_type = change_request.requested_room_type
        
        from coustom_admin.models import Rooms
        # Filter rooms by hostel and optionally by requested room type, ensuring available capacity
        query = Rooms.objects.filter(
            hostel=hostel,
            current_occupants__lt=F('capacity')
        )
        
        if requested_room_type and requested_room_type != "Any":
            query = query.filter(room_type=requested_room_type)
            
        available_rooms = query.values('id', 'room_number', 'room_type', 'current_occupants', 'capacity')
        
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
    except RoomChangeRequest.DoesNotExist:
        return JsonResponse({'error': 'Room change request not found'}, status=404)
    except Exception as e:
        logger.exception(f"Error fetching available rooms for change request: {str(e)}")
        return JsonResponse({'error': f'Error fetching available rooms: {str(e)}'}, status=500)

@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
@csrf_exempt
def warden_complaints(request):
    warden_profile = request.user.warden_profile
    assigned_hostel = HostelWardens.objects.filter(warden=warden_profile).first().hostel if HostelWardens.objects.filter(warden=warden_profile).exists() else None
    
    if not assigned_hostel:
        messages.error(request, 'You are not assigned to any hostel.')
        return redirect('warden:dashboard')
    
    from student.models import Complaint
    complaints = Complaint.objects.filter(
        hostel=assigned_hostel,
        submitted_to='Warden'
    ).order_by('-created_at')
    
    if request.method == 'POST':
        complaint_id = request.POST.get('complaint_id')
        status = request.POST.get('status')
        if complaint_id and status:
            try:
                complaint = Complaint.objects.get(complaint_id=complaint_id, hostel=assigned_hostel)
                complaint.status = status
                if status == 'Resolved':
                    complaint.resolved_at = timezone.now()
                    complaint.resolved_by = request.user
                complaint.save()
                messages.success(request, f'Complaint #{complaint_id} status updated to {status}.')
            except Complaint.DoesNotExist:
                messages.error(request, f'Complaint #{complaint_id} not found or you are not authorized to update it.')
            except Exception as e:
                messages.error(request, f'Error updating complaint: {str(e)}')
            return redirect('warden:warden_complaints')
    
    context = {
        'page_title': 'Manage Complaints',
        'complaints': complaints,
        'total_complaints': complaints.count(),
    }
    return render(request, 'warden/warden_complaints.html', context, using=None)

@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
def security_deposits(request):
    warden_profile = request.user.warden_profile
    assigned_hostel = HostelWardens.objects.filter(warden=warden_profile).first().hostel if HostelWardens.objects.filter(warden=warden_profile).exists() else None
    
    if not assigned_hostel:
        messages.error(request, 'You are not assigned to any hostel.')
        return redirect('warden:dashboard')
    
    from coustom_admin.models import SecurityDeposit
    deposits = SecurityDeposit.objects.filter(
        booking__hostel=assigned_hostel
    ).select_related('booking__student', 'booking', 'received_by').order_by('-payment_date')
    
    # Apply filters from GET parameters if needed
    student_name = request.GET.get('student_name')
    if student_name:
        deposits = deposits.filter(
            Q(booking__student__first_name__icontains=student_name) |
            Q(booking__student__last_name__icontains=student_name)
        )
    
    status_filter = request.GET.get('status')
    if status_filter == 'pending':
        deposits = deposits.filter(payment_status='Pending')
    elif status_filter == 'approved':
        deposits = deposits.filter(payment_status='Approved')
    elif status_filter == 'refunded':
        deposits = deposits.filter(payment_status='Refunded')
    
    context = {
        'page_title': 'Security Deposits',
        'deposits': deposits,
        'total_deposits': deposits.count(),
        'student_name_filter': student_name,
        'status_filter': status_filter,
    }
    return render(request, 'warden/warden_security_deposits.html', context)

@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
def security_deposit_details(request, deposit_id):
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return HttpResponseForbidden()
        
    try:
        from coustom_admin.models import SecurityDeposit
        deposit = SecurityDeposit.objects.select_related('booking__student', 'booking__hostel', 'received_by').get(id=deposit_id)
        
        # Ensure warden is authorized to view this deposit
        warden_profile = request.user.warden_profile
        assigned_hostel = HostelWardens.objects.filter(warden=warden_profile).first().hostel
        if not assigned_hostel:
            logger.error(f"No hostel assigned to warden for deposit_id={deposit_id}")
            return JsonResponse({'error': 'No hostel assigned to your profile. Please contact an administrator.'}, status=403)
            
        if deposit.booking.hostel != assigned_hostel:
            logger.warning(f"Unauthorized access attempt for deposit_id={deposit_id} by warden {request.user.username}")
            return JsonResponse({'error': 'You are not authorized to view this deposit.'}, status=403)
        
        student = deposit.booking.student
        if not student:
            logger.error(f"No student associated with booking for deposit_id={deposit_id}")
            return JsonResponse({'error': 'No student associated with this deposit.'}, status=404)
            
        student_name = f"{student.first_name} {student.last_name}" if student.first_name or student.last_name else student.username
        student_email = student.email if student.email else "N/A"
        student_contact = "N/A"
        if hasattr(student, 'student'):
            student_contact = getattr(student.student, 'contact_number', "N/A") or "N/A"
        
        data = {
            'student_name': student_name,
            'student_email': student_email,
            'student_contact': student_contact,
            'amount': str(deposit.amount) if deposit.amount else "N/A",
            'payment_date': deposit.payment_date.strftime('%Y-%m-%d') if deposit.payment_date else "N/A",
            'payment_method': deposit.payment_method if deposit.payment_method else "N/A",
            'status': deposit.payment_status if deposit.payment_status else "N/A",
            'transaction_id': deposit.transaction_id if deposit.transaction_id else "N/A",
            'receipt_number': deposit.receipt_number if deposit.receipt_number else "N/A",
            'received_by': deposit.received_by.get_full_name() if deposit.received_by else "N/A",
            'notes': deposit.notes if deposit.notes else "No notes provided."
        }
        logger.info(f"Successfully retrieved details for deposit_id={deposit_id}")
        return JsonResponse(data)
    except SecurityDeposit.DoesNotExist:
        logger.error(f"Security deposit not found for deposit_id={deposit_id}")
        return JsonResponse({'error': 'Security deposit not found'}, status=404)
    except AttributeError as ae:
        logger.exception(f"AttributeError fetching security deposit details for deposit_id={deposit_id}: {str(ae)}")
        return JsonResponse({'error': f'Attribute error occurred: {str(ae)}'}, status=500)
    except Exception as e:
        logger.exception(f"Unexpected error fetching security deposit details for deposit_id={deposit_id}: {str(e)}")
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)

@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
def monthly_fees(request):
    """
    View to display all student monthly fees for the warden's assigned hostel with filtering options.
    """
    warden_profile = request.user.warden_profile
    assigned_hostel = HostelWardens.objects.filter(warden=warden_profile).first().hostel if HostelWardens.objects.filter(warden=warden_profile).exists() else None
    
    if not assigned_hostel:
        messages.error(request, 'You are not assigned to any hostel.')
        return redirect('warden:dashboard')
    
    from coustom_admin.models import StudentMonthlyFee
    import calendar
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from django.utils import timezone
    
    # Get all monthly fees for the assigned hostel
    fees = StudentMonthlyFee.objects.filter(hostel=assigned_hostel).select_related('student', 'student__user').all().order_by('-year', '-month', '-created_at')
    
    # Apply search filter if provided
    search_query = request.GET.get('search', '')
    if search_query:
        fees = fees.filter(
            Q(student__user__first_name__icontains=search_query) |
            Q(student__user__last_name__icontains=search_query) |
            Q(student__user__email__icontains=search_query) |
            Q(transaction_id__icontains=search_query)
        )
    
    # Apply month filter if provided
    month_filter = request.GET.get('month', '')
    if month_filter:
        fees = fees.filter(month=month_filter)
    
    # Apply year filter if provided
    year_filter = request.GET.get('year', '')
    if year_filter:
        fees = fees.filter(year=year_filter)
    
    # Prepare month choices for filter dropdown (only current and previous month)
    current_date = timezone.now().date()
    current_month = current_date.month
    current_year = current_date.year
    previous_month = current_month - 1 if current_month > 1 else 12
    previous_year = current_year if current_month > 1 else current_year - 1
    
    months = [
        (current_month, calendar.month_name[current_month]),
        (previous_month, calendar.month_name[previous_month])
    ]
    years = [current_year, previous_year] if previous_year != current_year else [current_year]
    
    # Pagination
    paginator = Paginator(fees, 10)  # Show 10 fees per page
    page = request.GET.get('page')
    try:
        fees_page = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        fees_page = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page of results
        fees_page = paginator.page(paginator.num_pages)
    
    context = {
        'page_title': 'Monthly Fees',
        'warden_hostel': assigned_hostel,
        'fees': fees_page,
        'page_obj': fees_page,
        'months': months,
        'years': years,
        'search_query': search_query,
        'month_filter': month_filter,
        'year_filter': year_filter,
    }
    
    return render(request, "warden/monthly_fees.html", context)

@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
def generate_monthly_fees(request):
    """
    View to generate monthly fees for students in the warden's assigned hostel.
    """
    warden_profile = request.user.warden_profile
    assigned_hostel = HostelWardens.objects.filter(warden=warden_profile).first().hostel if HostelWardens.objects.filter(warden=warden_profile).exists() else None
    
    if not assigned_hostel:
        messages.error(request, 'You are not assigned to any hostel.')
        return redirect('warden:dashboard')
    
    from coustom_admin.models import StudentMonthlyFee, RoomAssignment, RoomTypeRate
    from messincharge.models import MessAttendance, MessCharges, MessStudent
    from django.utils import timezone
    from datetime import date
    import calendar
    
    if request.method == 'POST':
        month = int(request.POST.get('month', timezone.now().month))
        year = timezone.now().year  # Always use current year
        electricity_bill = float(request.POST.get('electricity_bill', 0.0))
        
        # Check if the selected month is not the current or previous month of the current year
        current_date = timezone.now().date()
        selected_date = date(year, month, 1)
        current_month_date = date(current_date.year, current_date.month, 1)
        previous_month_date = date(current_date.year, current_date.month - 1, 1) if current_date.month > 1 else date(current_date.year - 1, 12, 1)
        if selected_date > current_month_date:
            messages.error(request, "You can only generate fees for the current or previous month.")
            return redirect('warden:generate_monthly_fees')
        elif selected_date != current_month_date and selected_date != previous_month_date:
            messages.error(request, "You can only generate fees for the current or previous month.")
            return redirect('warden:generate_monthly_fees')
        
        active_assignments = RoomAssignment.objects.filter(is_active=True, room__hostel=assigned_hostel)
        total_assignments = active_assignments.count()
        created_fees = 0
        
        if total_assignments == 0:
            messages.warning(request, "No active room assignments found for this hostel. No fee records generated.")
            return redirect('warden:monthly_fees')
            
        # Calculate per student electricity bill if total is provided
        electricity_per_student = electricity_bill / total_assignments if electricity_bill > 0 and total_assignments > 0 else 0.0
        
        for assignment in active_assignments:
            student = assignment.booking.student.student
            hostel = assignment.room.hostel
            
            if StudentMonthlyFee.objects.filter(student=student, month=month, year=year).exists():
                continue
            
            room_type = assignment.room.room_type
            if room_type in ['Triple', 'Quad']:
                room_type = 'Shared'
            try:
                rate = RoomTypeRate.objects.get(hostel=hostel, room_type=room_type)
                monthly_rent = int(rate.per_head_rent)
            except RoomTypeRate.DoesNotExist:
                monthly_rent = int(assignment.room.rent)
            
            try:
                mess_student = MessStudent.objects.get(student=student, hostel=hostel, is_active=True)
                last_day = calendar.monthrange(year, month)[1]
                start_date = date(year, month, 1)
                end_date = date(year, month, last_day)
                attendance_records = MessAttendance.objects.filter(
                    mess_student=mess_student,
                    date__range=[start_date, end_date]
                ).aggregate(
                    breakfast_count=Sum('breakfast'),
                    lunch_count=Sum('lunch'),
                    dinner_count=Sum('dinner')
                )
                
                breakfast_count = attendance_records['breakfast_count'] or 0
                lunch_count = attendance_records['lunch_count'] or 0
                dinner_count = attendance_records['dinner_count'] or 0
                
                charges = MessCharges.objects.filter(
                    hostel=hostel,
                    effective_from__lte=end_date
                ).order_by('-effective_from').first()
                
                if charges:
                    mess_expenses = int(
                        breakfast_count * 60 +
                        lunch_count * 60 +
                        dinner_count * 60
                    )
                else:
                    mess_expenses = 0
            except MessStudent.DoesNotExist:
                mess_expenses = 0
            
            next_month = month + 1 if month < 12 else 1
            next_year = year if month < 12 else year + 1
            due_date = date(next_year, next_month, 10)
            
            fee = StudentMonthlyFee(
                student=student,
                hostel=hostel,
                month=month,
                year=year,
                monthly_rent=monthly_rent,
                mess_expenses=mess_expenses,
                electricity_bill=electricity_per_student,
                due_date=due_date
            )
            fee.save()
            created_fees += 1
        
        if created_fees > 0:
            messages.success(request, f"Generated {created_fees} new monthly fee records for {month}/{year}.")
        else:
            messages.warning(request, f"No new monthly fee records generated for {month}/{year}. All records already exist.")
        return redirect('warden:monthly_fees')
    
    current_date = timezone.now().date()
    current_month = current_date.month
    current_year = current_date.year
    previous_month = current_month - 1 if current_month > 1 else 12
    previous_year = current_year if current_month > 1 else current_year - 1
    
    months = [
        (current_month, calendar.month_name[current_month]),
        (previous_month, calendar.month_name[previous_month])
    ]
    years = [current_year, previous_year] if previous_year != current_year else [current_year]
    
    context = {
        'page_title': 'Generate Monthly Fees',
        'warden_hostel': assigned_hostel,
        'current_month': current_month,
        'current_year': current_year,
        'months': months,
        'years': years,
    }
    return render(request, "warden/generate_monthly_fees.html", context)

@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
def collect_monthly_fee(request, fee_id):
    """
    View to collect payment for a specific monthly fee.
    """
    warden_profile = request.user.warden_profile
    assigned_hostel = HostelWardens.objects.filter(warden=warden_profile).first().hostel if HostelWardens.objects.filter(warden=warden_profile).exists() else None
    
    if not assigned_hostel:
        messages.error(request, 'You are not assigned to any hostel.')
        return redirect('warden:dashboard')
    
    from coustom_admin.models import StudentMonthlyFee
    from django.utils import timezone
    
    try:
        fee = StudentMonthlyFee.objects.get(id=fee_id, hostel=assigned_hostel)
    except StudentMonthlyFee.DoesNotExist:
        messages.error(request, 'Fee record not found or you are not authorized to access it.')
        return redirect('warden:monthly_fees')
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'Cash')
        transaction_id = request.POST.get('transaction_id', '')
        notes = request.POST.get('notes', '')
        
        fee.payment_status = 'Paid'
        fee.payment_date = timezone.now().date()
        fee.transaction_id = transaction_id if transaction_id else None
        fee.notes = notes
        fee.collected_by = request.user  # Store the user who collected the fee
        fee.save()
        
        messages.success(request, f"Payment for {fee.student.user.get_full_name()} for {fee.month}/{fee.year} has been recorded.")
        return redirect('warden:monthly_fees')
    
    context = {
        'page_title': 'Collect Monthly Fee',
        'fee': fee,
    }
    return render(request, "warden/collect_monthly_fee.html", context)
