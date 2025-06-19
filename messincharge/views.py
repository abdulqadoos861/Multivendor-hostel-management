from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth import logout
from coustom_admin.models import MessIncharge
from messincharge.models import MessMenu , Expenses

def messincharge(request):
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
                return redirect('messincharge:messincharge')  # Redirect to mess in-charge dashboard or index
            except MessIncharge.DoesNotExist:
                messages.error(request, 'You are not registered as a Mess Incharge.')
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
            
            try:
                # Update user profile information
                user = request.user
                user.first_name = first_name
                user.last_name = last_name
                user.email = email
                user.save()
                
                # Update mess incharge phone number if provided
                if phone_number:
                    print(f"Attempting to update phone number to: {phone_number}")
                    mess_incharge.phone_number = phone_number
                    mess_incharge.save()
                    print(f"Phone number updated to: {mess_incharge.phone_number}")
                    messages.success(request, 'Profile and phone number updated successfully.')
                    # Refresh the mess_incharge object from the database to ensure latest data
                    mess_incharge.refresh_from_db()
                else:
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
    
    from coustom_admin.models import Student, BookingRequest
    from messincharge.models import MessStudent
    # Fetch students assigned to the same hostel as the mess in-charge through BookingRequest
    booking_requests = BookingRequest.objects.filter(hostel=mess_incharge.hostel, status='Approved')
    student_ids = booking_requests.values_list('student_id', flat=True)
    students = Student.objects.filter(id__in=student_ids)
    
    # Fetch students already enrolled for mess
    mess_student_ids = MessStudent.objects.filter(hostel=mess_incharge.hostel, is_active=True).values_list('student_id', flat=True)
    enrolled_students = Student.objects.filter(id__in=mess_student_ids)
    
    context = {
        'students': students,
        'enrolled_students': enrolled_students,
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
