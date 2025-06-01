from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from .models import Hostels, Wardens, HostelWardens, Rooms, RoomTypeRate, Student, BookingRequest
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.utils import timezone
from datetime import datetime, timedelta
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.db.models import Q, Count, F
from .forms import StudentRegistrationForm, BookingRequestForm
from django.urls import reverse
import json
import re

def is_student(user):
    return hasattr(user, 'student')

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
    return render(request, "dashboard.html")

@login_required
def add_room(request):
    hostels = Hostels.objects.all()
    rooms = Rooms.objects.all()

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
                rent = rate.per_head_rent * capacity
            except RoomTypeRate.DoesNotExist:
                messages.error(request, f'No fixed rate found for {room_type} in {hostel.name}. Please set rates first.')
                return redirect('fixed_rates')

            if Rooms.objects.filter(room_number=room_number).exclude(id=room.id if 'room' in locals() else None).exists():
                messages.error(request, f'Room number {room_number} already exists.')
                return redirect('add_room')

            room = Rooms(
                hostel_id=hostel,
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
                rent = rate.per_head_rent * capacity
            except RoomTypeRate.DoesNotExist:
                messages.error(request, f'No fixed rate found for {room_type} in {hostel.name}. Please set rates first.')
                return redirect('fixed_rates')

            if Rooms.objects.filter(room_number=room_number).exclude(id=room.id).exists():
                messages.error(request, f'Room number {room_number} already exists.')
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
def get_room_rate(request, hostel_id, room_type):
    try:
        rate = RoomTypeRate.objects.get(hostel_id=hostel_id, room_type=room_type)
        return JsonResponse({'per_head_rent': float(rate.per_head_rent)})
    except RoomTypeRate.DoesNotExist:
        return JsonResponse({'per_head_rent': None})

@login_required
def fixed_rates(request):
    hostels = Hostels.objects.all()
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

            if gender not in ['Male','male', 'Female', 'female', 'Other', 'other']:
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
            print(f"Error in add_hostel: {str(e)}")
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
            description = request.POST.get("description")

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

            if gender not in ['Male', 'Female']:
                return JsonResponse({
                    "status": "error",
                    "message": f"Invalid gender value: {gender}"
                }, status=400)

            hostel.name = name
            hostel.address = address
            hostel.gender = gender
            hostel.contact_number = contact_number
            hostel.total_floors = total_floors
            hostel.description = description or ""
            
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
def hostels(request):
    hostels = Hostels.objects.all().order_by('-created_at')
    return render(request, "hostels.html", {'hostels': hostels})

@login_required
def complaints(request):
    return render(request, "complaints.html")

@login_required
def expenses(request):
    return render(request, "expenses.html")

@login_required
def manageStudent(request):
    print("DEBUG: manageStudent view called")  # Debug log
    students = Student.objects.all()
    form = StudentRegistrationForm()
    hostels = Hostels.objects.all()
    
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
                        address=form.cleaned_data['address'],
                        gender=form.cleaned_data['gender'],
                        institute=form.cleaned_data['institute']
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
    user = get_object_or_404(User, id=user_id)
    student = get_object_or_404(Student, user=user)
    
    if request.method == 'POST':
        try:
            username = request.POST.get('username')
            email = request.POST.get('email')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            contact_number = request.POST.get('contact_number')
            cnic = request.POST.get('cnic')
            address = request.POST.get('address')
            gender = request.POST.get('gender')
            institute = request.POST.get('institute')
            
            # Update user
            user.username = username
            user.email = email
            user.first_name = first_name
            user.last_name = last_name
            user.save()
            
            # Update student profile
            student.contact_number = contact_number
            student.cnic = cnic
            student.address = address
            student.gender = gender
            student.institute = institute
            student.save()
            
            messages.success(request, 'Student updated successfully!')
            return JsonResponse({'success': True})
            
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    # Prepare student data for the form
    student_data = {
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'contact_number': student.contact_number,
        'cnic': student.cnic,
        'address': student.address,
        'gender': student.gender,
        'institute': student.institute
    }
    
    return JsonResponse(student_data)

@login_required
def delete_student(request, user_id):
    if request.method == 'POST':
        try:
            user = get_object_or_404(User, id=user_id)
            student = get_object_or_404(Student, user=user)
            username = user.username
            user.delete()
            return JsonResponse({'status': 'success', 'message': f'Student {username} deleted successfully'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Error deleting student: {str(e)}'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

def manageWardens(request):
    wardens = Wardens.objects.select_related('user_id').prefetch_related('hostelwardens_set__hostel').all().order_by('-created_at')
    return render(request, "manageWardens.html", {"wardens": wardens})

@login_required
@csrf_exempt
def addWarden(request):
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            gender = request.POST.get('gender')
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')

            # Check if it's an AJAX request
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

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
                    gender=gender
                )
                warden.save()

                if is_ajax:
                    return JsonResponse({
                        'status': 'success', 
                        'message': 'Warden registered successfully',
                        'warden': {
                            'id': warden.id,
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

@login_required
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
            
            if HostelWardens.objects.filter(hostel=hostel).exists():
                messages.error(request, 'This hostel is already assigned to another warden')
                return redirect('manageWardens')
            
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

@login_required
@csrf_exempt
def deleteWarden(request, warden_id):
    if request.method == 'POST':
        try:
            warden = get_object_or_404(Wardens, id=warden_id)
            
            HostelWardens.objects.filter(warden=warden).delete()
            
            user = warden.user_id
            warden.delete()
            user.delete()
            
            messages.success(request, 'Warden deleted successfully')
            return redirect('manageWardens')
        except Exception as e:
            messages.error(request, str(e))
            return redirect('manageWardens')
    return redirect('manageWardens')

@login_required
def users(request):
    users = User.objects.filter(is_superuser=False).order_by('-date_joined')
    
    role = request.GET.get('role', '')
    status = request.GET.get('status', '')
    search = request.GET.get('search', '')
    
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
def updateWarden(request, warden_id):
    if request.method == 'POST':
        try:
            warden = get_object_or_404(Wardens, id=warden_id)
            user = warden.user_id
            
            name = request.POST.get('name')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            gender = request.POST.get('gender')
            is_active = request.POST.get('is_active') == 'on'
            
            user.first_name = name.split()[0]
            user.last_name = ' '.join(name.split()[1:]) if len(name.split()) > 1 else ''
            user.email = email
            user.is_active = is_active
            user.save()
            
            warden.name = name
            warden.contact_number = phone
            warden.gender = gender
            warden.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Warden updated successfully'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=400)

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

@login_required
def profile(request):
    return render(request, 'profile.html')

@login_required
def manage_booking(request):
    if is_student(request.user):
        # For students, show only their bookings
        bookings = BookingRequest.objects.filter(student=request.user.student)
    else:
        # For admins, show all bookings
        bookings = BookingRequest.objects.all()
    
    # Add status counts for summary
    status_counts = bookings.values('status').annotate(count=Count('status'))
    
    context = {
        'bookings': bookings.order_by('-request_date'),
        'status_counts': {item['status']: item['count'] for item in status_counts},
        'total_bookings': bookings.count(),
    }
    return render(request, 'manageBookings.html', context)

@login_required
@user_passes_test(is_student, login_url='/admin/')
def create_booking(request):
    if request.method == 'POST':
        form = BookingRequestForm(request.POST, user=request.user)
        if form.is_valid():
            booking = form.save(commit=False)
            booking.student = request.user.student
            booking.status = 'Pending'
            booking.save()
            messages.success(request, 'Your booking request has been submitted successfully!')
            return redirect('manage_booking')
    else:
        form = BookingRequestForm(user=request.user)
    
    return render(request, 'create_booking.html', {'form': form})

@login_required
@user_passes_test(lambda u: u.is_staff, login_url='login')
def approve_booking(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(BookingRequest, id=booking_id)
        booking.status = 'Approved'
        booking.admin_notes = request.POST.get('admin_notes', '')
        booking.save()
        messages.success(request, f'Booking #{booking.id} has been approved.')
    return redirect('manage_booking')

@login_required
@user_passes_test(lambda u: u.is_staff, login_url='login')
def reject_booking(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(BookingRequest, id=booking_id)
        booking.status = 'Rejected'
        booking.admin_notes = request.POST.get('admin_notes', '')
        booking.save()
        messages.warning(request, f'Booking #{booking.id} has been rejected.')
    return redirect('manage_booking')

@login_required
def cancel_booking(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(BookingRequest, id=booking_id)
        # Only allow the student who made the booking or an admin to cancel
        if request.user.student == booking.student or request.user.is_staff:
            booking.status = 'Cancelled'
            if request.user.is_staff:
                booking.admin_notes = request.POST.get('admin_notes', 'Cancelled by admin')
            booking.save()
            messages.info(request, f'Booking #{booking.id} has been cancelled.')
        else:
            messages.error(request, 'You are not authorized to cancel this booking.')
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
                        'rate': room_type.per_head_rent,  # Changed from rate to per_head_rent
                        'total_rooms': total_rooms
                    })
            
            return JsonResponse({'status': 'success', 'availability': availability})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def get_room_types(request):
    """AJAX view to get room types for a specific hostel"""
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

# manage_booking function is used for handling booking management