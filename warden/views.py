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
from django.db.models import Q, F
from django.utils import timezone
from datetime import datetime
from django.shortcuts import get_object_or_404
from django.db import transaction
import logging
from coustom_admin.models import Student, Rooms, Wardens, BookingRequest, HostelWardens, RoomAssignment
from .forms import StudentRegistrationForm

logger = logging.getLogger(__name__)

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


class WardenManageBookingsView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = BookingRequest
    template_name = 'warden/managebookings.html'
    context_object_name = 'bookings'
    paginate_by = 10

    def test_func(self):
        return hasattr(self.request.user, 'warden_profile')

    def get_queryset(self):
        # Get the warden's assigned hostel
        warden = self.request.user.warden_profile
        hostel = HostelWardens.objects.filter(warden=warden).first().hostel

        queryset = BookingRequest.objects.filter(hostel=hostel)

        # Handle search
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(student__first_name__icontains=search_query) |
                Q(student__last_name__icontains=search_query)
            )

        # Handle status filter
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        return queryset.select_related('student', 'hostel')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Manage Bookings'
        context['status_filter'] = self.request.GET.get('status', '')
        context['search_query'] = self.request.GET.get('search', '')
        context['today'] = timezone.now().date()
        return context

@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
def search_students(request):
    query = request.GET.get('query', '')
    if not query:
        return JsonResponse([])

    students = Student.objects.filter(
        Q(user__first_name__icontains=query) |
        Q(user__last_name__icontains=query) |
        Q(cnic__icontains=query)
    )[:5]

    data = [{
        'id': student.id,
        'full_name': f"{student.user.first_name} {student.user.last_name}",
        'cnic': student.cnic
    } for student in students]

    return JsonResponse(data, safe=False)

@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
def create_booking(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    try:
        # Get the warden's assigned hostel
        warden = request.user.warden_profile
        hostel = HostelWardens.objects.filter(warden=warden).first().hostel

        student_id = request.POST.get('student_id')
        student = get_object_or_404(Student, id=student_id)

        booking = BookingRequest.objects.create(
            student=student.user,
            hostel=hostel,
            room_type=request.POST.get('room_type'),
            check_in_date=request.POST.get('check_in_date'),
            status='Pending'
        )

        messages.success(request, 'Booking created successfully!')
        return JsonResponse({'status': 'success'})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@csrf_exempt
def approve_booking(request, booking_id):
    logger.info(f"approve_booking called by warden {request.user.username} for booking_id={booking_id}, method={request.method}")
    if request.method == 'POST':
        try:
            logger.info(f"Request POST data: {request.POST}")
            booking = get_object_or_404(BookingRequest.objects.select_related('hostel', 'student'), id=booking_id)
            logger.info(f"Found booking: {booking.id}, status={booking.status}, hostel={booking.hostel.name if booking.hostel else 'N/A'}")

            # Ensure warden is associated with the hostel of the booking
            warden_user = request.user
            try:
                warden_profile = Wardens.objects.get(user=warden_user)
                if not HostelWardens.objects.filter(warden=warden_profile, hostel=booking.hostel).exists():
                    logger.warning(f"Warden {warden_user.username} not authorized for hostel {booking.hostel.name}")
                    return JsonResponse({'status': 'error', 'message': 'You are not authorized to manage bookings for this hostel.'}, status=403)
            except Wardens.DoesNotExist:
                logger.error(f"Warden profile not found for user {warden_user.username}")
                return JsonResponse({'status': 'error', 'message': 'Warden profile not found.'}, status=404)

            if booking.status != 'Pending':
                logger.warning(f"Booking {booking.id} is not in 'Pending' state (current: {booking.status})")
                return JsonResponse({'status': 'error', 'message': f'Booking is already {booking.status.lower()}.'}, status=400)

            room_id = request.POST.get('room_id')
            admin_notes = request.POST.get('admin_notes', '')
            logger.info(f"Room ID from form: {room_id}, Admin notes: {admin_notes}")

            if not room_id:
                logger.warning("No room_id provided in request")
                return JsonResponse({'status': 'error', 'message': 'Please select a room to assign.'}, status=400)

            selected_room = get_object_or_404(Rooms, id=room_id, hostel=booking.hostel, room_type=booking.room_type)
            logger.info(f"Found room: {selected_room.id}, type={selected_room.room_type}, capacity={selected_room.capacity}, current_occupants={selected_room.current_occupants}")

            if selected_room.current_occupants >= selected_room.capacity:
                logger.warning(f"Room {selected_room.id} is full: {selected_room.current_occupants}/{selected_room.capacity}")
                return JsonResponse({'status': 'error', 'message': 'Selected room is already full. Please choose another room.'}, status=400)

            logger.info("Starting transaction to update booking and room")
            with transaction.atomic():
                booking.status = 'Approved'

                booking.admin_notes = admin_notes # Warden's notes
                booking.save()
                logger.info(f"Updated booking {booking.id} to Approved with room {selected_room.id}")

                RoomAssignment.objects.create(
                    booking=booking,
                    room=selected_room,
                    check_in_date=booking.check_in_date,
                    check_out_date=booking.check_out_date, # Use booking's check_out_date
                    is_active=True,
                    assigned_by=request.user,
                    notes=f"Booking approved by Warden {request.user.get_full_name() or request.user.username}. {admin_notes}"
                )
                logger.info(f"Created RoomAssignment for booking {booking.id} in room {selected_room.id}")

                selected_room.current_occupants = F('current_occupants') + 1
                selected_room.save(update_fields=['current_occupants'])
                selected_room.refresh_from_db() # Refresh to get the updated current_occupants

                if selected_room.current_occupants >= selected_room.capacity:
                    selected_room.status = 'Occupied'
                    selected_room.save(update_fields=['status'])
                logger.info(f"Updated room {selected_room.id} occupancy to {selected_room.current_occupants} and status to {selected_room.status}")

            return JsonResponse({'status': 'success', 'message': 'Booking approved and room assigned successfully!'})

        except BookingRequest.DoesNotExist:
            logger.error(f"Booking not found: {booking_id}")
            return JsonResponse({'status': 'error', 'message': 'Booking not found.'}, status=404)
        except Rooms.DoesNotExist:
            logger.error(f"Room not found or does not match criteria: room_id={room_id}")
            return JsonResponse({'status': 'error', 'message': 'Selected room not found or does not match booking criteria.'}, status=404)
        except Exception as e:
            logger.exception(f"Error approving booking {booking_id} by warden {request.user.username}: {str(e)}")
            return JsonResponse({'status': 'error', 'message': f'An error occurred: {str(e)}'}, status=500)

    logger.warning(f"Invalid request method: {request.method} for approve_booking by warden {request.user.username}")
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=400)



@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
def get_available_rooms(request):
    if request.method == 'GET':
        room_type = request.GET.get('room_type')
        check_in_date_str = request.GET.get('check_in_date')
        booking_id = request.GET.get('booking_id') # Optional: for editing existing booking

        logger.info(f"get_available_rooms called with room_type={room_type}, check_in_date_str={check_in_date_str}, booking_id={booking_id}")

        if not room_type or not check_in_date_str:
            logger.warning("Room type or check-in date missing.")
            return JsonResponse({'status': 'error', 'message': 'Room type and check-in date are required.'}, status=400)

        try:
            check_in_date = datetime.strptime(check_in_date_str, '%Y-%m-%d').date()
            logger.info(f"Parsed check_in_date: {check_in_date}")
        except ValueError:
            logger.error(f"Invalid date format: {check_in_date_str}")
            return JsonResponse({'status': 'error', 'message': 'Invalid date format.'}, status=400)

        try:
            warden_profile = request.user.warden_profile
            assigned_hostel = HostelWardens.objects.filter(warden=warden_profile).first().hostel
            if not assigned_hostel:
                logger.warning(f"Warden {request.user.username} is not assigned to any hostel.")
                return JsonResponse({'status': 'error', 'message': 'Warden is not assigned to any hostel.'}, status=403)
            logger.info(f"Warden {request.user.username} assigned to hostel: {assigned_hostel.name}")
        except Wardens.DoesNotExist:
            logger.error(f"Warden profile not found for user {request.user.username}.")
            return JsonResponse({'status': 'error', 'message': 'Warden profile not found.'}, status=404)

        # Filter rooms by type, hostel, and capacity
        initial_rooms_queryset = Rooms.objects.filter(
            room_type=room_type,
            hostel=assigned_hostel,
            current_occupants__lt=F('capacity')
        )
        logger.info(f"Initial rooms matching type and capacity: {initial_rooms_queryset.count()}")

        # Exclude rooms that are already assigned for the given check-in date
        # This assumes a RoomAssignment is for a specific check-in date and implies occupancy
        # If a room can have multiple assignments on the same day (e.g., short-term stays),
        # this logic might need adjustment.
        assigned_room_ids = RoomAssignment.objects.filter(
            check_in_date=check_in_date,
            room__in=initial_rooms_queryset
        ).values_list('room_id', flat=True)
        logger.info(f"Rooms already assigned on {check_in_date}: {len(assigned_room_ids)}")

        available_rooms = initial_rooms_queryset.exclude(id__in=assigned_room_ids).order_by('room_number')
        logger.info(f"Final available rooms after excluding assigned: {available_rooms.count()}")

        rooms_data = [{
            'id': room.id,
            'room_number': room.room_number,
            'capacity': room.capacity,
            'current_occupants': room.current_occupants
        } for room in available_rooms]

        return JsonResponse(rooms_data, safe=False)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
def booking_details(request, booking_id):
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return HttpResponseForbidden()

    try:
        booking = get_object_or_404(BookingRequest.objects.select_related('student__user', 'hostel', 'assigned_room'), id=booking_id)
        
        # Ensure warden is authorized to view this booking
        warden_profile = request.user.warden_profile
        assigned_hostel = HostelWardens.objects.filter(warden=warden_profile).first().hostel
        
        if not assigned_hostel or booking.hostel != assigned_hostel:
            return JsonResponse({'error': 'You are not authorized to view this booking.'}, status=403)

        data = {
            'id': booking.id,
            'student_name': booking.student.get_full_name(),
            'student_email': booking.student.email,
            'student_cnic': booking.student.student.cnic if hasattr(booking.student, 'student') else 'N/A',
            'hostel_name': booking.hostel.name,
            'room_type': booking.room_type,
            'check_in_date': booking.check_in_date.strftime('%Y-%m-%d'),
            'request_date': booking.request_date.strftime('%Y-%m-%d %H:%M'),
            'status': booking.status,
            'assigned_room': booking.assigned_room.room_number if booking.assigned_room else 'N/A',
            'admin_notes': booking.admin_notes if booking.admin_notes else 'N/A'
        }
        return JsonResponse(data)
    except BookingRequest.DoesNotExist:
        return JsonResponse({'error': 'Booking not found'}, status=404)
    except Exception as e:
        logger.exception(f"Error fetching booking details for booking_id={booking_id}: {str(e)}")
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)

@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
def reject_booking(request, booking_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    try:
        warden = request.user.warden_profile
        hostel = HostelWardens.objects.filter(warden=warden).first().hostel
        booking = get_object_or_404(BookingRequest, id=booking_id, hostel=hostel)

        if booking.status != 'Pending':
            return JsonResponse({'error': 'Booking is not in pending state'}, status=400)

        booking.status = 'Rejected'
        booking.admin_notes = request.POST.get('admin_notes')
        booking.save()

        return JsonResponse({'status': 'success'})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@user_passes_test(lambda u: hasattr(u, 'warden_profile'))
def booking_details(request, booking_id):
    try:
        warden = request.user.warden_profile
        hostel = HostelWardens.objects.filter(warden=warden).first().hostel
        booking = get_object_or_404(BookingRequest, id=booking_id, hostel=hostel)

        data = {
            'student_name': f"{booking.student.first_name} {booking.student.last_name}",
            'room_type': booking.room_type,
            'check_in_date': booking.check_in_date.strftime('%Y-%m-%d'),
            'duration': booking.duration if hasattr(booking, 'duration') else None,
            'status': booking.status,
            'admin_notes': booking.admin_notes
        }

        return JsonResponse(data)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    


def warden_logout(request):
    logout(request)
    return redirect('warden:login')