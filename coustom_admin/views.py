from datetime import datetime, date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import Q, Count, F, Case, When, Value, IntegerField, CharField, Prefetch
from django.db.models.functions import TruncMonth, ExtractMonth, ExtractYear, Concat
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.template.loader import render_to_string
from django.core.mail import send_mail
from decimal import Decimal
from django.conf import settings
import calendar
import json
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.contrib.auth import get_user_model

# Get the User model
User = get_user_model()

from .forms import StudentRegistrationForm, BookingRequestForm, MessInchargeForm
from .models import Hostels, RoomTypeRate, Rooms, BookingRequest, Student, RoomAssignment, Wardens, HostelWardens, MessIncharge, SecurityDeposit
from django.urls import reverse
import json
import re
import logging
from django.utils.safestring import mark_safe
from django.db.models import Prefetch

logger = logging.getLogger(__name__)

@login_required
def users(request):
    """
    View to display all non-superuser users
    """
    users = User.objects.filter(is_superuser=False).order_by('-date_joined')
    context = {
        'users': users,
        'page_title': 'Manage Users',
        'active_menu': 'users',
    }
    return render(request, 'users.html', context)

def is_student(user):
    return hasattr(user, 'student')

@login_required
def get_room_rate(request, hostel_id, room_type):
    """
    Get the per head rent for a specific hostel and room type
    """
    logger.info(f'get_room_rate called with hostel_id={hostel_id}, room_type={room_type}')
    try:
        # Convert room_type to title case to match database
        room_type = room_type.title()
        logger.info(f'Looking up rate for hostel_id={hostel_id}, room_type={room_type}')
        
        try:
            rate = RoomTypeRate.objects.get(hostel_id=hostel_id, room_type__iexact=room_type)
            logger.info(f'Found rate: {rate}')
            return JsonResponse({
                'status': 'success',
                'per_head_rent': float(rate.per_head_rent)
            })
        except RoomTypeRate.MultipleObjectsReturned:
            # In case of multiple matches (shouldn't happen due to unique_together constraint)
            logger.warning(f'Multiple rates found for hostel_id={hostel_id}, room_type={room_type}')
            rate = RoomTypeRate.objects.filter(hostel_id=hostel_id, room_type__iexact=room_type).first()
            return JsonResponse({
                'status': 'success',
                'per_head_rent': float(rate.per_head_rent)
            })
    except RoomTypeRate.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Room rate not found for the selected hostel and room type'
        }, status=404)
    except Exception as e:
        logger.error(f'Error getting room rate: {str(e)}')
        return JsonResponse({
            'status': 'error',
            'message': 'An error occurred while fetching room rate'
        }, status=500)

def is_admin(user):
    return user.is_staff

def admin_login(request):
    try:
        if request.user.is_authenticated:
            return redirect("dashboard")
            
        if request.method == "POST":
            username = request.POST.get("username")
            password = request.POST.get("password")
            
            user = authenticate(request, username=username, password=password)
            
            if user is not None and user.is_superuser:
                login(request, user)
                return redirect("dashboard")
            else:
                messages.error(request, "Invalid credentials")
                return render(request, "admin_login.html")
        
        return render(request, "admin_login.html")
        
    except Exception as e:
        print(e)
        messages.error(request, "An error occurred. Please try again.")
        return render(request, "admin_login.html")

@login_required
def dashboard(request):
    # Fetch statistics for the dashboard
    from .models import Hostels, Rooms, BookingRequest, Student
    from student.models import Complaint, Feedback
    from messincharge.models import Expenses
    from django.db.models import Sum, Count

    total_hostels = Hostels.objects.count()
    total_rooms = Rooms.objects.count()
    active_bookings = BookingRequest.objects.filter(status='Approved').count()
    total_students = Student.objects.count()
    total_complaints = Complaint.objects.count()
    total_expenses = Expenses.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    total_wardens = Wardens.objects.count()
    total_feedback = Feedback.objects.count()
    recent_bookings = BookingRequest.objects.all().order_by('-request_date')[:5]
    recent_complaints = Complaint.objects.all().order_by('-created_at')[:5]
    last_updated = timezone.now().strftime('%Y-%m-%d %H:%M:%S')

    context = {
        'total_hostels': total_hostels,
        'total_rooms': total_rooms,
        'active_bookings': active_bookings,
        'total_students': total_students,
        'total_complaints': total_complaints,
        'total_expenses': total_expenses,
        'total_wardens': total_wardens,
        'total_feedback': total_feedback,
        'recent_bookings': recent_bookings,
        'recent_complaints': recent_complaints,
        'last_updated': last_updated,
    }
    return render(request, "dashboard.html", context)

@login_required
def dashboard_stats_api(request):
    """
    API endpoint to fetch real-time dashboard statistics.
    """
    from .models import Hostels, Rooms, BookingRequest, Student, Wardens
    from student.models import Complaint, Feedback
    from messincharge.models import Expenses
    from django.db.models import Sum

    stats = {
        'total_hostels': Hostels.objects.count(),
        'total_rooms': Rooms.objects.count(),
        'active_bookings': BookingRequest.objects.filter(status='Approved').count(),
        'total_students': Student.objects.count(),
        'total_complaints': Complaint.objects.count(),
        'total_expenses': Expenses.objects.aggregate(Sum('amount'))['amount__sum'] or 0,
        'total_wardens': Wardens.objects.count(),
        'total_feedback': Feedback.objects.count(),
        'last_updated': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    return JsonResponse({'status': 'success', 'stats': stats})

@login_required
def warden_dashboard(request):
    return render(request, "warden/warden_dashboard.html")

@login_required
def add_room(request):
    hostels = Hostels.objects.filter(status='Active')
    # Use select_related to fetch the related hostel data in a single query
    rooms = Rooms.objects.select_related('hostel').all()

    if request.method == 'POST':
        hostel_id = request.POST.get('hostel')
        floor_number = request.POST.get('floor_number')
        room_number = request.POST.get('room_number')
        room_type = request.POST.get('room_type')
        description = request.POST.get('description')

        try:
            hostel = Hostels.objects.get(id=hostel_id)
            try:
                floor_value = int(floor_number)
                if floor_value < 0 or floor_value > hostel.total_floors:
                    messages.error(request, f'Floor number must be between 0 and {hostel.total_floors}.')
                    return redirect('add_room')
            except ValueError:
                messages.error(request, 'Invalid floor number.')
                return redirect('add_room')

            if not room_number:
                messages.error(request, 'Room number is required.')
                return redirect('add_room')

            capacity = {'Single': 1, 'Double': 2, 'Shared': 4}.get(room_type, 1)
            rent = None
            try:
                rate = RoomTypeRate.objects.get(hostel_id=hostel_id, room_type=room_type)
                rent = rate.per_head_rent
            except RoomTypeRate.DoesNotExist:
                messages.error(request, f'No fixed rate found for {room_type} in {hostel.name}. Please set rates first.')
                return redirect('fixed_rates')

            if Rooms.objects.filter(room_number=room_number, hostel=hostel).exclude(id=room.id if 'room' in locals() else None).exists():
                messages.error(request, f'Room number {room_number} already exists in {hostel.name}.')
                return redirect('add_room')

            room = Rooms(
                hostel=hostel,
                room_number=room_number,
                floor_number=floor_value,
                room_type=room_type,
                rent=rent,
                description=description,
                capacity=capacity,
                current_occupants=0,
                status='Available'
            )
            room.save()
            messages.success(request, 'Room added successfully!')
            return redirect('add_room')
        except Hostels.DoesNotExist:
            messages.error(request, 'Invalid hostel selected.')
        except Exception as e:
            messages.error(request, f'Error adding room: {str(e)}')

    return render(request, 'add_room.html', {'hostels': hostels, 'rooms': rooms})

@login_required
@csrf_exempt
def update_room(request, room_id):
    room = get_object_or_404(Rooms, id=room_id)
    if request.method == 'POST':
        try:
            hostel_id = request.POST.get('hostel')
            floor_number = request.POST.get('floor_number')
            room_number = request.POST.get('room_number')
            room_type = request.POST.get('room_type')
            description = request.POST.get('description')

            try:
                hostel = Hostels.objects.get(id=hostel_id)
                floor_value = int(floor_number)
                if floor_value < 0 or floor_value > hostel.total_floors:
                    messages.error(request, f'Floor number must be between 0 and {hostel.total_floors}.')
                    return redirect('add_room')
            except ValueError:
                messages.error(request, 'Invalid floor number.')
                return redirect('add_room')

            if not room_number:
                messages.error(request, 'Room number is required.')
                return redirect('add_room')

            capacity = {'Single': 1, 'Double': 2, 'Shared': 4}.get(room_type, 1)
            rent = None
            try:
                rate = RoomTypeRate.objects.get(hostel_id=hostel_id, room_type=room_type)
                rent = rate.per_head_rent 
            except RoomTypeRate.DoesNotExist:
                messages.error(request, f'No fixed rate found for {room_type} in {hostel.name}. Please set rates first.')
                return redirect('fixed_rates')

            if Rooms.objects.filter(room_number=room_number, hostel=hostel).exclude(id=room.id).exists():
                messages.error(request, f'Room number {room_number} already exists in {hostel.name}.')
                return redirect('add_room')

            room.hostel_id = hostel
            room.floor_number = floor_value
            room.room_number = room_number
            room.room_type = room_type
            room.capacity = capacity
            room.rent = rent
            room.description = description
            room.save()

            messages.success(request, 'Room updated successfully!')
            return redirect('add_room')
        except Hostels.DoesNotExist:
            messages.error(request, 'Invalid hostel selected.')
        except Exception as e:
            messages.error(request, f'Error updating room: {str(e)}')
        return redirect('add_room')
    elif request.method == 'GET':
        try:
            room_data = {
                'status': 'success',
                'room': {
                    'id': room.id,
                    'room_number': room.room_number,
                    'floor_number': room.floor_number,
                    'room_type': room.room_type,
                    'description': room.description or '',
                    'hostel_id': room.hostel.id,
                    'hostel_name': room.hostel.name
                }
            }
            return JsonResponse(room_data)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    else:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

@login_required
@csrf_exempt
def delete_room(request, room_id):
    if request.method == 'POST':
        try:
            room = get_object_or_404(Rooms, id=room_id)
            if room.current_occupants > 0:
                return JsonResponse({'status': 'error', 'message': 'Cannot delete room with occupants.'}, status=400)
            room_number = room.room_number
            room.delete()
            return JsonResponse({'status': 'success', 'message': f'Room {room_number} deleted successfully'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error deleting room: {str(e)}'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

@login_required
def get_hostel_flats(request, hostel_id):
    try:
        hostel = Hostels.objects.get(id=hostel_id)
        return JsonResponse({'total_floors': hostel.total_floors})
    except Hostels.DoesNotExist:
        return JsonResponse({'error': 'Hostel not found'}, status=404)

@login_required
def fixed_rates(request):
    hostels = Hostels.objects.filter(status='Active')
    room_types = ['Single', 'Double', 'Shared']
    
    if request.method == 'POST':
        hostel_id = request.POST.get('hostel')
        for room_type in room_types:
            rate_key = f'rate_{room_type.lower()}'
            rate_value = request.POST.get(rate_key)
            try:
                rate_value = float(rate_value) if rate_value else None
                if rate_value is not None and rate_value <= 0:
                    messages.error(request, f'Rate for {room_type} must be positive.')
                    return redirect('fixed_rates')
            except ValueError:
                messages.error(request, f'Rate for {room_type} must be a valid number.')
                return redirect('fixed_rates')

            try:
                hostel = Hostels.objects.get(id=hostel_id)
                rate, created = RoomTypeRate.objects.update_or_create(
                    hostel=hostel,
                    room_type=room_type,
                    defaults={'per_head_rent': rate_value}
                )
            except Hostels.DoesNotExist:
                messages.error(request, 'Invalid hostel selected.')
                return redirect('fixed_rates')
            except Exception as e:
                messages.error(request, f'Error saving rate for {room_type}: {str(e)}')
                return redirect('fixed_rates')
        
        messages.success(request, 'Fixed rates updated successfully!')
        return redirect('fixed_rates')

    rates = RoomTypeRate.objects.all()
    return render(request, 'fixed_rates.html', {'hostels': hostels, 'room_types': room_types, 'rates': rates})



@login_required
def hostel_charges(request):
    hostels = Hostels.objects.all().order_by('name')
    selected_hostel_id = request.GET.get('hostel', '')
    search_query = request.GET.get('search', '')
    
    if search_query:
        hostels = hostels.filter(name__icontains=search_query)
    
    rates = []
    selected_hostel = None
    if selected_hostel_id:
        try:
            selected_hostel = Hostels.objects.get(id=selected_hostel_id)
            rates = RoomTypeRate.objects.filter(hostel=selected_hostel)
        except Hostels.DoesNotExist:
            messages.error(request, 'Selected hostel not found.')
    
    room_types = ['Single', 'Double', 'Shared']
    rates_dict = {rt: None for rt in room_types}
    for rate in rates:
        rates_dict[rate.room_type] = float(rate.per_head_rent)
    
    context = {
        'hostels': hostels,
        'selected_hostel': selected_hostel,
        'rates_dict': rates_dict,
        'room_types': room_types,
        'search_query': search_query,
    }
    
    return render(request, 'hostel_charges.html', context)

@login_required
def Addhostel(request):
    if request.method == "POST":
        try:
            name = request.POST.get("name")
            address = request.POST.get("address")
            gender = request.POST.get("gender")
            contact_number = request.POST.get("contact_number")
            total_floors = request.POST.get("total_floors")
            description = request.POST.get("description")
            created_at = request.POST.get("created_at")

            if not all([name, address, gender, contact_number, total_floors]):
                return JsonResponse({"status": "error", "message": "All required fields must be provided"}, status=400)

            try:
                total_floors = int(total_floors)
                if total_floors < 1:
                    return JsonResponse({"status": "error", "message": "Total floors must be at least 1"}, status=400)
            except ValueError:
                return JsonResponse({"status": "error", "message": "Total floors must be a valid number"}, status=400)

            if gender not in ['Male', 'male', 'Female', 'female', 'Other', 'other']:
                return JsonResponse({"status": "error", "message": "Invalid gender value"}, status=400)

            created_at_date = None
            if created_at:
                try:
                    created_at_date = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S")
                    created_at_date = timezone.make_aware(created_at_date)
                except ValueError:
                    return JsonResponse({"status": "error", "message": "Invalid date format for created_at"}, status=400)

            hostel = Hostels(
                name=name,
                address=address,
                gender=gender,
                contact_number=contact_number,
                total_floors=total_floors,
                description=description or "",
                created_at=created_at_date or timezone.now()
            )
            hostel.save()
            
            return JsonResponse({"status": "success", "message": "Hostel added successfully"})
        except Exception as e:
            print(f"Error in add_hostel: {e}")
            return JsonResponse({"status": "error", "message": f"Server error: {str(e)}"}, status=500)
    else:
        return JsonResponse({"status": "error", "message": "Invalid request method"}, status=400)

@login_required
def updateHostel(request, id):
    if request.method == "POST":
        try:
            hostel = get_object_or_404(Hostels, id=id)
            
            name = request.POST.get("name")
            address = request.POST.get("address")
            gender = request.POST.get("gender")
            contact_number = request.POST.get("contact_number")
            total_floors = request.POST.get("total_floors")
            description = request.POST.get("description", "")
            
            if not all([name, address, gender, contact_number, total_floors]):
                missing_fields = [field for field, value in {
                    'name': name, 'address': address, 'gender': gender,
                    'contact_number': contact_number, 'total_floors': total_floors
                }.items() if not value]
                return JsonResponse({
                    "status": "error",
                    "message": f"Missing required fields: {', '.join(missing_fields)}"
                }, status=400)

            try:
                total_floors = int(total_floors)
                if total_floors < 1:
                    return JsonResponse({
                        "status": "error",
                        "message": "Total floors must be at least 1"
                    }, status=400)
            except ValueError:
                return JsonResponse({
                    "status": "error",
                    "message": "Total floors must be a valid number"
                }, status=400)

            # Convert gender to title case for consistency
            gender = gender.title()
            if gender not in ['Male', 'Female']:
                return JsonResponse({
                    "status": "error",
                    "message": f"Invalid gender value: {gender}. Must be either 'Male' or 'Female'."
                }, status=400)

            hostel.name = name
            hostel.address = address
            hostel.gender = gender
            hostel.contact_number = contact_number
            hostel.total_floors = total_floors
            hostel.description = description
            
            hostel.save()
            
            return JsonResponse({
                "status": "success",
                "message": "Hostel updated successfully"
            })
        except Hostels.DoesNotExist:
            return JsonResponse({
                "status": "error",
                "message": f"Hostel with ID {id} not found"
            }, status=404)
        except Exception as e:
            print(f"Error in update_hostel: {str(e)}")
            return JsonResponse({
                "status": "error",
                "message": f"Server error: {str(e)}"
            }, status=500)
    else:
        return JsonResponse({
            "status": "error",
            "message": f"Invalid request method: {request.method}"
        }, status=400)

@login_required
@csrf_exempt
def deleteHostel(request, id):
    if request.method == "POST":
        try:
            hostel = get_object_or_404(Hostels, id=id)
            
            # Check for associated rooms
            if Rooms.objects.filter(hostel_id=hostel).exists():
                return JsonResponse({
                    "status": "error",
                    "message": "Cannot delete hostel with associated rooms. Delete rooms first."
                }, status=400)
            
            # Check for associated wardens
            if HostelWardens.objects.filter(hostel=hostel).exists():
                return JsonResponse({
                    "status": "error",
                    "message": "Cannot delete hostel with assigned wardens. Unassign wardens first."
                }, status=400)
            
            # Check for associated room type rates
            if RoomTypeRate.objects.filter(hostel=hostel).exists():
                return JsonResponse({
                    "status": "error",
                    "message": "Cannot delete hostel with associated room type rates. Delete rates first."
                }, status=400)
            
            # Check for students with this hostel as preferred
            if Student.objects.filter(preferred_hostel=hostel).exists():
                return JsonResponse({
                    "status": "error",
                    "message": "Cannot delete hostel with students preferring it. Update student preferences first."
                }, status=400)
            
            hostel_name = hostel.name
            hostel.delete()
            
            return JsonResponse({
                "status": "success",
                "message": f"Hostel '{hostel_name}' deleted successfully"
            })
        except Hostels.DoesNotExist:
            return JsonResponse({
                "status": "error",
                "message": f"Hostel with ID {id} not found"
            }, status=404)
        except Exception as e:
            print(f"Error in delete_hostel: {str(e)}")
            return JsonResponse({
                "status": "error",
                "message": f"Server error: {str(e)}"
            }, status=500)
    else:
        return JsonResponse({
            "status": "error",
            "message": "Invalid request method"
        }, status=400)

@login_required
def hostellist(request):
    hostels = Hostels.objects.all()
    return render(request, 'hostel_form.html', {'hostels': hostels})

@login_required
def get_hostels(request):
    hostels = Hostels.objects.all().values('id', 'name')
    return JsonResponse(list(hostels), safe=False)

@login_required
def room_assignments(request):
    """
    View to display all room assignments with filtering options
    """
    # Get filter parameters
    hostel_id = request.GET.get('hostel')
    room_type = request.GET.get('room_type')
    status = request.GET.get('status', 'active')  # Default to active assignments
    
    # Start with base queryset - optimized with select_related for all foreign keys
    assignments = RoomAssignment.objects.select_related(
        'booking',
        'booking__student',
        'room',
        'room__hostel',
        'assigned_by'
    ).order_by('-is_active', 'room__room_number')
    
    # Apply filters
    if hostel_id:
        assignments = assignments.filter(room__hostel_id=hostel_id)
    
    if room_type:
        assignments = assignments.filter(room__room_type=room_type)
    
    if status == 'active':
        assignments = assignments.filter(is_active=True)
    elif status == 'inactive':
        assignments = assignments.filter(is_active=False)
    
    # Get filter options for the template
    hostels = Hostels.objects.all()
    room_types = Rooms.ROOM_TYPES
    
    context = {
        'assignments': assignments,
        'hostels': hostels,
        'room_types': room_types,
        'selected_hostel': int(hostel_id) if hostel_id else '',
        'selected_room_type': room_type if room_type else '',
        'selected_status': status,
        'title': 'Room Assignments',
    }
    
    return render(request, 'room_assignments.html', context)

@login_required
@require_http_methods(["POST"])
def checkout_assignment(request, assignment_id):
    """
    Handle checkout of a student from a room assignment.
    """
    try:
        assignment = RoomAssignment.objects.get(id=assignment_id, is_active=True)
        room = assignment.room
        
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
            
            # Update room status if needed
            if room.current_occupants == 0:
                room.status = 'Available'
                room.save(update_fields=['status'])
        
        return JsonResponse({
            'status': 'success',
            'message': f'Student checked out from room {room.room_number} successfully.'
        })
    except RoomAssignment.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Room assignment not found or already checked out.'
        }, status=404)
    except Exception as e:
        logger.error(f"Error during checkout: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Error during checkout: {str(e)}'
        }, status=500)

@login_required
def hostels(request):
    hostels = Hostels.objects.all().order_by('-created_at')
    return render(request, "hostels.html", {'hostels': hostels})

@login_required
@csrf_exempt
def complaints(request):
    if request.method == 'POST':
        # Handle form submission for updating complaint status
        complaint_id = request.POST.get('complaint_id')
        status = request.POST.get('status')
        if complaint_id and status:
            try:
                from student.models import Complaint
                complaint = Complaint.objects.get(complaint_id=complaint_id)
                complaint.status = status
                if status == 'Resolved':
                    complaint.resolved_at = timezone.now()
                    complaint.resolved_by = request.user
                    complaint.resolution_notes = request.POST.get('resolution_notes', '')
                complaint.save()
                messages.success(request, f'Complaint #{complaint_id} status updated to {status}.')
            except Exception as e:
                messages.error(request, f'Error updating complaint #{complaint_id}: {str(e)}')
            return redirect('complaints')
    
    # Retrieve complaints submitted to admin
    try:
        from student.models import Complaint
        complaints = Complaint.objects.all()
        
        # Apply filters from GET parameters
        search_query = request.GET.get('search', '')
        if search_query:
            complaints = complaints.filter(
                Q(student__user__first_name__icontains=search_query) |
                Q(student__user__last_name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        hostel_filter = request.GET.get('hostel', '')
        if hostel_filter:
            complaints = complaints.filter(hostel_id=hostel_filter)
        
        status_filter = request.GET.get('status', '')
        if status_filter:
            complaints = complaints.filter(status=status_filter)
        
        complaints = complaints.order_by('-created_at')
    except Exception as e:
        messages.error(request, f'Error retrieving complaints: {str(e)}')
        complaints = []

    # Retrieve bookings for admin-assigned hostel
    bookings = []
    try:
        admin_hostels = HostelWardens.objects.filter(warden__user=request.user).values_list('hostel_id', flat=True)
        if admin_hostels:
            bookings = BookingRequest.objects.filter(hostel_id__in=admin_hostels).order_by('-request_date')
    except Exception as e:
        messages.error(request, f'Error retrieving bookings: {str(e)}')

    # Retrieve all hostels for filter dropdown
    hostels = Hostels.objects.all().order_by('name')

    context = {
        'complaints': complaints,
        'bookings': bookings,
        'hostels': hostels,
    }
    return render(request, "complaints.html", context)

@login_required
def expenses(request):
    """
    View to display all expenses from the Expenses model with search and filter functionality.
    """
    from messincharge.models import Expenses
    
    # Get all expenses with related hostel data
    expenses = Expenses.objects.select_related('hostel_id', 'created_by').all().order_by('-created_at')
    
    # Apply search filter if provided
    search_query = request.GET.get('search', '')
    if search_query:
        expenses = expenses.filter(
            Q(description__icontains=search_query) |
            Q(hostel_id__name__icontains=search_query) |
            Q(created_by__username__icontains=search_query)
        )
    
    # Apply category filter if provided
    filter_param = request.GET.get('filter', 'all')
    if filter_param == 'food':
        expenses = expenses.filter(description__icontains='food')
    elif filter_param == 'utilities':
        expenses = expenses.filter(description__icontains='utilities')
    
    context = {
        'expenses': expenses,
        'search_query': search_query,
        'filter_param': filter_param,
    }
    
    return render(request, "expenses.html", context)

@login_required
def manageStudent(request):
    """
    View for managing students with pagination and search functionality.
    """
    # Get all active students with related user data in a single query
    students = Student.objects.select_related('user').all()
    
    # Apply search filter if provided
    search_query = request.GET.get('search', '')
    if search_query:
        students = students.filter(
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(contact_number__icontains=search_query) |
            Q(cnic__icontains=search_query) |
            Q(institute__icontains=search_query)
        )
    
    # Apply status filter if provided
    status_filter = request.GET.get('status')
    if status_filter in ['active', 'inactive']:
        is_active = status_filter == 'active'
        students = students.filter(user__is_active=is_active)
    
    # Order by most recently created
    students = students.order_by('-user__date_joined')
    
    # Initialize the form
    form = StudentRegistrationForm()
    
    # Get all hostels for the form
    hostels = Hostels.objects.all()
    
    # Log the number of students being displayed
    logger.info(f'Displaying {students.count()} students in manageStudent view')
    
    if request.method == 'POST':
        print("DEBUG: POST request received")  # Debug log
        print("DEBUG: POST data:", request.POST)  # Debug log
        form = StudentRegistrationForm(request.POST)
        print("DEBUG: Form is valid:", form.is_valid())  # Debug log
        print("DEBUG: Form errors:", form.errors)  # Debug log
        
        if form.is_valid():
            print("DEBUG: Form is valid, processing...")  # Debug log
            try:
                with transaction.atomic():
                    print("DEBUG: Creating user...")  # Debug log
                    # Create user
                    user = User.objects.create_user(
                        username=form.cleaned_data['username'],
                        email=form.cleaned_data['email'],
                        password=form.cleaned_data['password'],
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name']
                    )
                    print(f"DEBUG: User created with ID: {user.id}")  # Debug log
                    
                    # Create student profile
                    print("DEBUG: Creating student profile...")  # Debug log
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
                        guardian_cnic=form.cleaned_data['guardian_cnic'],
                        guardian_relation=form.cleaned_data['guardian_relation'],
                        guardian_contact=form.cleaned_data['guardian_contact']
                    )
                    print(f"DEBUG: Student profile created with ID: {student.id}")  # Debug log
                    
                    # For AJAX requests, return success response
                    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
                    print(f"DEBUG: Is AJAX request: {is_ajax}")  # Debug log
                    
                    if is_ajax:
                        print("DEBUG: Processing AJAX response")  # Debug log
                        response_data = {
                            'status': 'success',
                            'message': 'Student registered successfully!',
                            'student_id': student.id,
                            'student_name': f"{user.first_name} {user.last_name}"
                        }
                        
                        # If booking data is present, include it in the response
                        if form.cleaned_data.get('hostel') and form.cleaned_data.get('room_type'):
                            print("DEBUG: Creating booking request")  # Debug log
                            BookingRequest.objects.create(
                                student=student,
                                hostel=form.cleaned_data['hostel'],
                                room_type=form.cleaned_data['room_type'],
                                check_in_date=form.cleaned_data['check_in_date'],
                                check_out_date=form.cleaned_data['check_out_date'],
                                message=form.cleaned_data.get('message', ''),
                                status='Pending'
                            )
                            response_data['message'] = 'Student registered and booking request submitted successfully!'
                        
                        print("DEBUG: Returning JSON response:", response_data)  # Debug log
                        return JsonResponse(response_data)
                    
                    # For regular form submission
                    if form.cleaned_data.get('hostel') and form.cleaned_data.get('room_type'):
                        print("DEBUG: Creating booking request (regular form)")  # Debug log
                        BookingRequest.objects.create(
                            student=student,
                            hostel=form.cleaned_data['hostel'],
                            room_type=form.cleaned_data['room_type'],
                            check_in_date=form.cleaned_data['check_in_date'],
                            check_out_date=form.cleaned_data['check_out_date'],
                            message=form.cleaned_data.get('message', ''),
                            status='Pending'
                        )
                        messages.success(request, 'Student registered and booking request submitted successfully!')
                    else:
                        messages.success(request, 'Student registered successfully!')
                    
                    print("DEBUG: Redirecting to manageStudent")  # Debug log
                    return redirect('manageStudent')
                    
            except Exception as e:
                error_msg = f'Error registering student: {str(e)}'
                print(f"ERROR: {error_msg}")  # Debug log
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
                messages.error(request, error_msg)
        else:
            print("DEBUG: Form is invalid")  # Debug log
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': 'Form validation failed', 'errors': form.errors}, status=400)
    
    return render(request, "manageStudent.html", {
        'students': students,
        'form': form,
        'hostels': hostels,
    })

@login_required
def edit_student(request, user_id):
    if request.method == 'GET':
        try:
            user = get_object_or_404(User, id=user_id)
            student = get_object_or_404(Student, user=user)
            
            student_data = {
                'status': 'success',
                'student': {
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'contact_number': student.contact_number,
                    'cnic': student.cnic,
                    'street': student.street or '',
                    'area': student.area or '',
                    'city': student.city or '',
                    'district': student.district or '',
                    'guardian_name': student.guardian_name or '',
                    'guardian_cnic': student.guardian_cnic or '',
                    'guardian_relation': student.guardian_relation or '',
                    'guardian_contact': student.guardian_contact or '',
                    'gender': student.gender,
                    'institute': student.institute,
                    'is_active': user.is_active
                }
            }
            return JsonResponse(student_data)
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    elif request.method == 'POST':
        try:
            # Check if the request is JSON
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST
                
            # Get form data
            username = data.get('username')
            email = data.get('email')
            first_name = data.get('first_name')
            last_name = data.get('last_name')
            contact_number = data.get('contact_number')
            cnic = data.get('cnic')
            address = data.get('address')
            gender = data.get('gender')
            institute = data.get('institute')
            is_active = data.get('is_active', 'true').lower() == 'true'
            
            # Validate required fields
            required_fields = [
                'username', 'email', 'first_name', 'last_name',
                'contact_number', 'cnic', 'gender', 'institute'
            ]
            
            missing_fields = [field for field in required_fields if not data.get(field)]
            if missing_fields:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Missing required fields: {", ".join(missing_fields)}'
                }, status=400)
            
            user = get_object_or_404(User, id=user_id)
            student = get_object_or_404(Student, user=user)
            
            # Check if username or email already exists for other users
            if User.objects.filter(username=username).exclude(id=user.id).exists():
                return JsonResponse({
                    'status': 'error',
                    'message': 'Username already exists',
                    'field': 'username'
                }, status=400)
                
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                return JsonResponse({
                    'status': 'error',
                    'message': 'Email already exists',
                    'field': 'email'
                }, status=400)
            
            # Validate CNIC format (if provided)
            if cnic and not cnic.isdigit():
                return JsonResponse({
                    'status': 'error',
                    'message': 'CNIC must contain only numbers',
                    'field': 'cnic'
                }, status=400)
            
            # Update user
            user.username = username
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.is_active = is_active
            user.save()
            
            # Update student profile
            student.contact_number = contact_number
            student.cnic = cnic
            student.street = data.get('street', '')
            student.area = data.get('area', '')
            student.city = data.get('city', '')
            student.district = data.get('district', '')
            student.guardian_name = data.get('guardian_name', '')
            student.guardian_cnic = data.get('guardian_cnic', '')
            student.guardian_relation = data.get('guardian_relation', '')
            student.guardian_contact = data.get('guardian_contact', '')
            student.gender = gender
            student.institute = institute
            student.save()
            
            # Prepare response
            response_data = {
                'status': 'success', 
                'message': 'Student updated successfully!',
                'redirect_url': reverse('manageStudent')
            }
            
            # If it's an AJAX request, return JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse(response_data)
            
            # For regular form submission
            messages.success(request, response_data['message'])
            return redirect('manageStudent')
            
        except Exception as e:
            error_msg = f'Error updating student: {str(e)}'
            logger.error(error_msg, exc_info=True)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': error_msg}, status=500)
            
            messages.error(request, error_msg)
            return redirect('manageStudent')
    
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@login_required
def delete_student(request, user_id):
    if request.method == 'POST':
        try:
            # Prevent deleting own account
            if request.user.id == user_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'You cannot delete your own account while logged in.'
                }, status=400)
            
            # Get the user and student objects
            user = get_object_or_404(User, id=user_id)
            student = get_object_or_404(Student, user=user)
            username = user.username
            
            # Check for any active bookings or important relations before deletion
            active_bookings = BookingRequest.objects.filter(
                student=student,
                status__in=['Pending', 'Approved']
            ).exists()
            
            if active_bookings:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Cannot delete student with active or pending bookings.'
                }, status=400)
            
            # Log the deletion
            logger.info(f'Deleting student: {username} (ID: {user_id})')
            
            # Perform the deletion in a transaction
            with transaction.atomic():
                # Delete related records first
                student.delete()
                user.delete()
            
            # Prepare success response
            response_data = {
                'status': 'success',
                'message': f'Student {username} has been deleted successfully.'
            }
            
            # If it's an AJAX request, return JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse(response_data)
            
            # For regular form submission
            messages.success(request, response_data['message'])
            return redirect('manageStudent')
            
        except Exception as e:
            error_msg = f'Error deleting student: {str(e)}'
            logger.error(error_msg, exc_info=True)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': error_msg}, status=500)
            
            messages.error(request, error_msg)
            return redirect('manageStudent')
    
    # If not a POST request
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method. Only POST is allowed.'
    }, status=405)
@csrf_exempt
def manageWardens(request):
    """
    View to display all wardens with their assigned hostels
    """
    wardens = Wardens.objects.select_related('user').prefetch_related('hostelwardens_set__hostel').all().order_by('-created_at')
    logger.info(f"Fetching wardens only. Total wardens retrieved: {wardens.count()}")
    logger.info(f"Request URL for manageWardens: {request.get_full_path()}")
    return render(request, "manageWardens.html", {"wardens": wardens})

def addWarden(request):
    # Check if it's an AJAX request at the beginning
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            gender = request.POST.get('gender')
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')

            if not all([name, email, phone, gender, password, confirm_password]):
                if is_ajax:
                    return JsonResponse({'status': 'error', 'message': 'All fields are required'}, status=400)
                messages.error(request, 'All fields are required')
                return redirect('manageWardens')

            if password != confirm_password:
                if is_ajax:
                    return JsonResponse({'status': 'error', 'message': 'Passwords do not match'}, status=400)
                messages.error(request, 'Passwords do not match')
                return redirect('manageWardens')

            if User.objects.filter(email=email).exists():
                if is_ajax:
                    return JsonResponse({'status': 'error', 'message': 'Email already registered'}, status=400)
                messages.error(request, 'Email already registered')
                return redirect('manageWardens')

            username = email.split('@')[0]
            if User.objects.filter(username=username).exists():
                base_username = username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1

            try:
                user = User(
                    username=username,
                    email=email,
                    first_name=name.split()[0],
                    last_name=' '.join(name.split()[1:]) if len(name.split()) > 1 else '',
                    is_staff=True
                )
                user.set_password(password)
                user.save()

                warden = Wardens(
                    user_id=user,
                    name=name,
                    contact_number=phone,
                    gender=gender,
                    created_at=timezone.now()
                )
                warden.save()

                if is_ajax:
                    return JsonResponse({
                        'status': 'success', 
                        'message': 'Warden registered successfully',
                        'warden': {
                            'id': user.id,
                            'name': warden.name,
                            'email': email,
                            'phone': phone,
                            'gender': gender
                        }
                    })
                
                messages.success(request, 'Warden registered successfully')
                return redirect('manageWardens')

            except Exception as e:
                if 'user' in locals():
                    user.delete()
                if is_ajax:
                    return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
                raise e

        except Exception as e:
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            messages.error(request, str(e))
            return redirect('manageWardens')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)
    return redirect('manageWardens')

@login_required
def wardenlist(request):
    wardens = Wardens.objects.all().order_by('-created_at')
    return render(request, "wardenlist.html", {"wardens": wardens})

@login_required
@csrf_exempt
def getAvailableHostels(request, warden_id):
    if request.method == 'GET':
        try:
            # Check if the warden already has a hostel assigned
            warden_assigned = HostelWardens.objects.filter(warden_id=warden_id).exists()
            if warden_assigned:
                return JsonResponse({
                    'status': 'success',
                    'hostels': [],
                    'warden_id': warden_id,
                    'message': 'This warden already has a hostel assigned. Only one hostel per warden is allowed.'
                })
            
            assigned_hostel_ids = HostelWardens.objects.values_list('hostel_id', flat=True)
            available_hostels = Hostels.objects.exclude(id__in=assigned_hostel_ids).filter(status='Active')
            
            hostels_data = [
                {
                    'id': hostel.id,
                    'name': hostel.name,
                    'address': hostel.address,
                    'total_floors': hostel.total_floors
                }
                for hostel in available_hostels
            ]
            
            return JsonResponse({
                'status': 'success',
                'hostels': hostels_data,
                'warden_id': warden_id
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=400)

@login_required
@csrf_exempt
def assignHostel(request):
    if request.method == 'POST':
        try:
            warden_id = request.POST.get('warden_id')
            hostel_id = request.POST.get('hostel')
            
            if not all([warden_id, hostel_id]):
                error_msg = 'Both Warden ID and Hostel ID are required'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    if not warden_id and not hostel_id:
                        return JsonResponse({'status': 'error', 'message': 'Both Warden ID and Hostel ID are required'}, status=400)
                    elif not warden_id:
                        return JsonResponse({'status': 'error', 'message': 'Warden ID is required'}, status=400)
                    elif not hostel_id:
                        return JsonResponse({'status': 'error', 'message': 'Hostel ID is required'}, status=400)
                messages.error(request, error_msg)
                return redirect('manageWardens')
            
            warden = get_object_or_404(Wardens, user_id=warden_id)
            hostel = get_object_or_404(Hostels, id=hostel_id)
            
            if HostelWardens.objects.filter(hostel=hostel).exists():
                error_msg = 'This hostel is already assigned to another warden'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': error_msg}, status=400)
                messages.error(request, error_msg)
                return redirect('manageWardens')
            
            hostel_warden = HostelWardens(
                hostel=hostel,
                warden=warden
            )
            hostel_warden.save()
            
            success_msg = f'Hostel {hostel.name} assigned to warden {warden.name} successfully'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'message': success_msg})
            messages.success(request, success_msg)
            return redirect('manageWardens')
        except Exception as e:
            error_msg = str(e)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'message': error_msg}, status=500)
            messages.error(request, error_msg)
            return redirect('manageWardens')
    return redirect('manageWardens')

@login_required
@csrf_exempt
def deleteWarden(request, warden_id):
    if request.method == 'POST':
        try:
            warden = get_object_or_404(Wardens, user_id=warden_id)
            
            # Delete any hostel assignments first
            HostelWardens.objects.filter(warden=warden).delete()
            
            # Delete the warden and associated user
            user = warden.user
            warden.delete()
            user.delete()
            
            response_data = {'status': 'success', 'message': 'Warden deleted successfully'}
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse(response_data)
            messages.success(request, response_data['message'])
            return redirect('manageWardens')
        except Exception as e:
            response_data = {'status': 'error', 'message': str(e)}
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse(response_data, status=500)
            messages.error(request, response_data['message'])
            return redirect('manageWardens')
    return redirect('manageWardens')

@login_required
def users(request):
    users = User.objects.filter(is_superuser=False).order_by('-date_joined')
    
    role = request.GET.get('role', '')
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    # Apply role filter if specified
    if role:
        if role == 'warden':
            # Filter specifically for wardens by checking if they have a Warden profile
            users = users.filter(is_staff=True, warden_profile__isnull=False)
        elif role == 'student':
            users = users.filter(is_staff=False)
        elif role == 'mess_incharge':
            users = users.filter(is_staff=True, messincharge__isnull=False)
        elif role == 'security_guard':
            users = users.filter(is_staff=True, securityguard__isnull=False)
    
    if status:
        if status == 'active':
            users = users.filter(is_active=True)
        elif status == 'inactive':
            users = users.filter(is_active=False)
    
    if search:
        users = users.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(username__icontains=search)
        )
    
    context = {
        'users': users,
        'total_users': users.count(),
        'role_filter': role,
        'status_filter': status,
        'search_query': search
    }
    
    return render(request, 'users.html', context)

@login_required
@csrf_exempt
def deleteUser(request, user_id):
    if request.method == 'POST':
        try:
            user = get_object_or_404(User, id=user_id)
            
            if user.is_superuser:
                messages.error(request, 'Cannot delete superuser accounts')
                return redirect('users')
            
            user.delete()
            messages.success(request, 'User deleted successfully')
            return redirect('users')
        except Exception as e:
            messages.error(request, str(e))
            return redirect('users')
    return redirect('users')

@login_required
@csrf_exempt
def getWarden(request, warden_id):
    """
    Get warden details by ID
    Returns JSON with warden details
    """
    logger = logging.getLogger(__name__)
    logger.info(f"getWarden called with warden_id: {warden_id}")
    
    try:
        logger.info("Trying to get warden from database...")
        # Use select_related to fetch the related user in the same query
        warden = Wardens.objects.select_related('user').get(user_id=warden_id)
        logger.info(f"Found warden: {warden.name} (User ID: {warden.user_id})")
        
        # Get assigned hostels
        logger.info("Fetching assigned hostels...")
        assigned_hostels = list(Hostels.objects.filter(
            hostelwardens__warden=warden
        ).values_list('id', flat=True))
        logger.info(f"Assigned hostels: {assigned_hostels}")
        
        # Get the user email through the related user object
        data = {
            'status': 'success',
            'warden': {
                'id': warden.user_id,  # Use user_id as the ID since it's the primary key
                'name': warden.name,
                'email': warden.user.email if hasattr(warden, 'user') else '',
                'contact_number': warden.contact_number,
                'gender': warden.gender,
                'is_active': warden.user.is_active if hasattr(warden, 'user') else False,
                'assigned_hostels': assigned_hostels
            }
        }
        logger.info("Returning warden data")
        return JsonResponse(data)
        
    except Wardens.DoesNotExist as e:
        logger.error(f"Warden not found: {e}")
        return JsonResponse({'status': 'error', 'message': 'Warden not found'}, status=404)
    except Exception as e:
        logger.error(f"Error in getWarden: {str(e)}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
@csrf_exempt
def updateWarden(request, warden_id):
    logger = logging.getLogger(__name__)
    logger.info(f"updateWarden called with warden_id: {warden_id}")
    logger.info(f"Request method: {request.method}")
    
    if request.method == 'POST':
        try:
            logger.info(f"Trying to get warden with user_id: {warden_id}")
            warden = Wardens.objects.select_related('user').get(user_id=warden_id)
            logger.info(f"Found warden: {warden.name} (User ID: {warden.user_id})")
            
            # Log all POST data for debugging
            logger.info(f"POST data: {request.POST}")
            
            # Get form data
            name = request.POST.get('name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            gender = request.POST.get('gender')
            is_active = request.POST.get('is_active') == 'on'
            
            logger.info(f"Updating warden with - Name: {name}, Email: {email}, Phone: {phone}, Gender: {gender}, Active: {is_active}")
            
            # Update warden fields
            warden.name = name
            warden.contact_number = phone
            warden.gender = gender
            
            # Update user fields if user exists
            if hasattr(warden, 'user') and warden.user:
                user = warden.user
                user.email = email
                user.is_active = is_active
                
                # Handle password update if provided
                password = request.POST.get('password')
                if password and password.strip() != '':
                    logger.info("Updating password")
                    user.set_password(password)
                
                user.save()
                logger.info("User updated successfully")
            
            warden.save()
            logger.info("Warden updated successfully")
            
            # Update assigned hostels
            if 'hostels' in request.POST:
                # Get selected hostels
                hostel_ids = request.POST.getlist('hostels')
                logger.info(f"Updating assigned hostels: {hostel_ids}")
                
                # Remove existing assignments
                deleted_count, _ = HostelWardens.objects.filter(warden=warden).delete()
                logger.info(f"Deleted {deleted_count} existing hostel assignments")
                
                # Add new assignments
                for hostel_id in hostel_ids:
                    try:
                        hostel = Hostels.objects.get(id=hostel_id)
                        HostelWardens.objects.create(warden=warden, hostel=hostel)
                        logger.info(f"Assigned hostel ID {hostel_id} to warden")
                    except Hostels.DoesNotExist:
                        logger.warning(f"Hostel with ID {hostel_id} not found")
                        continue
            
            logger.info("Warden update completed successfully")
            return JsonResponse({
                'status': 'success', 
                'message': 'Warden updated successfully',
                'redirect_url': reverse('manageWardens')
            })
            
        except Wardens.DoesNotExist as e:
            logger.error(f"Warden not found: {e}")
            return JsonResponse({
                'status': 'error', 
                'message': 'Warden not found'
            }, status=404)
            
        except Exception as e:
            logger.error(f"Error updating warden: {str(e)}", exc_info=True)
            return JsonResponse({
                'status': 'error', 
                'message': f'Failed to update warden: {str(e)}'
            }, status=500)
            
    else:
        logger.warning("Invalid request method")
        return JsonResponse({
            'status': 'error', 
            'message': 'Invalid request method'
        }, status=405)

@login_required
@csrf_exempt
def removeWardenFromHostel(request, hostel_id):
    """
    Remove a warden assignment from a specific hostel.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"removeWardenFromHostel called with hostel_id: {hostel_id}")
    logger.info(f"Request method: {request.method}")
    
    if request.method == 'POST':
        try:
            logger.info(f"Trying to get hostel with id: {hostel_id}")
            hostel = Hostels.objects.get(id=hostel_id)
            logger.info(f"Found hostel: {hostel.name} (ID: {hostel.id})")
            
            logger.info(f"Attempting to remove warden assignment from hostel: {hostel.name}")
            assignment = HostelWardens.objects.filter(hostel=hostel).first()
            
            if assignment:
                warden_name = assignment.warden.name if assignment.warden else "Unknown Warden"
                assignment.delete()
                logger.info(f"Removed warden assignment from hostel: {hostel.name}")
                
                return JsonResponse({
                    'status': 'success',
                    'message': f'Warden {warden_name} has been removed from {hostel.name} successfully.',
                    'redirect_url': reverse('hostels')
                })
            else:
                logger.warning(f"No warden assignment found for hostel: {hostel.name}")
                return JsonResponse({
                    'status': 'error',
                    'message': f'No warden assignment found for {hostel.name}.'
                }, status=404)
                
        except Hostels.DoesNotExist as e:
            logger.error(f"Hostel not found: {e}")
            return JsonResponse({
                'status': 'error',
                'message': 'Hostel not found.'
            }, status=404)
            
        except Exception as e:
            logger.error(f"Error removing warden from hostel: {str(e)}", exc_info=True)
            return JsonResponse({
                'status': 'error',
                'message': f'Failed to remove warden from hostel: {str(e)}'
            }, status=500)
            
    else:
        logger.warning("Invalid request method")
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid request method. Use POST to remove a warden assignment.'
        }, status=405)

@login_required
@csrf_exempt
def update_user(request, user_id):
    if request.method == 'POST':
        try:
            user = get_object_or_404(User, id=user_id)
            
            if user.is_superuser:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Cannot update superuser accounts'
                }, status=403)
            
            name = request.POST.get('name')
            email = request.POST.get('email')
            role = request.GET.get('role')
            is_active = request.POST.get('is_active') == 'true'
            
            user.first_name = name.split()[0]
            user.last_name = ' '.join(name.split()[1:]) if len(name.split()) > 1 else ''
            user.email = email
            user.is_active = is_active
            
            if role == 'warden':
                user.is_staff = True
            else:
                user.is_staff = False
                
            user.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'User updated successfully'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=400)

@csrf_exempt
def toggle_user_status(request, user_id):
    """
    Toggle the active status of a user.
    Expects a POST request with JSON body: {'is_active': true/false}
    """
    if request.method == 'POST':
        try:
            # Parse JSON data from request body
            data = json.loads(request.body)
            is_active = data.get('is_active')
            
            if is_active is None:
                return JsonResponse(
                    {'status': 'error', 'message': 'Missing is_active parameter'},
                    status=400
                )
            
            # Get the user
            user = User.objects.get(id=user_id)
            
            # Prevent modifying superusers
            if user.is_superuser:
                return JsonResponse(
                    {'status': 'error', 'message': 'Cannot modify superuser status'},
                    status=403
                )
            
            # Update the user's status
            user.is_active = is_active
            user.save()
            
            status_text = 'activated' if is_active else 'deactivated'
            return JsonResponse({
                'status': 'success',
                'message': f'User {status_text} successfully',
                'is_active': user.is_active
            })
            
        except User.DoesNotExist:
            return JsonResponse(
                {'status': 'error', 'message': 'User not found'},
                status=404
            )
        except json.JSONDecodeError:
            return JsonResponse(
                {'status': 'error', 'message': 'Invalid JSON data'},
                status=400
            )
        except Exception as e:
            return JsonResponse(
                {'status': 'error', 'message': str(e)},
                status=400
            )
    
    return JsonResponse(
        {'status': 'error', 'message': 'Only POST method is allowed'},
        status=405
    )

@login_required
@csrf_exempt
def toggle_hostel_status(request, id):
    """
    Toggle the status of a hostel.
    Simply toggles the current status on a POST request.
    """
    if request.method == 'POST':
        try:
            # Get the hostel
            hostel = Hostels.objects.get(id=id)
            
            # Toggle the hostel's status
            hostel.status = 'Inactive' if hostel.status == 'Active' else 'Active'
            hostel.save()
            
            status_text = 'activated' if hostel.status == 'Active' else 'deactivated'
            return JsonResponse({
                'status': 'success',
                'message': f'Hostel {status_text} successfully',
                'is_active': hostel.status
            })
            
        except Hostels.DoesNotExist:
            return JsonResponse(
                {'status': 'error', 'message': 'Hostel not found'},
                status=404
            )
        except Exception as e:
            return JsonResponse(
                {'status': 'error', 'message': str(e)},
                status=500
            )
    
    return JsonResponse(
        {'status': 'error', 'message': 'Only POST method is allowed'},
        status=405
    )

@login_required
def profile(request):
    user = request.user
    
    if request.method == 'POST':
        try:
            # Handle form data (can be JSON or form-data)
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST.dict()
            
            # Debug: Log received data
            print("Received data:", data)
                
            # Update basic user info
            if 'name' in data and data['name']:
                name_parts = data['name'].strip().split(' ', 1)
                user.first_name = name_parts[0]
                user.last_name = name_parts[1] if len(name_parts) > 1 else ''
            
            if 'email' in data and data['email']:
                user.email = data['email'].strip()
            
            # Save user changes
            user.save()
            
            # Handle Student profile if it exists
            student_profile = None
            if hasattr(user, 'student'):
                student_profile = user.student
                if 'phone' in data:
                    student_profile.contact_number = data.get('phone', '').strip()
                if 'address' in data:
                    student_profile.address = data.get('address', '').strip()
                student_profile.save()
            
            # Prepare response data
            response_data = {
                'status': 'success',
                'message': 'Profile updated successfully',
                'user': {
                    'name': user.get_full_name(),
                    'email': user.email,
                    'username': user.username,
                    'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None,
                    'date_joined': user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
                    'is_staff': user.is_staff,
                    'is_active': user.is_active,
                    'phone': student_profile.contact_number if student_profile else '',
                    'address': student_profile.address if student_profile else '',
                    'profile_picture': None  # No profile picture in the current model
                }
            }
            
            # Return JSON response for AJAX requests
            return JsonResponse(response_data)
            
        except Exception as e:
            error_msg = str(e)
            print(f"Error updating profile: {error_msg}")
            return JsonResponse(
                {'status': 'error', 'message': f'Failed to update profile: {error_msg}'}, 
                status=400
            )
    
    # GET request - show profile
    student_profile = None
    if hasattr(user, 'student'):
        student_profile = user.student
    
    user_data = {
        'name': user.get_full_name(),
        'email': user.email,
        'username': user.username,
        'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else 'Never',
        'date_joined': user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
        'is_staff': user.is_staff,
        'is_active': user.is_active,
        'is_superuser': user.is_superuser,
        'phone': student_profile.contact_number if student_profile else '',
        'address': student_profile.address if student_profile else '',
        'profile_picture': None  # No profile picture in the current model
    }
    
    # If it's an AJAX request, return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'user_data': user_data})
        
    # Otherwise, render the template
    return render(request, 'profile.html', {'user_data': user_data})

@login_required
def manage_booking(request):
    if is_student(request.user):
        # For students, show only their bookings
        bookings = BookingRequest.objects.filter(student=request.user.student).select_related('student', 'hostel')
    else:
        # For admins, show all bookings
        bookings = BookingRequest.objects.all().select_related('student', 'hostel')
    
    # Apply filters from GET parameters
    status_filter = request.GET.get('status', '')
    hostel_filter = request.GET.get('hostel', '')
    search_query = request.GET.get('search', '')
    
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    if hostel_filter:
        bookings = bookings.filter(hostel_id=hostel_filter)
    if search_query:
        bookings = bookings.filter(
            Q(student__first_name__icontains=search_query) |
            Q(student__last_name__icontains=search_query) |
            Q(student__email__icontains=search_query)
        )
    
    # Add status counts for summary
    status_counts = bookings.values('status').annotate(count=Count('status'))
    
    # Get all hostels with their room types and rates
    hostels_queryset = Hostels.objects.prefetch_related(
        Prefetch('roomtyperate_set', 
                queryset=RoomTypeRate.objects.all().only('room_type', 'per_head_rent'),
                to_attr='room_types')
    ).all()
    
    # Prepare hostels data with room types for JavaScript
    hostels_data = []
    for hostel in hostels_queryset:
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
        'hostels': hostels_queryset,  # Pass the QuerySet for template iteration
        'hostels_json': hostels_json,  # Pass the JSON string for JavaScript
        'today': date.today(),    # For setting min date on date picker
        'status_filter': status_filter,
        'hostel_filter': hostel_filter,
        'search_query': search_query
    }
    return render(request, 'manageBookings.html', context)

@login_required
def create_booking(request):
    logger.info(f"Processing booking request. Method: {request.method}")
    
    is_staff = request.user.is_staff or hasattr(request.user, 'warden')
    
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid request method'
        }, status=405)
    
    logger.debug(f"POST data: {request.POST}")
    
    try:
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
                from .models import BookingRequest
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
                from .models import RoomAssignment
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
            from .models import BookingRequest
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
            from .models import RoomAssignment
            active_assignment = RoomAssignment.objects.filter(
                booking__student=student.user,
                is_active=True
            ).select_related('room').first()
            
            if active_assignment:
                return JsonResponse({
                    'status': 'error',
                    'message': f'You already have an active room assignment in room {active_assignment.room.room_number}.'
                }, status=400)
        
        logger.debug(f"Form data with student: {form_data}")
        
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
            return redirect('manage_booking')
        
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
                from .models import RoomAssignment
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
                booking.save()
                
                logger.info(f"Booking {booking.id} created successfully for student {booking.student.username}")
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Booking created successfully!',
                        'booking_id': booking.id
                    })
                
                messages.success(request, 'Booking request has been submitted successfully!')
                return redirect('manage_booking')
                
        except Exception as e:
            logger.exception("Error saving booking:")
            error_message = str(e) or 'An error occurred while saving the booking. Please try again or contact support.'
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': error_message
                }, status=400)
            
            messages.error(request, error_message)
            return redirect('manage_booking')
            
    except Exception as e:
        logger.exception("Unexpected error in create_booking:")
        error_message = 'An unexpected error occurred. Please try again or contact support.'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': error_message
            }, status=500)
        
        messages.error(request, error_message)
        return redirect('manage_booking')
    
    # If we get here, it's a GET request or form was invalid
    initial_data = {}
    if hasattr(request.user, 'student') and not is_staff:
        initial_data['student'] = request.user.student
        
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
    
    return render(request, 'create_booking.html', {
        'form': form,
        'hostels': hostels,  # Pass QuerySet for template
        'hostels_json': hostels_json,  # Pass JSON for JavaScript
        'is_staff': is_staff,
        'min_date': timezone.now().strftime('%Y-%m-%d'),
        'default_check_out': (timezone.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    })

@login_required
@user_passes_test(lambda u: u.is_staff, login_url='login')
@require_http_methods(["GET"])
def get_available_rooms(request, booking_id):
    """
    Get available rooms for a booking request
    """
    response_data = {
        'status': 'error',
        'message': 'An unexpected error occurred',
        'debug': {}
    }
    
    try:
        # Debug logging
        logger.info(f"Fetching available rooms for booking ID: {booking_id}")
        
        # Get the booking
        try:
            booking = BookingRequest.objects.select_related('hostel').get(id=booking_id)
            response_data['debug']['booking_found'] = True
            response_data['debug']['booking_id'] = booking.id
            response_data['debug']['hostel_id'] = booking.hostel.id if booking.hostel else None
            response_data['debug']['room_type'] = booking.room_type
            
        except BookingRequest.DoesNotExist:
            error_msg = f"Booking with ID {booking_id} not found"
            logger.error(error_msg)
            response_data.update({
                'message': 'Booking not found.',
                'debug': {'error': error_msg}
            })
            return JsonResponse(response_data, status=404)
        except Exception as e:
            error_msg = f"Error getting booking: {str(e)}"
            logger.error(error_msg, exc_info=True)
            response_data.update({
                'message': 'Error retrieving booking details.',
                'debug': {'error': error_msg}
            })
            return JsonResponse(response_data, status=500)
            
        logger.info(f"Found booking: {booking.id} for hostel: {booking.hostel.name}")
        
        try:
            # Get all available rooms of the requested type in the selected hostel
            # First, get rooms with capacity > current_occupants
            available_rooms = Rooms.objects.filter(
                hostel_id=booking.hostel.id,
                room_type=booking.room_type,
                status='Available'
            ).annotate(
                available_beds_annotated=F('capacity') - F('current_occupants')
            ).filter(
                available_beds_annotated__gt=0
            ).order_by('floor_number', 'room_number')
            
            room_count = available_rooms.count()
            logger.info(f"Found {room_count} available rooms")
            response_data['debug']['rooms_found'] = room_count
            
            # Prepare room data for JSON response
            rooms_data = [
                {
                    'id': room.id,
                    'room_number': room.room_number,
                    'floor_number': room.floor_number,
                    'capacity': room.capacity,
                    'current_occupants': room.current_occupants,
                    'available_beds': room.available_beds_annotated,
                    'rent': str(room.rent) if room.rent else '0.00',
                    'per_head_rent': str(float(room.rent) / room.capacity if room.rent and room.capacity > 0 else 0.00)
                }
                for room in available_rooms
            ]
            
            response_data.update({
                'status': 'success',
                'message': f'Found {room_count} available rooms',
                'hostel_name': booking.hostel.name,
                'requested_room_type': booking.room_type,
                'available_rooms': rooms_data
            })
            
            return JsonResponse(response_data)
            
        except Exception as e:
            error_msg = f"Error processing room data: {str(e)}"
            logger.error(error_msg, exc_info=True)
            response_data.update({
                'message': 'Error processing room data',
                'debug': {'error': error_msg}
            })
            return JsonResponse(response_data, status=500)
            
    except Exception as e:
        error_msg = f"Unexpected error in get_available_rooms: {str(e)}"
        logger.error(error_msg, exc_info=True)
        response_data.update({
            'message': 'An unexpected error occurred',
            'debug': {'error': error_msg}
        })
        return JsonResponse(response_data, status=500)

@login_required
@user_passes_test(lambda u: u.is_staff, login_url='login')
def approve_booking(request, booking_id):
    logger.info(f"approve_booking called with booking_id={booking_id}, method={request.method}")
    
    if request.method == 'POST':
        try:
            logger.info(f"Request POST data: {request.POST}")
            
            # Get the booking
            try:
                booking = BookingRequest.objects.select_related('hostel', 'student').get(id=booking_id)
                logger.info(f"Found booking: {booking.id}, status={booking.status}, hostel={booking.hostel}")
            except BookingRequest.DoesNotExist:
                logger.error(f"Booking not found: {booking_id}")
                messages.error(request, 'Booking not found.')
                return JsonResponse({
                    'status': 'error',
                    'message': 'Booking not found.'
                }, status=404)
            
            room_id = request.POST.get('room_id')
            admin_notes = request.POST.get('admin_notes', '')
            security_deposit_amount = request.POST.get('security_deposit_amount', '')
            payment_method = request.POST.get('payment_method', '')
            transaction_id = request.POST.get('transaction_id', '')
            staff_name = request.POST.get('staff_name', '')
            
            logger.info(f"Room ID from form: {room_id}, Admin notes: {admin_notes}")
            logger.info(f"Security Deposit Amount: {security_deposit_amount}, Payment Method: {payment_method}, Transaction ID: {transaction_id}, Staff Name: {staff_name}")
            
            if not room_id:
                logger.warning("No room_id provided in request")
                messages.error(request, 'Please select a room to assign.')
                return JsonResponse({
                    'status': 'error',
                    'message': 'Please select a room to assign.'
                }, status=400)
            
            if not security_deposit_amount or not payment_method:
                logger.warning("Security deposit details incomplete")
                messages.error(request, 'Please provide complete security deposit details.')
                return JsonResponse({
                    'status': 'error',
                    'message': 'Please provide complete security deposit details.'
                }, status=400)
            
            # Get the room with detailed error checking
            try:
                room = Rooms.objects.get(id=room_id)
                if room.hostel_id != booking.hostel.id:
                    logger.error(f"Room {room_id} found but hostel mismatch: expected {booking.hostel.id}, got {room.hostel_id}")
                    messages.error(request, f'Selected room {room_id} does not belong to the booked hostel {booking.hostel.name}.')
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Selected room does not belong to the booked hostel {booking.hostel.name}.',
                        'debug': {
                            'room_id': room_id,
                            'expected_hostel_id': booking.hostel.id,
                            'actual_hostel_id': room.hostel_id,
                            'room_type': room.room_type
                        }
                    }, status=400)
                if room.room_type != booking.room_type:
                    logger.error(f"Room {room_id} found but room type mismatch: expected {booking.room_type}, got {room.room_type}")
                    messages.error(request, f'Selected room {room_id} is of type {room.room_type}, but booking requires {booking.room_type}.')
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Selected room is of type {room.room_type}, but booking requires {booking.room_type}.',
                        'debug': {
                            'room_id': room_id,
                            'hostel_id': booking.hostel.id,
                            'expected_room_type': booking.room_type,
                            'actual_room_type': room.room_type
                        }
                    }, status=400)
                logger.info(f"Found room: {room.id}, type={room.room_type}, capacity={room.capacity}, current_occupants={room.current_occupants}")
            except Rooms.DoesNotExist:
                logger.error(f"Room not found: id={room_id}")
                messages.error(request, f'Selected room ID {room_id} does not exist in the system.')
                return JsonResponse({
                    'status': 'error',
                    'message': f'Selected room ID {room_id} does not exist in the system.',
                    'debug': {
                        'room_id': room_id,
                        'hostel_id': booking.hostel.id,
                        'room_type': booking.room_type
                    }
                }, status=404)
            
            # Check if room has available beds
            if room.current_occupants >= room.capacity:
                logger.warning(f"Room {room.id} is full: {room.current_occupants}/{room.capacity}")
                messages.error(request, 'Selected room is already full. Please choose another room.')
                return JsonResponse({
                    'status': 'error',
                    'message': 'Selected room is already full. Please choose another room.'
                }, status=400)
            
            logger.info("Starting transaction to update booking and room")
            
            try:
                # Update booking status, assign room, and record security deposit
                with transaction.atomic():
                    try:
                        # First, update the booking
                        booking.status = 'Approved'
                        booking.assigned_room = room
                        booking.admin_notes = admin_notes
                        # Set monthly_rent to per head rent for the room type
                        try:
                            rate = RoomTypeRate.objects.get(hostel_id=booking.hostel.id, room_type=booking.room_type)
                            booking.monthly_rent = rate.per_head_rent
                        except RoomTypeRate.DoesNotExist:
                            logger.warning(f"No rate found for hostel {booking.hostel.id}, room type {booking.room_type}")
                            booking.monthly_rent = room.rent / room.capacity if room.rent and room.capacity > 0 else 0.0
                        booking.save()
                        logger.info(f"Updated booking {booking.id} to Approved with room {room.id} and monthly rent {booking.monthly_rent}")
                        
                        # Create room assignment record
                        RoomAssignment.objects.create(
                            booking=booking,
                            room=room,
                            check_in_date=timezone.now().date(),
                            is_active=True,
                            assigned_by=request.user,
                            notes=f"Booking approved by {request.user.get_full_name() or request.user.username}"
                        )
                        logger.info(f"Created RoomAssignment for booking {booking.id} in room {room.id}")
                        
                        # Record security deposit
                        from .models import SecurityDeposit
                        security_deposit = SecurityDeposit(
                            booking=booking,
                            amount=float(security_deposit_amount),
                            payment_method=payment_method,
                            transaction_id=transaction_id if transaction_id else None,
                            notes=f"Security deposit recorded during booking approval by {request.user.get_full_name() or request.user.username}",
                            received_by=request.user,
                            is_verified=True
                        )
                        if payment_method == 'Cash' and staff_name:
                            security_deposit.notes += f"\nReceived by: {staff_name}"
                        security_deposit.save()
                        logger.info(f"Recorded security deposit for booking {booking.id}")
                        
                        # Then update room occupancy using F() expression to avoid race conditions
                        updated = Rooms.objects.filter(
                            id=room.id,
                            current_occupants__lt=F('capacity')  # Only update if not full
                        ).update(
                            current_occupants=F('current_occupants') + 1
                        )
                        
                        if updated == 0:
                            logger.warning(f"Room {room.id} became full before we could update it")
                            raise Exception('Room is now full. Please select another room.')
                            
                        # Update room status if needed
                        room.refresh_from_db()
                        if room.current_occupants >= room.capacity:
                            room.status = 'Occupied'
                            room.save(update_fields=['status'])
                            
                        logger.info(f"Updated room {room.id} occupancy")
                        
                    except Exception as e:
                        logger.exception(f"Error in transaction: {str(e)}")
                        raise  # Re-raise to be caught by outer try-except
                
                # Refresh data to get updated values
                room.refresh_from_db()
                logger.info(f"Room {room.id} after update - occupants: {room.current_occupants}, status: {room.status}")
                
                messages.success(request, f'Booking #{booking.id} has been approved and room {room.room_number} has been assigned.')
                logger.info(f"Successfully approved booking {booking.id}")
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Booking approved successfully.',
                    'redirect_url': '/manage_booking/'
                })
                
            except Exception as e:
                error_msg = str(e)
                logger.exception(f"Database error during booking approval: {error_msg}")
                
                # Provide more specific error messages based on the exception
                if 'room' in error_msg.lower() and 'full' in error_msg.lower():
                    user_msg = 'The selected room is now full. Please choose another room.'
                else:
                    user_msg = f'A database error occurred: {error_msg}'
                
                messages.error(request, user_msg)
                return JsonResponse({
                    'status': 'error',
                    'message': user_msg
                }, status=500)
            
        except Exception as e:
            logger.exception(f"Unexpected error in approve_booking: {str(e)}")
            messages.error(request, f'An unexpected error occurred: {str(e)}')
            return JsonResponse({
                'status': 'error',
                'message': f'An unexpected error occurred: {str(e)}'
            }, status=500)
    
    # For GET requests, return the available rooms
    try:
        booking = BookingRequest.objects.get(id=booking_id)
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid request method. Use POST to approve a booking.'
        }, status=405)
    except BookingRequest.DoesNotExist:
        messages.error(request, 'Booking not found.')
        return JsonResponse({
            'status': 'error',
            'message': 'Booking not found.'
        }, status=404)





@login_required
@user_passes_test(lambda u: u.is_staff, login_url='login')
def reject_booking(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(BookingRequest, id=booking_id)
        booking.status = 'Rejected'
        booking.admin_notes = request.POST.get('rejection_reason', '')
        booking.save()
        messages.warning(request, f'Booking #{booking.id} has been rejected.')
    return redirect('manage_booking')

@login_required
def cancel_booking(request, booking_id):
    """
    Cancel a booking. Only the student who made the booking or an admin can cancel.
    """
    if request.method == 'POST':
        booking = get_object_or_404(BookingRequest, id=booking_id)
        # Only allow the student who made the booking or an admin to cancel
        if request.user.student == booking.student or request.user.is_staff:
            try:
                with transaction.atomic():
                    booking.status = 'Cancelled'
                    booking.admin_notes = (
                        f"Booking cancelled by {request.user.username} "
                        f"on {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        f"\n{request.POST.get('admin_notes', '')}"
                    )
                    booking.save()
                    
                    messages.success(request, f'Booking #{booking.id} has been cancelled successfully.')
                    
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': True,
                            'message': 'Booking has been cancelled successfully.'
                        })
                        
            except Exception as e:
                error_msg = f'Error cancelling booking: {str(e)}'
                logger.error(error_msg)
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': 'An error occurred while cancelling the booking.'
                    }, status=500)
                    
                messages.error(request, 'An error occurred while cancelling the booking.')
        else:
            error_msg = 'You are not authorized to cancel this booking.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': error_msg
                }, status=403)
                
            messages.error(request, error_msg)
    
    return redirect('manage_booking')

def check_availability(request):
    if request.method == 'GET':
        hostel_id = request.GET.get('hostel_id')
        check_in = request.GET.get('check_in')
        check_out = request.GET.get('check_out')
        
        try:
            # Convert string dates to date objects
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
            
            # Get all room types for the hostel
            room_types = RoomTypeRate.objects.filter(hostel_id=hostel_id)
            
            availability = []
            for room_type in room_types:
                # Count total rooms of this type
                total_rooms = Rooms.objects.filter(
                    hostel_id=hostel_id,
                    room_type=room_type.room_type
                ).count()
                
                # Count booked rooms for the selected dates
                booked_rooms = BookingRequest.objects.filter(
                    hostel_id=hostel_id,
                    room_type=room_type.room_type,
                    status='Approved',
                    check_in_date__lt=check_out_date,
                    check_out_date__gt=check_in_date
                ).count()
                
                available_rooms = total_rooms - booked_rooms
                
                if available_rooms > 0:
                    availability.append({
                        'room_type': room_type.room_type,
                        'available': available_rooms,
                        'rate': float(room_type.per_head_rent),
                        'total_rooms': total_rooms
                    })
            
            return JsonResponse({'status': 'success', 'availability': availability})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def search_students(request):
    try:
        logger.info(f"Search request: {request.GET}")
        
        if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
            logger.warning("Non-AJAX request received")
            return JsonResponse({'error': 'Invalid request'}, status=400)
        
        query = request.GET.get('q', '').strip()
        if not query or len(query) < 3:
            logger.warning(f"Search query too short: '{query}'")
            return JsonResponse({'error': 'Search query too short'}, status=400)
        
        logger.info(f"Searching for: {query}")
        
        from django.contrib.auth import get_user_model
        from .models import Student
        
        User = get_user_model()
        
        student_matches = Student.objects.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(cnic__icontains=query)
        ).select_related('user')[:10]
        
        logger.info(f"Found {len(student_matches)} matching students")
        
        results = []
        for student in student_matches:
            try:
                user = student.user
                results.append({
                    'id': student.id,
                    'user_id': user.id,  # Include user ID for the form
                    'full_name': f"{user.first_name or ''} {user.last_name or ''}".strip(),
                    'email': user.email or '',
                    'cnic': student.cnic or '',
                    'phone': student.contact_number or ''
                })
            except Exception as e:
                logger.error(f"Error formatting student {student.id}: {str(e)}")
                continue
        
        if not results:
            logger.info("No results from Student model, trying User model")
            user_matches = User.objects.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query)
            )[:10]
            
            for user in user_matches:
                try:
                    results.append({
                        'id': user.id,
                        'user_id': user.id,  # Same as id for direct user matches
                        'full_name': f"{user.first_name or ''} {user.last_name or ''}".strip(),
                        'email': user.email or '',
                        'cnic': '',
                        'phone': ''
                    })
                except Exception as e:
                    logger.error(f"Error formatting user {user.id}: {str(e)}")
                    continue
        
        logger.info(f"Returning {len(results)} results")
        return JsonResponse({
            'students': results,
            'query': query
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error in search_students: {str(e)}\n{error_details}")
        return JsonResponse({
            'error': 'An error occurred while searching',
            'details': str(e),
            'traceback': error_details.split('\n')
        }, status=500)

@login_required
def get_room_types(request):
    if request.method == 'GET' and 'hostel_id' in request.GET:
        try:
            hostel_id = request.GET.get('hostel_id')
            room_types = RoomTypeRate.objects.filter(
                hostel_id=hostel_id
            ).values('id', 'room_type', 'per_head_rent')
            
            return JsonResponse({
                'status': 'success',
                'room_types': list(room_types)
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required
@require_http_methods(["GET"])
def test_url(request, booking_id):
    """Test URL endpoint to verify routing is working"""
    return JsonResponse({
        'status': 'success',
        'message': 'Test endpoint is working!',
        'booking_id': booking_id,
        'request_path': request.path,
        'request_method': request.method
    })

def get_booking_details(request, booking_id):
    """
    Get booking details by ID
    Returns JSON with booking details including student and hostel information
    """
    print(f"\n=== DEBUG: get_booking_details called with booking_id: {booking_id} ===")
    print(f"Request path: {request.path}")
    print(f"Request method: {request.method}")
    print(f"Request headers: {request.headers}")
    
    try:
        booking = get_object_or_404(BookingRequest, id=booking_id)
        
        # Prepare booking data
        booking_data = {
            'id': booking.id,
            'student': {
                'id': booking.student.id,
                'user': {
                    'id': booking.student.user.id,
                    'username': booking.student.user.username,
                    'email': booking.student.user.email,
                    'first_name': booking.student.user.first_name,
                    'last_name': booking.student.user.last_name,
                    'get_full_name': booking.student.user.get_full_name(),
                    'phone': booking.student.user.phone if hasattr(booking.student.user, 'phone') else ''
                },
                'cnic': booking.student.cnic,
                'phone': booking.student.phone_number
            },
            'hostel': {
                'id': booking.hostel.id,
                'name': booking.hostel.name,
                'address': booking.hostel.address
            },
            'room_type': booking.room_type,
            'checkin_date': booking.checkin_date.isoformat() if booking.checkin_date else None,
            'checkout_date': booking.checkout_date.isoformat() if booking.checkout_date else None,
            'status': booking.status,
            'total_amount': float(booking.total_amount) if booking.total_amount else 0.0,
            'security_deposit': float(booking.security_deposit) if booking.security_deposit else 0.0,
            'monthly_rent': float(booking.monthly_rent) if booking.monthly_rent else 0.0,
            'duration_months': booking.duration_months,
            'created_at': booking.request_date.isoformat(),
        }
        
        return JsonResponse({
            'status': 'success',
            'booking': booking_data
        })
        
    except Exception as e:
        logger.error(f'Error getting booking details: {str(e)}')
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to load booking details'
        }, status=500)


def get_hostels(request):
    try:
        hostels = Hostels.objects.prefetch_related('roomtyperate_set').all()
        hostels_data = []
        
        for hostel in hostels:
            hostel_data = {
                'id': hostel.id,
                'name': hostel.name,
                'room_types': [
                    {
                        'room_type': rt.room_type,
                        'per_head_rent': float(rt.per_head_rent) if rt.per_head_rent else 0.0
                    } for rt in hostel.roomtyperate_set.all()
                ]
            }
            hostels_data.append(hostel_data)
            
        return JsonResponse(hostels_data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def mess_menu(request):
    """
    View to display mess menu for all hostels from the MessMenu model with search and hostel filter functionality.
    """
    from messincharge.models import MessMenu
    from coustom_admin.models import Hostels
    
    # Get all hostels
    hostels = Hostels.objects.all().order_by('name')
    
    # Apply search filter if provided
    search_query = request.GET.get('search', '')
    if search_query:
        hostels = hostels.filter(name__icontains=search_query)
    
    # Get selected hostel if provided
    selected_hostel = None
    hostel_id = request.GET.get('hostel', '')
    if hostel_id:
        try:
            selected_hostel = Hostels.objects.get(id=hostel_id)
        except Hostels.DoesNotExist:
            selected_hostel = None
    
    # Get all mess menu data for the hostels
    hostel_menus = MessMenu.objects.filter(hostel_id__in=hostels).select_related('hostel_id')
    
    # Define days of the week for the template
    days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    # Structure menu data for easy access in template
    menu_data = {}
    for hostel in hostels:
        menu_data[hostel.id] = {}
        for day in days_of_week:
            menu_data[hostel.id][day] = {
                'Breakfast': None,
                'Lunch': None,
                'Dinner': None
            }
    
    for menu in hostel_menus:
        if menu.hostel_id.id in menu_data:
            if menu.day_of_week in menu_data[menu.hostel_id.id]:
                menu_data[menu.hostel_id.id][menu.day_of_week][menu.meal_type] = menu
    
    context = {
        'hostels': hostels,
        'selected_hostel': selected_hostel,
        'menu_data': menu_data,
        'days_of_week': days_of_week,
        'search_query': search_query,
    }
    
    return render(request, "mess_menu.html", context)

@login_required
def manage_mess_incharge(request):
    """
    View to display all mess incharge with their assigned hostels
    """
    mess_incharges = MessIncharge.objects.select_related('user', 'hostel').all().order_by('-created_at')
    hostels = Hostels.objects.all()
    return render(request, "manageMessIncharge.html", {"mess_incharges": mess_incharges, "hostels": hostels})

@login_required
@csrf_exempt
def add_mess_incharge(request):
    if request.method == 'POST':
        form = MessInchargeForm(request.POST)
        if form.is_valid():
            try:
                name = form.cleaned_data['name']
                email = request.POST.get('email')
                password = form.cleaned_data.get('password')
                
                if User.objects.filter(email=email).exists():
                    messages.error(request, 'Email already registered')
                    return redirect('add_mess_incharge')

                username = email.split('@')[0]
                if User.objects.filter(username=username).exists():
                    base_username = username
                    counter = 1
                    while User.objects.filter(username=username).exists():
                        username = f"{base_username}{counter}"
                        counter += 1

                user = User(
                    username=username,
                    email=email,
                    first_name=name.split()[0],
                    last_name=' '.join(name.split()[1:]) if len(name.split()) > 1 else '',
                    is_staff=True
                )
                if password:
                    user.set_password(password)
                user.save()

                mess_incharge = form.save(commit=False)
                mess_incharge.user = user
                mess_incharge.created_at = timezone.now()
                mess_incharge.save()

                # Ensure no Wardens object is created for this user
                from coustom_admin.models import Wardens
                if Wardens.objects.filter(user=user).exists():
                    Wardens.objects.filter(user=user).delete()

                messages.success(request, 'Mess Incharge registered successfully')
                return redirect('manage_mess_incharge')
            except Exception as e:
                if 'user' in locals():
                    user.delete()
                messages.error(request, f'Error registering Mess Incharge: {str(e)}')
                return redirect('add_mess_incharge')
        else:
            messages.error(request, 'Form validation failed. Please correct the errors below.')
            return redirect('add_mess_incharge')
    
    form = MessInchargeForm()
    # Filter hostels to show only active ones without an assigned Mess Incharge
    filtered_hostels = Hostels.objects.filter(status='Active').exclude(mess_incharges__isnull=False)
    form.fields['hostel'].queryset = filtered_hostels
    return render(request, "add_mess_incharge.html", {"form": form, "hostels": filtered_hostels})

@login_required
@csrf_exempt
def edit_mess_incharge(request, mess_incharge_id):
    mess_incharge = get_object_or_404(MessIncharge, user_id=mess_incharge_id)
    if request.method == 'POST':
        form = MessInchargeForm(request.POST, instance=mess_incharge)
        if form.is_valid():
            try:
                email = request.POST.get('email')
                password = form.cleaned_data.get('password')
                is_active = request.POST.get('is_active') == 'on'

                if hasattr(mess_incharge, 'user') and mess_incharge.user:
                    user = mess_incharge.user
                    user.email = email
                    user.is_active = is_active
                    if password:
                        user.set_password(password)
                    user.save()

                form.save()
                messages.success(request, 'Mess Incharge updated successfully')
                return redirect('manage_mess_incharge')
            except Exception as e:
                messages.error(request, f'Failed to update Mess Incharge: {str(e)}')
                return redirect('manage_mess_incharge')
        else:
            messages.error(request, 'Form validation failed. Please correct the errors below.')
    else:
        form = MessInchargeForm(instance=mess_incharge)
        # Filter hostels to show only active ones without an assigned Mess Incharge, or the currently assigned hostel
        filtered_hostels = Hostels.objects.filter(
            status='Active'
        ).filter(
            Q(mess_incharges__isnull=True) | Q(mess_incharges=mess_incharge)
        )
        form.fields['hostel'].queryset = filtered_hostels
        return render(request, "edit_mess_incharge.html", {"form": form, "mess_incharge": mess_incharge, "hostels": filtered_hostels})

@login_required
@csrf_exempt
def delete_mess_incharge(request, mess_incharge_id):
    if request.method == 'POST':
        try:
            mess_incharge = get_object_or_404(MessIncharge, user_id=mess_incharge_id)
            user = mess_incharge.user
            mess_incharge.delete()
            user.delete()
            messages.success(request, 'Mess Incharge deleted successfully')
            return redirect('manage_mess_incharge')
        except Exception as e:
            messages.error(request, str(e))
            return redirect('manage_mess_incharge')
    return redirect('manage_mess_incharge')

@login_required
@csrf_exempt
def get_mess_incharge(request, mess_incharge_id):
    try:
        mess_incharge = MessIncharge.objects.select_related('user', 'hostel').get(user_id=mess_incharge_id)
        data = {
            'status': 'success',
            'mess_incharge': {
                'id': mess_incharge.user_id,
                'name': mess_incharge.name,
                'email': mess_incharge.user.email if hasattr(mess_incharge, 'user') else '',
                'contact_number': mess_incharge.contact_number,
                'gender': mess_incharge.gender,
                'is_active': mess_incharge.user.is_active if hasattr(mess_incharge, 'user') else False,
                'hostel_id': mess_incharge.hostel.id,
                'hostel_name': mess_incharge.hostel.name
            }
        }
        return JsonResponse(data)
    except MessIncharge.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Mess Incharge not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def manage_security_guards(request):
    """
    View to display all security guards
    """
    from security.models import SecurityGuard
    security_guards = SecurityGuard.objects.select_related('user', 'hostel').all().order_by('-created_at')
    hostels = Hostels.objects.all()
    return render(request, "manageSecurityGuards.html", {"security_guards": security_guards, "hostels": hostels})

@login_required
@csrf_exempt
def add_security_guard(request):
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            email = request.POST.get('email')
            username = request.POST.get('username')
            password = request.POST.get('password')
            contact_number = request.POST.get('contact_number')
            cnic = request.POST.get('cnic')
            street = request.POST.get('street')
            area = request.POST.get('area')
            city = request.POST.get('city')
            district = request.POST.get('district')
            gender = request.POST.get('gender')
            hostel_id = request.POST.get('hostel')
            shift = request.POST.get('shift')

            required_fields = {
                'name': name,
                'username': username,
                'email': email,
                'password': password,
                'gender': gender,
                'hostel': hostel_id,
                'shift': shift
            }
            missing_fields = [field for field, value in required_fields.items() if not value]
            if missing_fields:
                return JsonResponse({'status': 'error', 'message': f'Missing required fields: {", ".join(missing_fields)}'}, status=400)

            if User.objects.filter(username=username).exists():
                return JsonResponse({'status': 'error', 'message': 'Username already registered'}, status=400)

            if User.objects.filter(email=email).exists():
                return JsonResponse({'status': 'error', 'message': 'Email already registered'}, status=400)

            try:
                hostel = Hostels.objects.get(id=hostel_id)
                from security.models import SecurityGuard
                # Check if a security guard already exists for this hostel and shift
                if SecurityGuard.objects.filter(hostel=hostel, shift=shift).exists():
                    return JsonResponse({'status': 'error', 'message': 'A security guard is already assigned to this hostel for the selected shift.'}, status=400)

                user = User(
                    username=username,
                    email=email if email else '',
                    first_name=name.split()[0] if name else '',
                    last_name=' '.join(name.split()[1:]) if name and len(name.split()) > 1 else '',
                    is_staff=True
                )
                user.set_password(password)
                user.save()
                
                # Add user to Security group
                from django.contrib.auth.models import Group
                security_group, _ = Group.objects.get_or_create(name='Security')
                user.groups.add(security_group)

                security_guard = SecurityGuard(
                    user=user,
                    name=name,
                    contact_number=contact_number if contact_number else '',
                    cnic=cnic if cnic else '',
                    street=street if street else '',
                    area=area if area else '',
                    city=city if city else '',
                    district=district if district else '',
                    gender=gender,
                    hostel=hostel,
                    shift=shift,
                    created_at=timezone.now()
                )
                security_guard.save()

                # Ensure no Wardens object is created for this user
                from coustom_admin.models import Wardens
                if Wardens.objects.filter(user=user).exists():
                    Wardens.objects.filter(user=user).delete()

                response_data = {
                    'status': 'success',
                    'message': 'Security Guard registered successfully',
                    'redirect_url': reverse('manage_security_guards')
                }
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse(response_data)
                messages.success(request, response_data['message'])
                return redirect('manage_security_guards')
            except Exception as e:
                if 'user' in locals():
                    user.delete()
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    hostels = Hostels.objects.filter(status='Active')
    return render(request, "manageSecurityGuards.html", {"hostels": hostels})

@login_required
@csrf_exempt
def delete_security_guard(request, guard_id):
    if request.method == 'POST':
        try:
            from security.models import SecurityGuard
            security_guard = get_object_or_404(SecurityGuard, user_id=guard_id)
            user = security_guard.user
            security_guard.delete()
            user.delete()
            response_data = {'status': 'success', 'message': 'Security Guard deleted successfully'}
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse(response_data)
            messages.success(request, response_data['message'])
            return redirect('manage_security_guards')
        except Exception as e:
            response_data = {'status': 'error', 'message': str(e)}
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse(response_data, status=500)
            messages.error(request, response_data['message'])
            return redirect('manage_security_guards')
    return redirect('manage_security_guards')

@login_required
@csrf_exempt
def edit_security_guard(request, guard_id):
    if request.method == 'POST':
        try:
            from security.models import SecurityGuard
            security_guard = SecurityGuard.objects.select_related('user', 'hostel').get(user_id=guard_id)
            name = request.POST.get('name')
            email = request.POST.get('email')
            contact_number = request.POST.get('contact_number')
            cnic = request.POST.get('cnic')
            street = request.POST.get('street')
            area = request.POST.get('area')
            city = request.POST.get('city')
            district = request.POST.get('district')
            gender = request.POST.get('gender')
            hostel_id = request.POST.get('hostel')
            shift = request.POST.get('shift')
            is_active = request.POST.get('is_active') == 'on'

            hostel = Hostels.objects.get(id=hostel_id)
            # Check if a security guard already exists for this hostel and shift, excluding the current guard
            if SecurityGuard.objects.filter(hostel=hostel, shift=shift).exclude(user_id=guard_id).exists():
                return JsonResponse({'status': 'error', 'message': 'A security guard is already assigned to this hostel for the selected shift.'}, status=400)

            security_guard.name = name
            security_guard.contact_number = contact_number
            security_guard.cnic = cnic
            security_guard.street = street
            security_guard.area = area
            security_guard.city = city
            security_guard.district = district
            security_guard.gender = gender
            security_guard.hostel = hostel
            security_guard.shift = shift

            if hasattr(security_guard, 'user') and security_guard.user:
                user = security_guard.user
                user.email = email
                user.is_active = is_active
                user.save()

            security_guard.save()
            response_data = {
                'status': 'success', 
                'message': 'Security Guard updated successfully',
                'redirect_url': reverse('manage_security_guards')
            }
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse(response_data)
            messages.success(request, response_data['message'])
            return redirect('manage_security_guards')
        except SecurityGuard.DoesNotExist:
            response_data = {'status': 'error', 'message': 'Security Guard not found'}
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse(response_data, status=404)
            messages.error(request, response_data['message'])
            return redirect('manage_security_guards')
        except Exception as e:
            response_data = {'status': 'error', 'message': f'Failed to update Security Guard: {str(e)}'}
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse(response_data, status=500)
            messages.error(request, response_data['message'])
            return redirect('manage_security_guards')
    else:
        from security.models import SecurityGuard
        security_guard = get_object_or_404(SecurityGuard, user_id=guard_id)
        hostels = Hostels.objects.filter(status='Active')
        return render(request, "editSecurityGuard.html", {"security_guard": security_guard, "hostels": hostels})

@login_required
def get_security_guards_data(request):
    """
    Retrieve all security guard data from the database in JSON format.
    """
    from security.models import SecurityGuard
    security_guards = SecurityGuard.objects.select_related('user', 'hostel').all().order_by('-created_at')
    guards_data = [
        {
            'id': guard.user_id,
            'name': guard.name,
            'email': guard.user.email if hasattr(guard, 'user') else '',
            'contact_number': guard.contact_number,
            'cnic': guard.cnic,
            'street': guard.street,
            'area': guard.area,
            'city': guard.city,
            'district': guard.district,
            'gender': guard.gender,
            'hostel': guard.hostel.name if guard.hostel else '',
            'shift': guard.shift,
            'created_at': guard.created_at.strftime('%Y-%m-%d %H:%M:%S') if guard.created_at else '',
            'is_active': guard.user.is_active if hasattr(guard, 'user') else False
        }
        for guard in security_guards
    ]
    return JsonResponse({
        'status': 'success',
        'security_guards': guards_data
    })

@login_required
def security_deposits(request):
    """
    View to display all security deposits with filtering options.
    """
    from coustom_admin.models import SecurityDeposit, Hostels
    
    # Get all security deposits with related booking and student data
    deposits = SecurityDeposit.objects.select_related('booking', 'booking__student', 'booking__hostel', 'received_by').all().order_by('-payment_date')
    
    # Apply search filter if provided
    search_query = request.GET.get('search', '')
    if search_query:
        deposits = deposits.filter(
            Q(booking__student__user__first_name__icontains=search_query) |
            Q(booking__student__user__last_name__icontains=search_query) |
            Q(booking__student__user__email__icontains=search_query) |
            Q(transaction_id__icontains=search_query)
        )
    
    # Apply hostel filter if provided
    hostel_filter = request.GET.get('hostel', '')
    if hostel_filter:
        deposits = deposits.filter(booking__hostel_id=hostel_filter)
    
    # Get all hostels for filter dropdown
    hostels = Hostels.objects.all().order_by('name')
    
    context = {
        'deposits': deposits,
        'total_deposits': deposits.count(),
        'hostels': hostels,
        'search_query': search_query,
        'hostel_filter': hostel_filter,
    }
    
    return render(request, "securityDeposits.html", context)

@login_required
def student_feedbacks(request):
    """
    View to display all feedbacks submitted by students.
    """
    from student.models import Feedback
    from coustom_admin.models import Hostels
    
    # Get all feedbacks with related user and hostel data
    feedbacks = Feedback.objects.select_related('user', 'hostel').all().order_by('-created_at')
    
    # Apply search filter if provided
    search_query = request.GET.get('search', '')
    if search_query:
        feedbacks = feedbacks.filter(
            Q(feedback_text__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(hostel__name__icontains=search_query)
        )
    
    # Apply hostel filter if provided
    hostel_filter = request.GET.get('hostel', '')
    if hostel_filter:
        feedbacks = feedbacks.filter(hostel_id=hostel_filter)
    
    # Apply rating filter if provided
    rating_filter = request.GET.get('rating', '')
    if rating_filter:
        feedbacks = feedbacks.filter(rating=rating_filter)
    
    # Get all hostels for filter dropdown
    hostels = Hostels.objects.all().order_by('name')
    
    context = {
        'feedbacks': feedbacks,
        'hostels': hostels,
        'search_query': search_query,
        'hostel_filter': hostel_filter,
        'rating_filter': rating_filter,
    }
    
    return render(request, "student_feedbacks.html", context)

@login_required
def get_feedback_details(request, feedback_id):
    """
    API endpoint to retrieve detailed feedback information by ID.
    """
    from student.models import Feedback
    try:
        feedback = Feedback.objects.select_related('user', 'hostel').get(id=feedback_id)
        data = {
            'status': 'success',
            'feedback': {
                'id': feedback.id,
                'student': {
                    'full_name': feedback.user.get_full_name() if feedback.user else 'Anonymous',
                    'username': feedback.user.username if feedback.user else 'Anonymous',
                    'email': feedback.user.email if feedback.user else 'N/A'
                },
                'hostel': {
                    'name': feedback.hostel.name if feedback.hostel else 'Not Specified'
                },
                'rating': feedback.rating,
                'feedback_text': feedback.feedback_text,
                'status': 'New' if feedback.is_new else 'Reviewed',
                'created_at': feedback.created_at.strftime('%Y-%m-%d %H:%M') if feedback.created_at else 'N/A'
            }
        }
        return JsonResponse(data)
    except Feedback.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Feedback not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def get_assignment_details(request, assignment_id):
    """
    API endpoint to get details of a specific room assignment.
    Returns JSON data for use in the room assignment details modal.
    """
    try:
        assignment = get_object_or_404(RoomAssignment, id=assignment_id)
        booking = getattr(assignment, 'booking', None)
        if not booking:
            raise ValueError("Booking not found for this assignment")
        student = getattr(booking, 'student', None)
        if not student:
            raise ValueError("Student not found for this booking")
        room = getattr(assignment, 'room', None)
        if not room:
            raise ValueError("Room not found for this assignment")
        hostel = getattr(room, 'hostel', None)
        if not hostel:
            raise ValueError("Hostel not found for this room")
        
        # Safely access student name
        student_name = 'N/A'
        try:
            student_name = student.get_full_name() if hasattr(student, 'get_full_name') else student.username
        except Exception as e:
            logger.warning(f"Error getting student name for id {assignment_id}: {str(e)}")
            student_name = getattr(student, 'username', 'N/A')

        # Safely access student email
        student_email = getattr(student, 'email', 'N/A')

        # Safely access student contact
        student_contact = getattr(student, 'phone', 'N/A')

        # Safely access hostel name
        hostel_name = getattr(hostel, 'name', 'N/A')

        # Safely access room details
        room_number = getattr(room, 'room_number', 'N/A')
        room_type = 'N/A'
        try:
            room_type = room.get_room_type_display() if hasattr(room, 'get_room_type_display') else getattr(room, 'room_type', 'N/A')
        except Exception as e:
            logger.warning(f"Error getting room type for id {assignment_id}: {str(e)}")
            room_type = getattr(room, 'room_type', 'N/A')

        floor_number = getattr(room, 'floor_number', 'N/A')

        # Safely access dates
        assigned_date = ''
        try:
            assigned_date = assignment.assigned_date.isoformat() if hasattr(assignment, 'assigned_date') and assignment.assigned_date else ''
        except Exception as e:
            logger.warning(f"Error formatting assigned_date for id {assignment_id}: {str(e)}")

        check_in_date = ''
        try:
            check_in_date = booking.check_in_date.isoformat() if hasattr(booking, 'check_in_date') and booking.check_in_date else ''
        except Exception as e:
            logger.warning(f"Error formatting check_in_date for id {assignment_id}: {str(e)}")

        check_out_date = ''
        try:
            check_out_date = assignment.check_out_date.isoformat() if hasattr(assignment, 'check_out_date') and assignment.check_out_date else ''
        except Exception as e:
            logger.warning(f"Error formatting check_out_date for id {assignment_id}: {str(e)}")

        # Safely access assigned_by
        assigned_by = 'N/A'
        try:
            if hasattr(assignment, 'assigned_by') and assignment.assigned_by:
                assigned_by = assignment.assigned_by.get_full_name() if hasattr(assignment.assigned_by, 'get_full_name') else assignment.assigned_by.username
        except Exception as e:
            logger.warning(f"Error getting assigned_by for id {assignment_id}: {str(e)}")

        # Safely access duration
        duration = 'N/A'
        try:
            duration = f"{booking.duration_months} month(s)" if hasattr(booking, 'duration_months') and booking.duration_months else 'N/A'
        except Exception as e:
            logger.warning(f"Error getting duration for id {assignment_id}: {str(e)}")

        data = {
            'student_name': student_name,
            'student_email': student_email,
            'student_contact': student_contact,
            'hostel_name': hostel_name,
            'room_number': room_number,
            'room_type': room_type,
            'floor_number': floor_number,
            'assigned_date': assigned_date,
            'assigned_by': assigned_by,
            'is_active': getattr(assignment, 'is_active', False),
            'check_in_date': check_in_date,
            'check_out_date': check_out_date,
            'duration': duration
        }
        return JsonResponse(data)
    except RoomAssignment.DoesNotExist:
        logger.error(f"RoomAssignment not found for id: {assignment_id}")
        return JsonResponse({'error': 'Assignment not found'}, status=404)
    except ValueError as ve:
        logger.error(f"Data integrity error in get_assignment_details for id {assignment_id}: {str(ve)}")
        return JsonResponse({'error': f'Missing data: {str(ve)}'}, status=500)
    except AttributeError as ae:
        logger.error(f"Attribute error in get_assignment_details for id {assignment_id}: {str(ae)}")
        return JsonResponse({'error': f'Invalid data structure: {str(ae)}'}, status=500)
    except Exception as e:
        logger.error(f"Unexpected error in get_assignment_details for id {assignment_id}: {str(e)}", exc_info=True)
        return JsonResponse({'error': f'Failed to load assignment details: {str(e)}'}, status=500)


@login_required
def monthly_fees(request):
    """
    View to display all student monthly fees with filtering options.
    """
    from coustom_admin.models import StudentMonthlyFee, Hostels
    
    # Get all monthly fees with related student and hostel data
    fees = StudentMonthlyFee.objects.select_related('student', 'student__user', 'hostel').all().order_by('-year', '-month', '-created_at')
    
    # Apply search filter if provided
    search_query = request.GET.get('search', '')
    if search_query:
        fees = fees.filter(
            Q(student__user__first_name__icontains=search_query) |
            Q(student__user__last_name__icontains=search_query) |
            Q(student__user__email__icontains=search_query) |
            Q(transaction_id__icontains=search_query)
        )
    
    # Apply hostel filter if provided
    hostel_filter = request.GET.get('hostel', '')
    if hostel_filter:
        fees = fees.filter(hostel_id=hostel_filter)
    
    # Apply month filter if provided
    month_filter = request.GET.get('month', '')
    if month_filter:
        fees = fees.filter(month=month_filter)
    
    # Apply year filter if provided
    year_filter = request.GET.get('year', '')
    if year_filter:
        fees = fees.filter(year=year_filter)
    
    # Get all hostels for filter dropdown
    hostels = Hostels.objects.all().order_by('name')
    
    # Prepare month choices for filter dropdown (all months)
    current_date = timezone.now().date()
    current_month = current_date.month
    current_year = current_date.year
    previous_month = current_month - 1 if current_month > 1 else 12
    previous_year = current_year if current_month > 1 else current_year - 1
    
    months = [(i, calendar.month_name[i]) for i in range(1, 13)]
    calc_months = [
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
        'fees': fees_page,
        'page_obj': fees_page,
        'hostels': hostels,
        'months': months,
        'calc_months': calc_months,
        'years': years,
        'current_month': current_month,
        'current_year': current_year,
        'search_query': search_query,
        'hostel_filter': hostel_filter,
        'month_filter': month_filter,
        'year_filter': year_filter,
    }
    
    return render(request, "monthly_fees.html", context)


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='login')
def calculate_monthly_fees_view(request):
    """
    View to trigger the calculation of monthly fees for students.
    """
    if request.method == 'POST':
        try:
            month = int(request.POST.get('month', timezone.now().month))
            year = int(request.POST.get('year', timezone.now().year))
            electricity_bill = Decimal(request.POST.get('electricity_bill', '0.00'))
            hostel_id = request.POST.get('hostel', '')
            
            # Check if fees already exist for the selected hostel, month, and year
            from coustom_admin.models import StudentMonthlyFee, Hostels
            if hostel_id:
                hostel = Hostels.objects.get(id=hostel_id)
                if StudentMonthlyFee.objects.filter(hostel_id=hostel_id, month=month, year=year).exists():
                    messages.warning(request, f'Monthly fees for {calendar.month_name[month]} {year} have already been generated for {hostel.name}.')
                    return redirect('monthly_fees')
            else:
                # Check for all hostels if no specific hostel is selected
                hostels_with_fees = Hostels.objects.filter(studentmonthlyfee__month=month, studentmonthlyfee__year=year).distinct()
                if hostels_with_fees.exists():
                    hostel_names = ", ".join([hostel.name for hostel in hostels_with_fees])
                    messages.warning(request, f'Monthly fees for {calendar.month_name[month]} {year} have already been generated for the following hostels: {hostel_names}.')
                    return redirect('monthly_fees')
            
            # Call the management command to calculate fees
            from django.core.management import call_command
            call_command('calculate_monthly_fees', month=month, year=year, electricity=electricity_bill, hostel=hostel_id)
            
            messages.success(request, f'Monthly fees for {calendar.month_name[month]} {year} have been calculated successfully.')
            return redirect('monthly_fees')
        except Exception as e:
            messages.error(request, f'Error calculating monthly fees: {str(e)}')
            return redirect('monthly_fees')
    
    # For GET request, show the form
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
    hostels = Hostels.objects.all().order_by('name')
    
    context = {
        'current_month': current_month,
        'current_year': current_year,
        'months': months,
        'years': years,
        'hostels': hostels,
    }
    return render(request, "calculate_monthly_fees.html", context)


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='login')
def edit_monthly_fee(request, fee_id):
    """
    View to edit a specific student monthly fee record.
    """
    from coustom_admin.models import StudentMonthlyFee
    
    fee = get_object_or_404(StudentMonthlyFee, id=fee_id)
    
    if request.method == 'POST':
        try:
            monthly_rent = float(request.POST.get('monthly_rent', fee.monthly_rent))
            mess_expenses = float(request.POST.get('mess_expenses', fee.mess_expenses))
            electricity_bill = float(request.POST.get('electricity_bill', fee.electricity_bill))
            payment_status = request.POST.get('payment_status', fee.payment_status)
            due_date = request.POST.get('due_date', fee.due_date)
            payment_date = request.POST.get('payment_date', fee.payment_date)
            transaction_id = request.POST.get('transaction_id', fee.transaction_id)
            notes = request.POST.get('notes', fee.notes)
            
            fee.monthly_rent = monthly_rent
            fee.mess_expenses = mess_expenses
            fee.electricity_bill = electricity_bill
            fee.payment_status = payment_status
            fee.due_date = due_date if due_date else fee.due_date
            fee.payment_date = payment_date if payment_date else fee.payment_date
            fee.transaction_id = transaction_id if transaction_id else fee.transaction_id
            fee.notes = notes if notes else fee.notes
            fee.save()
            
            messages.success(request, f'Fee record for {fee.student.user.get_full_name()} updated successfully.')
            return redirect('monthly_fees')
        except Exception as e:
            messages.error(request, f'Error updating fee record: {str(e)}')
            return redirect('monthly_fees')
    
    context = {
        'fee': fee,
    }
    return render(request, "monthly_fees.html", context)


@login_required
@user_passes_test(lambda u: u.is_staff, login_url='admin_login')
def mark_fee_paid(request, fee_id):
    """
    View to mark a specific student monthly fee as paid.
    """
    from coustom_admin.models import StudentMonthlyFee
    
    fee = get_object_or_404(StudentMonthlyFee, id=fee_id)
    
    if request.method == 'POST':
        try:
            payment_date = request.POST.get('payment_date', timezone.now().date())
            transaction_id = request.POST.get('transaction_id', '')
            notes = request.POST.get('notes', '')
            
            fee.payment_status = 'Paid'
            fee.payment_date = payment_date if payment_date else timezone.now().date()
            fee.transaction_id = transaction_id if transaction_id else fee.transaction_id
            fee.notes = notes if notes else fee.notes
            fee.save()
            
            messages.success(request, f'Fee for {fee.student.user.get_full_name()} marked as paid.')
            return redirect('monthly_fees')
        except Exception as e:
            messages.error(request, f'Error marking fee as paid: {str(e)}')
            return redirect('monthly_fees')
    
    context = {
        'fee': fee,
    }
    return render(request, "monthly_fees.html", context)

@login_required
@user_passes_test(lambda u: u.is_staff, login_url='admin_login')
def collect_monthly_fee(request, fee_id):
    """
    View to collect payment for a specific monthly fee in the admin app.
    """
    from coustom_admin.models import StudentMonthlyFee
    from django.utils import timezone
    from coustom_admin.payment_forms import MonthlyFeePaymentForm
    
    fee = get_object_or_404(StudentMonthlyFee, id=fee_id)
    
    if request.method == 'POST':
        form = MonthlyFeePaymentForm(request.POST)
        if form.is_valid():
            payment_method = form.cleaned_data.get('payment_method', 'Cash')
            transaction_id = form.cleaned_data.get('transaction_id', '')
            notes = form.cleaned_data.get('notes', '')
            amount = form.cleaned_data.get('amount', '')
            
            fee.payment_status = 'Paid'
            fee.payment_date = timezone.now().date()
            fee.transaction_id = transaction_id if transaction_id else None
            fee.notes = notes
            if amount:
                try:
                    fee.monthly_rent = float(amount)
                except ValueError:
                    pass  # If amount is invalid, keep the original value
            fee.collected_by = request.user  # Store the user who collected the fee
            # Recalculate total_fee to ensure it includes all components
            from decimal import Decimal
            fee.total_fee = Decimal(str(fee.monthly_rent)) + fee.mess_expenses + fee.electricity_bill
            fee.save()
            
            success_message = f"Payment recorded for {fee.student.user.get_full_name()}."
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': success_message
                })
            else:
                from urllib.parse import urlencode
                return redirect('/admin/monthly_fees/?' + urlencode({'success_message': success_message}))
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Form validation failed',
                    'errors': form.errors
                }, status=400)
            messages.error(request, 'Form validation failed. Please correct the errors below.')
    else:
        form = MonthlyFeePaymentForm(initial={'amount': fee.total_fee})
    
    context = {
        'fee': fee,
        'form': form,
    }
    return render(request, "payment_form.html", context)
