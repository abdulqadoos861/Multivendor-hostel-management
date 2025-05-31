from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from .models import Hostels, Wardens, HostelWardens, bookingRequest
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
import json
from django.db.models import Q



# Create your views here.

def admin_login(request):
    try:
        if request.user.is_authenticated:
            return redirect("dashboard")
            
        if request.method == "POST":
            username = request.POST.get("username")
            password = request.POST.get("password")
            
            # Authenticate user
            user = authenticate(request, username=username, password=password)
            
            if user is not None and user.is_superuser:
                login(request, user)
                return redirect("dashboard")
            else:
                messages.error(request, "Invalid credentials")
                return render(request, "admin_login.html")
        
        # GET request - show login form
        return render(request, "admin_login.html")
        
    except Exception as e:
        print(e)
        messages.error(request, "An error occurred. Please try again.")
        return render(request, "admin_login.html")

@login_required
def dashboard(request):
    return render(request, "dashboard.html")


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

            # Validate required fields
            if not all([name, address, gender, contact_number, total_floors]):
                return JsonResponse({"status": "error", "message": "All required fields must be provided"}, status=400)

            # Convert total_floors to integer
            try:
                total_floors = int(total_floors)
                if total_floors < 1:
                    return JsonResponse({"status": "error", "message": "Total floors must be at least 1"}, status=400)
            except ValueError:
                return JsonResponse({"status": "error", "message": "Total floors must be a valid number"}, status=400)

            # Validate gender
            if gender not in ['male', 'female']:
                return JsonResponse({"status": "error", "message": "Invalid gender value"}, status=400)

            # Convert created_at string to datetime if provided
            created_at_date = None
            if created_at:
                try:
                    created_at_date = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S")
                    created_at_date = timezone.make_aware(created_at_date)
                except ValueError:
                    return JsonResponse({"status": "error", "message": "Invalid date format for created_at"}, status=400)

            # Create and save hostel
            hostel = Hostels(
                name=name,
                address=address,
                gender=gender,
                contact_number=contact_number,
                total_floors=total_floors,
                description=description or "",  # Handle empty description
                created_at=created_at_date or timezone.now()
            )
            hostel.save()
            
            return JsonResponse({"status": "success", "message": "Hostel added successfully"})
        except Exception as e:
            # Log the error for debugging
            print(f"Error in add_hostel: {str(e)}")
            return JsonResponse({"status": "error", "message": f"Server error: {str(e)}"}, status=500)
    else:
        return JsonResponse({"status": "error", "message": "Invalid request method"}, status=400)
        

def updateHostel(request, id):
    if request.method == "POST":
        try:
            print(f"Updating hostel with ID: {id}")
            print(f"POST data: {request.POST}")
            
            hostel = get_object_or_404(Hostels, id=id)
            
            # Get form data
            name = request.POST.get("name")
            address = request.POST.get("address")
            gender = request.POST.get("gender")
            contact_number = request.POST.get("contact_number")
            total_floors = request.POST.get("total_floors")
            description = request.POST.get("description")

            print(f"Form data received: name={name}, address={address}, gender={gender}, contact={contact_number}, floors={total_floors}")

            # Validate required fields
            if not all([name, address, gender, contact_number, total_floors]):
                missing_fields = [field for field, value in {
                    'name': name, 'address': address, 'gender': gender,
                    'contact_number': contact_number, 'total_floors': total_floors
                }.items() if not value]
                return JsonResponse({
                    "status": "error",
                    "message": f"Missing required fields: {', '.join(missing_fields)}"
                }, status=400)

            # Convert total_floors to integer
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

            # Validate gender
            if gender not in ['male', 'female']:
                return JsonResponse({
                    "status": "error",
                    "message": f"Invalid gender value: {gender}. Must be 'male' or 'female'"
                }, status=400)

            # Update hostel fields
            hostel.name = name
            hostel.address = address
            hostel.gender = gender
            hostel.contact_number = contact_number
            hostel.total_floors = total_floors
            hostel.description = description or ""
            
            # Save the updated hostel
            hostel.save()
            print(f"Successfully updated hostel {id}")
            
            return JsonResponse({
                "status": "success",
                "message": "Hostel updated successfully"
            })
        except Hostels.DoesNotExist:
            print(f"Hostel with ID {id} not found")
            return JsonResponse({
                "status": "error",
                "message": f"Hostel with ID {id} not found"
            }, status=404)
        except Exception as e:
            print(f"Error in update_hostel: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": "error",
                "message": f"Server error: {str(e)}"
            }, status=500)
    else:
        return JsonResponse({
            "status": "error",
            "message": f"Invalid request method: {request.method}. Only POST is allowed."
        }, status=400)

def hostellist(request):
    hostels = Hostels.objects.all()
    print(f"Retrieved {hostels.count()} hostels from database")  # Debug log
    return render(request, 'hostel_form.html', {'hostels': hostels})

def hostels(request):
    hostels = Hostels.objects.all().order_by('-created_at')
    return render(request, "hostels.html", {'hostels': hostels})

def dashboard(request):
    return render(request,"dashboard.html")
def complaints(request):
    return render(request,"complaints.html")
def expenses(request):
    return render(request,"expenses.html")
def manageStudent(request):
    return render(request,"manageStudent.html")
def manageWardens(request):
    wardens = Wardens.objects.select_related('user_id').prefetch_related('hostelwardens_set__hostel').all().order_by('-created_at')
    return render(request, "manageWardens.html", {"wardens": wardens})
def manageBookings(request):
    # Get all booking requests with related user and hostel data
    bookings = bookingRequest.objects.select_related('user_id', 'hostel_id').all().order_by('-request_date')
    
    # Get filter parameters
    status = request.GET.get('status', '')
    hostel_id = request.GET.get('hostel', '')
    search = request.GET.get('search', '')
    
    # Apply filters if provided
    if status:
        bookings = bookings.filter(status=status)
    if hostel_id:
        bookings = bookings.filter(hostel_id=hostel_id)
    if search:
        bookings = bookings.filter(
            Q(user_id__first_name__icontains=search) |
            Q(user_id__last_name__icontains=search) |
            Q(user_id__username__icontains=search)
        )
    
    # Get all hostels for the filter dropdown
    hostels = Hostels.objects.all()
    
    context = {
        'bookings': bookings,
        'hostels': hostels,
        'total_bookings': bookings.count(),
        'status_filter': status,
        'hostel_filter': hostel_id,
        'search_query': search
    }
    
    return render(request, "manageBookings.html", context)

def profile(request):
    return render(request,"profile.html")

def deleteHostel(request, id):
    if request.method == "POST":
        try:
            print(f"Deleting hostel with ID: {id}")
            hostel = get_object_or_404(Hostels, id=id)
            hostel_name = hostel.name
            hostel.delete()
            print(f"Successfully deleted hostel {id}")
            
            return JsonResponse({
                "status": "success",
                "message": f"Hostel '{hostel_name}' deleted successfully"
            })
        except Hostels.DoesNotExist:
            print(f"Hostel with ID {id} not found")
            return JsonResponse({
                "status": "error",
                "message": f"Hostel with ID {id} not found"
            }, status=404)
        except Exception as e:
            print(f"Error in delete_hostel: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return JsonResponse({
                "status": "error",
                "message": f"Server error: {str(e)}"
            }, status=500)
    else:
        return JsonResponse({
            "status": "error",
            "message": f"Invalid request method: {request.method}. Only POST is allowed."
        }, status=400)


@csrf_exempt
def addWarden(request):
    if request.method == 'POST':
        try:
            # Extract data from request
            name = request.POST.get('name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            gender = request.POST.get('gender')
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')

            # Validate required fields
            if not all([name, email, phone, gender, password, confirm_password]):
                messages.error(request, 'All fields are required')
                return redirect('manageWardens')

            # Check if passwords match
            if password != confirm_password:
                messages.error(request, 'Passwords do not match')
                return redirect('manageWardens')

            # Check if email already exists
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already registered')
                return redirect('manageWardens')

            # Create username from email (before @ symbol)
            username = email.split('@')[0]
            
            # Check if username already exists
            if User.objects.filter(username=username).exists():
                # If username exists, append a number
                base_username = username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1

            try:
                # Create User account with proper password hashing and staff role
                user = User(
                    username=username,
                    email=email,
                    first_name=name.split()[0],
                    last_name=' '.join(name.split()[1:]) if len(name.split()) > 1 else '',
                    is_staff=True  # Set the user as staff (warden)
                )
                user.set_password(password)  # This will properly hash the password
                user.save()

                # Create Warden profile
                warden = Wardens(
                    user_id=user,
                    name=name,
                    contact_number=phone,
                    gender=gender
                )
                warden.save()

                messages.success(request, 'Warden registered successfully')
                return redirect('manageWardens')

            except Exception as e:
                # If anything fails, delete the user if it was created
                if 'user' in locals():
                    user.delete()
                raise e

        except Exception as e:
            messages.error(request, str(e))
            return redirect('manageWardens')

    return redirect('manageWardens')

def wardenlist(request):
    wardens = Wardens.objects.all().order_by('-created_at')
    return render(request, "wardenlist.html", {"wardens": wardens})

@csrf_exempt
def getAvailableHostels(request, warden_id):
    if request.method == 'GET':
        try:
            # Get all hostels that don't have a warden assigned
            assigned_hostel_ids = HostelWardens.objects.values_list('hostel_id', flat=True)
            available_hostels = Hostels.objects.exclude(id__in=assigned_hostel_ids)
            
            context = {
                'warden_id': warden_id,
                'hostels': available_hostels
            }
            return render(request, 'assign_hostel.html', context)
        except Exception as e:
            messages.error(request, str(e))
            return redirect('manageWardens')
    return redirect('manageWardens')

@csrf_exempt
def assignHostel(request):
    if request.method == 'POST':
        try:
            warden_id = request.POST.get('warden_id')
            hostel_id = request.POST.get('hostel')
            
            if not all([warden_id, hostel_id]):
                messages.error(request, 'Warden ID and Hostel ID are required')
                return redirect('manageWardens')
            
            warden = get_object_or_404(Wardens, id=warden_id)
            hostel = get_object_or_404(Hostels, id=hostel_id)
            
            # Check if hostel is already assigned
            if HostelWardens.objects.filter(hostel=hostel).exists():
                messages.error(request, 'This hostel is already assigned to another warden')
                return redirect('manageWardens')
            
            # Create the assignment
            hostel_warden = HostelWardens(
                hostel=hostel,
                warden=warden
            )
            hostel_warden.save()
            
            messages.success(request, f'Hostel {hostel.name} assigned to warden {warden.name} successfully')
            return redirect('manageWardens')
        except Exception as e:
            messages.error(request, str(e))
            return redirect('manageWardens')
    return redirect('manageWardens')

@csrf_exempt
def deleteWarden(request, warden_id):
    if request.method == 'POST':
        try:
            warden = get_object_or_404(Wardens, id=warden_id)
            
            # Delete the warden's hostel assignments first
            HostelWardens.objects.filter(warden=warden).delete()
            
            # Delete the associated user
            user = warden.user_id
            warden.delete()
            user.delete()
            
            messages.success(request, 'Warden deleted successfully')
            return redirect('manageWardens')
        except Exception as e:
            messages.error(request, str(e))
            return redirect('manageWardens')
    return redirect('manageWardens')

@csrf_exempt
def approveBooking(request, booking_id):
    if request.method == 'POST':
        try:
            booking = get_object_or_404(bookingRequest, id=booking_id)
            booking.status = 'Approved'
            booking.save()
            messages.success(request, 'Booking approved successfully')
        except Exception as e:
            messages.error(request, str(e))
    return redirect('manageBookings')

@csrf_exempt
def rejectBooking(request, booking_id):
    if request.method == 'POST':
        try:
            booking = get_object_or_404(bookingRequest, id=booking_id)
            reason = request.POST.get('rejection_reason', '')
            booking.status = 'Rejected'
            booking.save()
            messages.success(request, 'Booking rejected successfully')
        except Exception as e:
            messages.error(request, str(e))
    return redirect('manageBookings')

# @@@@@@@@ manage student @@@@@@@@

def users(request):
    # Get all users except superusers (admins)
    users = User.objects.filter(is_superuser=False).order_by('-date_joined')
    
    # Get filter parameters
    role = request.GET.get('role', '')
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
    # Apply filters if provided
    if role:
        if role == 'warden':
            users = users.filter(is_staff=True)
        elif role == 'student':
            users = users.filter(is_staff=False)
    
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
    
    return render(request, "users.html", context)

@csrf_exempt
def deleteUser(request, user_id):
    if request.method == 'POST':
        try:
            user = get_object_or_404(User, id=user_id)
            
            # Don't allow deletion of superusers
            if user.is_superuser:
                messages.error(request, 'Cannot delete superuser accounts')
                return redirect('users')
            
            # Delete the user
            user.delete()
            messages.success(request, 'User deleted successfully')
        except Exception as e:
            messages.error(request, str(e))
    return redirect('users')

@csrf_exempt
def updateWarden(request, warden_id):
    if request.method == 'POST':
        try:
            warden = get_object_or_404(Wardens, id=warden_id)
            user = warden.user_id
            
            # Get form data
            name = request.POST.get('name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            gender = request.POST.get('gender')
            is_active = request.POST.get('is_active') == 'on'
            
            # Update user data
            user.first_name = name.split()[0]
            user.last_name = ' '.join(name.split()[1:]) if len(name.split()) > 1 else ''
            user.email = email
            user.is_active = is_active
            user.save()
            
            # Update warden data
            warden.name = name
            warden.contact_number = phone
            warden.gender = gender
            warden.save()
            
            return JsonResponse({
                "status": "success",
                "message": "Warden updated successfully"
            })
        except Exception as e:
            return JsonResponse({
                "status": "error",
                "message": str(e)
            }, status=500)
    return JsonResponse({
        "status": "error",
        "message": "Invalid request method"
    }, status=400)

@csrf_exempt
def updateUser(request, user_id):
    if request.method == 'POST':
        try:
            user = get_object_or_404(User, id=user_id)
            
            # Don't allow updating superusers
            if user.is_superuser:
                return JsonResponse({
                    "status": "error",
                    "message": "Cannot update superuser accounts"
                }, status=403)
            
            # Get form data
            name = request.POST.get('name')
            email = request.POST.get('email')
            role = request.POST.get('role')
            is_active = request.POST.get('is_active') == 'on'
            
            # Update user data
            user.first_name = name.split()[0]
            user.last_name = ' '.join(name.split()[1:]) if len(name.split()) > 1 else ''
            user.email = email
            user.is_active = is_active
            
            # Update role
            if role == 'warden':
                user.is_staff = True
            else:
                user.is_staff = False
            
            user.save()
            
            return JsonResponse({
                "status": "success",
                "message": "User updated successfully"
            })
        except Exception as e:
            return JsonResponse({
                "status": "error",
                "message": str(e)
            }, status=500)
    return JsonResponse({
        "status": "error",
        "message": "Invalid request method"
    }, status=400)
