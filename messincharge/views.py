from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth import logout
from django.db import models
from coustom_admin.models import MessIncharge
from messincharge.models import MessMenu , Expenses

def messincharge(request):
    if not request.user.is_authenticated:
        messages.error(request, 'You must be logged in to access this page.')
        return redirect('messincharge:mess_incharge_login')
    
    try:
        mess_incharge = MessIncharge.objects.get(user=request.user)
        hostel_name = mess_incharge.hostel.name if mess_incharge.hostel else "Not Assigned"
        
        # Calculate statistics
        from messincharge.models import MessStudent, Expenses
        enrolled_students_count = MessStudent.objects.filter(hostel=mess_incharge.hostel, is_active=True).count()
        total_expenses = Expenses.objects.filter(hostel_id=mess_incharge.hostel).aggregate(total=models.Sum('amount'))['total'] or 0
        
        context = {
            'hostel_name': hostel_name,
            'enrolled_students_count': enrolled_students_count,
            'total_expenses': total_expenses,
        }
        return render(request, 'messincharge/minc_dashboard.html', context)
    except MessIncharge.DoesNotExist:
        messages.error(request, 'You are not registered as a Mess Incharge.')
        return redirect('messincharge:mess_incharge_login')

def mess_incharge_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            print(f"User {username} authenticated successfully. User ID: {user.id}, Is Staff: {user.is_staff}")
            try:
                mess_incharge = MessIncharge.objects.get(user=user)
                print(f"Mess Incharge profile found for user {username}. Associated User ID: {mess_incharge.user.id}")
                login(request, user)
                messages.success(request, 'Login successful.')
                return redirect('messincharge:messincharge')  # Redirect to mess in-charge dashboard or index
            except MessIncharge.DoesNotExist:
                print(f"No Mess Incharge profile found for user {username}.")
                messages.error(request, 'You are not registered as a Mess Incharge.')
        else:
            print(f"Authentication failed for username: {username}")
            messages.error(request, 'Invalid username or password.')
    return render(request, 'messincharge/mess_incharge_login.html')

def mess_incharge_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('messincharge:mess_incharge_login')

def mess_menu(request):
    if not request.user.is_authenticated:
        messages.error(request, 'You must be logged in to access this page.')
        return redirect('messincharge:mess_incharge_login')
    
    try:
        mess_incharge = MessIncharge.objects.get(user=request.user)
    except MessIncharge.DoesNotExist:
        messages.error(request, 'You are not registered as a Mess Incharge.')
        return redirect('messincharge:mess_incharge_login')
    
    from datetime import datetime, timedelta
    import json
    
    if request.method == 'POST':
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        meal_types = ['Breakfast', 'Lunch', 'Dinner']
        for day in days:
            for meal_type in meal_types:
                meal_key = f"{day}_{meal_type.lower()}"
                items_text = request.POST.get(meal_key, "")
                items_list = items_text.splitlines() if items_text else []
                print(f"Day: {day}, Meal: {meal_type}, Key: {meal_key}, Items: {items_list}")
                try:
                    obj, created = MessMenu.objects.update_or_create(
                        hostel_id=mess_incharge.hostel,
                        day_of_week=day,
                        meal_type=meal_type,
                        defaults={
                            'items': items_list,
                            'created_by': request.user,
                        }
                    )
                    print(f"Updated/Created record for {day} {meal_type}: {'Created' if created else 'Updated'}")
                except Exception as e:
                    print(f"Error saving record for {day} {meal_type}: {str(e)}")
        messages.success(request, 'Mess menu updated successfully.')
        return redirect('messincharge:mess_menu')
    
    # For GET request, fetch existing menu data
    menu_data = {}
    menus = MessMenu.objects.filter(hostel_id=mess_incharge.hostel)
    
    for menu in menus:
        if menu.day_of_week not in menu_data:
            menu_data[menu.day_of_week] = {}
        menu_data[menu.day_of_week][menu.meal_type.lower()] = "\n".join(menu.items) if menu.items else ""
    
    # Prepare a list of days with menu data for easier template access
    days_with_data = []
    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
        day_data = {
            'name': day,
            'breakfast': menu_data.get(day, {}).get('breakfast', ''),
            'lunch': menu_data.get(day, {}).get('lunch', ''),
            'dinner': menu_data.get(day, {}).get('dinner', '')
        }
        days_with_data.append(day_data)
    
    context = {
        'days_with_data': days_with_data,
        'current_date': datetime.now().date(),
    }
    return render(request, 'messincharge/mess_menu.html', context)

def add_expenses(request):
    if not request.user.is_authenticated:
        messages.error(request, 'You must be logged in to access this page.')
        return redirect('messincharge:mess_incharge_login')
    
    try:
        mess_incharge = MessIncharge.objects.get(user=request.user)
    except MessIncharge.DoesNotExist:
        messages.error(request, 'You are not registered as a Mess Incharge.')
        return redirect('messincharge:mess_incharge_login')
    
    from datetime import datetime
    
    if request.method == 'POST':
        description = request.POST.get('description', '')
        amount = request.POST.get('amount', '')
        date_incurred = request.POST.get('date_incurred', '')
        receipt = request.FILES.get('receipt', None)
        
        try:
            amount = float(amount)
            date_incurred = datetime.strptime(date_incurred, '%Y-%m-%d').date() if date_incurred else datetime.now().date()
            expense = Expenses(
                hostel_id=mess_incharge.hostel,
                description=description,
                amount=amount,
                date_incurred=date_incurred,
                created_by=request.user,
            )
            if receipt:
                expense.receipt = receipt
            expense.save()
            messages.success(request, 'Expense added successfully.')
            return redirect('messincharge:add_expenses')
        except ValueError as e:
            messages.error(request, 'Invalid input. Please ensure amount is a number and date is in correct format.')
        except Exception as e:
            messages.error(request, f'Error adding expense: {str(e)}')
    
    # Fetch expenses added by the current user
    expenses = Expenses.objects.filter(hostel_id=mess_incharge.hostel, created_by=request.user).order_by('-created_at')
    
    context = {
        'expenses': expenses,
        'current_date': datetime.now().date(),
    }
    return render(request, 'messincharge/add_expenses.html', context)

def settings(request):
    if not request.user.is_authenticated:
        messages.error(request, 'You must be logged in to access this page.')
        return redirect('messincharge:mess_incharge_login')
    
    try:
        mess_incharge = MessIncharge.objects.get(user=request.user)
    except MessIncharge.DoesNotExist:
        messages.error(request, 'You are not registered as a Mess Incharge.')
        return redirect('messincharge:mess_incharge_login')
    
    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'update_password':
            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')
            
            try:
                user = request.user
                if not user.check_password(current_password):
                    messages.error(request, 'Current password is incorrect.')
                elif new_password != confirm_password:
                    messages.error(request, 'New passwords do not match.')
                elif len(new_password) < 8:
                    messages.error(request, 'New password must be at least 8 characters long.')
                else:
                    user.set_password(new_password)
                    user.save()
                    messages.success(request, 'Password updated successfully. Please log in again.')
                    return redirect('messincharge:mess_incharge_logout')
            except Exception as e:
                messages.error(request, f'Error updating password: {str(e)}')
        elif action == 'update_profile':
            first_name = request.POST.get('first_name', '')
            last_name = request.POST.get('last_name', '')
            email = request.POST.get('email', '')
            phone_number = request.POST.get('phone_number', '')
            cnic = request.POST.get('cnic', '')
            gender = request.POST.get('gender', '')
            street = request.POST.get('street', '')
            area = request.POST.get('area', '')
            city = request.POST.get('city', '')
            district = request.POST.get('district', '')
            
            try:
                # Update user profile information
                user = request.user
                user.first_name = first_name
                user.last_name = last_name
                user.email = email
                user.save()
                
                # Update mess incharge profile with relevant fields
                mess_incharge.contact_number = phone_number
                mess_incharge.cnic = cnic
                mess_incharge.gender = gender
                mess_incharge.street = street
                mess_incharge.area = area
                mess_incharge.city = city
                mess_incharge.district = district
                mess_incharge.save()
                
                messages.success(request, 'Profile updated successfully.')
                return redirect('messincharge:settings')
            except Exception as e:
                messages.error(request, f'Error updating profile: {str(e)}')
                print(f"Error updating profile: {str(e)}")
    
    # Ensure the mess_incharge object is refreshed from the database before rendering
    mess_incharge.refresh_from_db()
    context = {
        'user': request.user,
        'mess_incharge': mess_incharge,
    }
    return render(request, 'messincharge/settings.html', context)

def manage_students(request):
    if not request.user.is_authenticated:
        messages.error(request, 'You must be logged in to access this page.')
        return redirect('messincharge:mess_incharge_login')
    
    try:
        mess_incharge = MessIncharge.objects.get(user=request.user)
    except MessIncharge.DoesNotExist:
        messages.error(request, 'You are not registered as a Mess Incharge.')
        return redirect('messincharge:mess_incharge_login')
    
    from coustom_admin.models import Student, BookingRequest, RoomAssignment
    from messincharge.models import MessStudent
    from django.db.models import Q
    
    # Initialize search terms from request
    all_search_term = request.GET.get('all_search', '')
    enrolled_search_term = request.GET.get('enrolled_search', '')
    
    # Fetch students with active room assignments in the same hostel as the mess in-charge through BookingRequest
    try:
        if mess_incharge.hostel:
            # Get BookingRequests with active RoomAssignments for the hostel
            booking_requests = BookingRequest.objects.filter(
                hostel=mess_incharge.hostel,
                status='Approved'
            ).exclude(
                room_assignment__isnull=True
            ).filter(
                room_assignment__is_active=True,
                room_assignment__room__hostel=mess_incharge.hostel
            ).select_related('student', 'room_assignment__room', 'hostel')
            student_user_ids = booking_requests.values_list('student_id', flat=True)
            print(f"Hostel: {mess_incharge.hostel.name}, Booking Requests with Active Assignments: {booking_requests.count()}, Student User IDs: {list(student_user_ids)}")
            
            # Filter students based on search term for all students
            students = Student.objects.filter(user_id__in=student_user_ids).select_related('user')
            if all_search_term:
                students = students.filter(
                    Q(user__first_name__icontains=all_search_term) |
                    Q(user__last_name__icontains=all_search_term) |
                    Q(user__email__icontains=all_search_term) |
                    Q(contact_number__icontains=all_search_term)
                )
            print(f"Total Students with Active Room Assignments: {students.count()}")
            
            # Prepare student data with additional details from BookingRequest and RoomAssignment
            student_data = []
            for student in students:
                booking = next((br for br in booking_requests if br.student_id == student.user_id), None)
                room = booking.room_assignment.room if booking and booking.room_assignment else None
                student_data.append({
                    'id': student.id,
                    'user': student.user,
                    'contact_number': student.contact_number,
                    'hostel': booking.hostel if booking else None,
                    'room_number': room.room_number if room else 'N/A',
                })
        else:
            print("No hostel assigned to this mess incharge.")
            messages.error(request, 'No hostel assigned to your profile. Please contact support.')
            students = Student.objects.none()
            student_data = []
            student_ids = []
    except Exception as e:
        print(f"Error fetching student assignments: {str(e)}")
        messages.error(request, 'Error fetching student assignments. Please contact support.')
        students = Student.objects.none()
        student_data = []
        student_ids = []
    
    # Fetch students already enrolled for mess
    mess_student_ids = MessStudent.objects.filter(hostel=mess_incharge.hostel, is_active=True).values_list('student_id', flat=True)
    enrolled_students = Student.objects.filter(id__in=mess_student_ids).select_related('user')
    if enrolled_search_term:
        enrolled_students = enrolled_students.filter(
            Q(user__first_name__icontains=enrolled_search_term) |
            Q(user__last_name__icontains=enrolled_search_term) |
            Q(user__email__icontains=enrolled_search_term) |
            Q(contact_number__icontains=enrolled_search_term)
        )
    print(f"Total Enrolled Students for Mess: {enrolled_students.count()}")
    
    # Prepare enrolled student data with additional details
    enrolled_student_data = []
    for student in enrolled_students:
        booking = next((br for br in booking_requests if br.student_id == student.user_id), None)
        room = booking.room_assignment.room if booking and booking.room_assignment else None
        enrolled_student_data.append({
            'id': student.id,
            'user': student.user,
            'contact_number': student.contact_number,
            'hostel': booking.hostel if booking else None,
            'room_number': room.room_number if room else 'N/A',
        })
    
    context = {
        'students': student_data,
        'enrolled_students': enrolled_student_data,
        'all_search_term': all_search_term,
        'enrolled_search_term': enrolled_search_term,
    }
    return render(request, 'messincharge/manage_students.html', context)

def add_mess_student(request):
    if not request.user.is_authenticated:
        messages.error(request, 'You must be logged in to access this page.')
        return redirect('messincharge:mess_incharge_login')
    
    try:
        mess_incharge = MessIncharge.objects.get(user=request.user)
    except MessIncharge.DoesNotExist:
        messages.error(request, 'You are not registered as a Mess Incharge.')
        return redirect('messincharge:mess_incharge_login')
    
    from coustom_admin.models import Student, BookingRequest
    from messincharge.models import MessStudent
    
    if request.method == 'POST':
        student_id = request.POST.get('student_id', '')
        action = request.POST.get('action', '')
        
        try:
            student = Student.objects.get(id=student_id)
            if action == 'add':
                mess_student, created = MessStudent.objects.get_or_create(
                    student=student,
                    hostel=mess_incharge.hostel,
                    defaults={
                        'enrolled_by': request.user,
                        'is_active': True,
                    }
                )
                if created:
                    messages.success(request, f'Student {student.user.get_full_name()} successfully enrolled for mess.')
                else:
                    if not mess_student.is_active:
                        mess_student.is_active = True
                        mess_student.enrolled_by = request.user
                        mess_student.save()
                        messages.success(request, f'Student {student.user.get_full_name()} re-enrolled for mess.')
                    else:
                        messages.info(request, f'Student {student.user.get_full_name()} is already enrolled for mess.')
            elif action == 'remove':
                try:
                    mess_student = MessStudent.objects.get(student=student, hostel=mess_incharge.hostel)
                    mess_student.is_active = False
                    mess_student.save()
                    messages.success(request, f'Student {student.user.get_full_name()} removed from mess enrollment.')
                except MessStudent.DoesNotExist:
                    messages.error(request, f'Student {student.user.get_full_name()} is not enrolled for mess.')
            return redirect('messincharge:manage_students')
        except Student.DoesNotExist:
            messages.error(request, 'Invalid student selected.')
        except Exception as e:
            messages.error(request, f'Error processing request: {str(e)}')
        return redirect('messincharge:manage_students')
    
    # This view might not need a separate template if integrated into manage_students
    return redirect('messincharge:manage_students')
