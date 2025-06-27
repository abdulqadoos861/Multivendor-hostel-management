from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from coustom_admin.models import Student  # Correct model location

@csrf_exempt
def student_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # Check if the user is associated with a student record using user_id
            try:
                student = Student.objects.get(user_id=user.id)
                return redirect('student_dashboard')
            except Student.DoesNotExist:
                logout(request)
                messages.error(request, "Access denied. This portal is for students only.")
                return render(request, 'student_login.html', {'error': 'Access denied'})
        else:
            messages.error(request, "Invalid username or password.")
            return render(request, 'student_login.html', {'error': 'Invalid credentials'})
    return render(request, 'student_login.html')

def student_dashboard(request):
    if not request.user.is_authenticated:
        return redirect('student_login')
    # Additional check to ensure the user is a student using user_id
    try:
        student = Student.objects.get(user_id=request.user.id)
        from coustom_admin.models import BookingRequest, RoomAssignment
        from messincharge.models import MessStudent
        
        # Get active booking and room assignment information
        active_booking = BookingRequest.objects.filter(
            student=request.user,
            status='Approved'
        ).first()
        
        room_info = None
        if active_booking:
            assignment = RoomAssignment.objects.filter(
                booking=active_booking,
                is_active=True
            ).select_related('room__hostel').first()
            if assignment and assignment.room:
                room_info = {
                    'hostel': assignment.room.hostel.name if assignment.room.hostel else 'N/A',
                    'room_number': assignment.room.room_number if assignment.room.room_number else 'N/A',
                    'floor': getattr(assignment.room, 'floor_number', 'N/A')
                }
        
        # Get mess enrollment information
        mess_enrollment = MessStudent.objects.filter(student=student, is_active=True).first()
        mess_info = None
        if mess_enrollment:
            mess_info = {
                'enrolled': True,
                'hostel': mess_enrollment.hostel.name if mess_enrollment.hostel else 'N/A',
                'status': 'Active' if mess_enrollment.is_active else 'Inactive'
            }
        else:
            mess_info = {
                'enrolled': False,
                'hostel': 'N/A',
                'status': 'Not Enrolled'
            }
        
        return render(request, 'student_dashboard.html', {
            'student': student,
            'room_info': room_info,
            'mess_info': mess_info
        })
    except Student.DoesNotExist:
        logout(request)
        messages.error(request, "Access denied. This portal is for students only.")
        return redirect('student_login')

def student_profile(request):
    if not request.user.is_authenticated:
        return redirect('student_login')
    try:
        student = Student.objects.get(user_id=request.user.id)
        if request.method == 'POST':
            form_type = request.POST.get('form_type')
            if form_type == 'personal':
                # Update student details
                student.contact_number = request.POST.get('contact_number')
                student.cnic = request.POST.get('cnic')
                student.street = request.POST.get('street')
                student.area = request.POST.get('area')
                student.city = request.POST.get('city')
                student.district = request.POST.get('district')
                student.gender = request.POST.get('gender')
                student.institute = request.POST.get('institute')
                student.guardian_name = request.POST.get('guardian_name')
                student.guardian_cnic = request.POST.get('guardian_cnic')
                student.guardian_relation = request.POST.get('guardian_relation')
                student.guardian_contact = request.POST.get('guardian_contact')
                student.save()
                
                # Update related User model fields
                user = student.user
                user.first_name = request.POST.get('first_name')
                user.last_name = request.POST.get('last_name')
                user.email = request.POST.get('email')
                user.save()
                
                messages.success(request, "Profile updated successfully.")
            elif form_type == 'password':
                # Handle password change
                current_password = request.POST.get('current_password')
                new_password = request.POST.get('new_password')
                confirm_password = request.POST.get('confirm_password')
                if request.user.check_password(current_password):
                    if new_password == confirm_password:
                        request.user.set_password(new_password)
                        request.user.save()
                        messages.success(request, "Password changed successfully. Please log in again.")
                        logout(request)
                        return redirect('student_login')
                    else:
                        messages.error(request, "New passwords do not match.")
                else:
                    messages.error(request, "Current password is incorrect.")
        
        # Fetch mess enrollment and attendance data
        from messincharge.models import MessStudent, MessAttendance
        from coustom_admin.models import BookingRequest, RoomAssignment
        from datetime import datetime
        
        mess_enrollment = MessStudent.objects.filter(student=student, is_active=True).first()
        mess_attendance = []
        if mess_enrollment:
            mess_attendance = MessAttendance.objects.filter(
                mess_student=mess_enrollment
            ).order_by('-date')[:7]  # Last 7 days of attendance
        
        # Get active booking and room assignment information
        active_booking = BookingRequest.objects.filter(
            student=request.user,
            status='Approved'
        ).first()
        
        room_info = None
        if active_booking:
            assignment = RoomAssignment.objects.filter(
                booking=active_booking,
                is_active=True
            ).select_related('room__hostel').first()
            if assignment and assignment.room:
                room_info = {
                    'hostel': assignment.room.hostel.name if assignment.room.hostel else 'N/A',
                    'room_number': assignment.room.room_number if assignment.room.room_number else 'N/A',
                    'floor': getattr(assignment.room, 'floor_number', 'N/A')
                }
        
        return render(request, 'student_profile.html', {
            'student': student,
            'mess_enrollment': mess_enrollment,
            'mess_attendance': mess_attendance,
            'room_info': room_info
        })
    except Student.DoesNotExist:
        logout(request)
        messages.error(request, "Access denied. This portal is for students only.")
        return redirect('student_login')

def student_booking(request):
    if not request.user.is_authenticated:
        return redirect('student_login')
    try:
        student = Student.objects.get(user_id=request.user.id)
        from coustom_admin.models import Hostels, BookingRequest
        hostels = Hostels.objects.all()
        bookings = BookingRequest.objects.filter(student=request.user).order_by('-request_date')
        from coustom_admin.models import RoomAssignment
        
        # Check for active room assignment
        has_active_assignment = RoomAssignment.objects.filter(
            booking__student=request.user,
            is_active=True
        ).exists()
        
        # Check for pending room change request if there is an active assignment
        has_pending_room_change = False
        if has_active_assignment:
            active_booking = BookingRequest.objects.filter(
                student=request.user,
                status='Approved'
            ).first()
            if active_booking:
                from student.models import RoomChangeRequest
                has_pending_room_change = RoomChangeRequest.objects.filter(
                    student=request.user,
                    current_booking=active_booking,
                    status='Pending'
                ).exists()
        
        if request.method == 'POST':
            form_type = request.POST.get('form_type')
            if form_type == 'room_change':
                change_hostel_id = request.POST.get('change_hostel')
                change_room_type = request.POST.get('change_room_type')
                reason = request.POST.get('reason')
                
                # Get current active booking
                active_booking = BookingRequest.objects.filter(
                    student=request.user,
                    status='Approved'
                ).first()
                
                if not active_booking:
                    messages.error(request, "No active booking found to request a room change.")
                else:
                    try:
                        new_hostel = None
                        if change_hostel_id:
                            new_hostel = Hostels.objects.get(id=change_hostel_id)
                        # Check for existing pending room change request
                        from student.models import RoomChangeRequest
                        existing_request = RoomChangeRequest.objects.filter(
                            student=request.user,
                            current_booking=active_booking,
                            status='Pending'
                        ).exists()
                        
                        if existing_request:
                            messages.error(request, "You already have a pending room change request for this booking. Please wait for it to be reviewed.")
                            return redirect('student_booking')
                            
                        # Create a new room change request using the separate model
                        room_change = RoomChangeRequest(
                            student=request.user,
                            current_booking=active_booking,
                            requested_hostel=new_hostel,
                            requested_room_type=change_room_type,
                            reason=reason
                        )
                        room_change.save()
                        messages.success(request, "Room change request submitted successfully. It will be reviewed by the administration.")
                        return redirect('student_booking')
                    except Hostels.DoesNotExist:
                        messages.error(request, "Invalid hostel selection for room change.")
                    except Exception as e:
                        messages.error(request, f"Error creating room change request: {str(e)}")
            else:
                hostel_id = request.POST.get('hostel')
                room_type = request.POST.get('room_type')
                check_in_date = request.POST.get('check_in_date')
                check_out_date = request.POST.get('check_out_date') or None
                
                # Check if student already has a pending or approved booking
                existing_booking = BookingRequest.objects.filter(
                    student=request.user,
                    status__in=['Pending', 'Approved']
                ).exists()
                
                if existing_booking:
                    messages.error(request, "You already have a pending or approved booking. You cannot create a new request until the current one is resolved.")
                else:
                    try:
                        hostel = Hostels.objects.get(id=hostel_id)
                        booking = BookingRequest(
                            student=request.user,
                            hostel=hostel,
                            room_type=room_type,
                            check_in_date=check_in_date,
                            check_out_date=check_out_date
                        )
                        booking.save()
                        messages.success(request, "Booking request submitted successfully. It will be reviewed by the administration.")
                        return redirect('student_booking')
                    except Hostels.DoesNotExist:
                        messages.error(request, "Invalid hostel selection.")
                    except Exception as e:
                        messages.error(request, f"Error creating booking request: {str(e)}")
            
        # Fetch room change requests for the current student
        from student.models import RoomChangeRequest
        room_change_requests = RoomChangeRequest.objects.filter(student=request.user).order_by('-request_date')
        
        return render(request, 'student_booking.html', {
            'student': student,
            'hostels': hostels,
            'bookings': bookings,
            'has_active_assignment': has_active_assignment,
            'has_pending_room_change': has_pending_room_change,
            'room_change_requests': room_change_requests
        })
    except Student.DoesNotExist:
        logout(request)
        messages.error(request, "Access denied. This portal is for students only.")
        return redirect('student_login')

def student_complaint(request):
    if not request.user.is_authenticated:
        return redirect('student_login')
    try:
        student = Student.objects.get(user_id=request.user.id)
        from student.models import Complaint
        from coustom_admin.models import BookingRequest, RoomAssignment
        complaints = Complaint.objects.filter(user=request.user).order_by('-created_at')
        
        # Get the student's assigned hostel from active booking
        assigned_hostel = None
        active_booking = BookingRequest.objects.filter(
            student=request.user,
            status='Approved'
        ).first()
        if active_booking:
            try:
                assignment = RoomAssignment.objects.get(
                    booking=active_booking,
                    is_active=True
                )
                assigned_hostel = active_booking.hostel
            except RoomAssignment.DoesNotExist:
                pass
        
        if request.method == 'POST':
            category = request.POST.get('category')
            title = request.POST.get('title')
            description = request.POST.get('description')
            priority = request.POST.get('priority')
            submitted_to = request.POST.get('submitted_to')
            
            try:
                if not assigned_hostel:
                    messages.error(request, "You must have an active hostel assignment to submit a complaint.")
                else:
                    complaint = Complaint(
                        user=request.user,
                        hostel=assigned_hostel,
                        category=category,
                        title=title,
                        description=description,
                        priority=priority,
                        submitted_to=submitted_to
                    )
                    complaint.save()
                    messages.success(request, "Complaint submitted successfully. It will be reviewed by the administration.")
                    return redirect('student_complaint')
            except Exception as e:
                messages.error(request, f"Error submitting complaint: {str(e)}")
        
        return render(request, 'student_complaint.html', {
            'student': student,
            'complaints': complaints,
            'assigned_hostel': assigned_hostel
        })
    except Student.DoesNotExist:
        logout(request)
        messages.error(request, "Access denied. This portal is for students only.")
        return redirect('student_login')

def student_feedback(request):
    if not request.user.is_authenticated:
        return redirect('student_login')
    try:
        student = Student.objects.get(user_id=request.user.id)
        from coustom_admin.models import BookingRequest, RoomAssignment
        from student.models import Feedback
        
        # Get the student's assigned hostel from active booking
        assigned_hostel = None
        active_booking = BookingRequest.objects.filter(
            student=request.user,
            status='Approved'
        ).first()
        if active_booking:
            try:
                assignment = RoomAssignment.objects.get(
                    booking=active_booking,
                    is_active=True
                )
                assigned_hostel = active_booking.hostel
            except RoomAssignment.DoesNotExist:
                pass
        
        # Retrieve previous feedback for the current user
        feedback_list = Feedback.objects.filter(user=request.user).order_by('-created_at')
        
        if request.method == 'POST':
            feedback_text = request.POST.get('feedback_text')
            rating = request.POST.get('rating')
            
            try:
                if not assigned_hostel:
                    messages.error(request, "You must have an active hostel assignment to submit feedback.")
                else:
                    feedback = Feedback(
                        user=request.user,
                        hostel=assigned_hostel,
                        feedback_text=feedback_text,
                        rating=int(rating) if rating else 3
                    )
                    feedback.save()
                    messages.success(request, "Feedback submitted successfully. Thank you for your input.")
                    return redirect('student_feedback')
            except Exception as e:
                messages.error(request, f"Error submitting feedback: {str(e)}")
        
        return render(request, 'student_feedback.html', {
            'student': student,
            'feedback_list': feedback_list,
            'assigned_hostel': assigned_hostel
        })
    except Student.DoesNotExist:
        logout(request)
        messages.error(request, "Access denied. This portal is for students only.")
        return redirect('student_login')

def student_fee_details(request):
    if not request.user.is_authenticated:
        return redirect('student_login')
    try:
        student = Student.objects.get(user_id=request.user.id)
        from coustom_admin.models import StudentMonthlyFee
        
        # Fetch fee details for the student, ordered by year and month descending
        fee_records = StudentMonthlyFee.objects.filter(student=student).order_by('-year', '-month')
        
        return render(request, 'student_fee_details.html', {
            'student': student,
            'fee_records': fee_records
        })
    except Student.DoesNotExist:
        logout(request)
        messages.error(request, "Access denied. This portal is for students only.")
        return redirect('student_login')

def student_logout(request):
    logout(request)
    return redirect('student_login')
