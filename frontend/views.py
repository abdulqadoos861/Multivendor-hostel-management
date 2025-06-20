from django.shortcuts import render
from coustom_admin.models import Hostels, Rooms, RoomTypeRate
from django.db.models import Sum, Min, Max

# Create your views here.
def index(request):
    hostels = Hostels.objects.all()
    hostel_data = []
    for hostel in hostels:
        rooms = Rooms.objects.filter(hostel=hostel)
        total_capacity = rooms.aggregate(Sum('capacity'))['capacity__sum'] or 0
        hostel_data.append({
            'hostel': hostel,
            'total_capacity': total_capacity,
        })
    # Sort by total capacity and take top 3
    top_hostels = sorted(hostel_data, key=lambda x: x['total_capacity'], reverse=True)[:3]
    return render(request, 'index.html', {'top_hostels': top_hostels})

def aboutus(request):
    return render(request, 'aboutus.html')

def contactus(request):
    return render(request, 'contact us.html')

def ourhostels(request):
    hostels = Hostels.objects.all()
    hostel_data = []
    for hostel in hostels:
        rooms = Rooms.objects.filter(hostel=hostel)
        total_capacity = rooms.aggregate(Sum('capacity'))['capacity__sum'] or 0
        current_occupants = rooms.aggregate(Sum('current_occupants'))['current_occupants__sum'] or 0
        remaining_capacity = total_capacity - current_occupants
        
        # Fetch room rent data
        room_rates = RoomTypeRate.objects.filter(hostel=hostel)
        rent_data = room_rates.values('room_type', 'per_head_rent')
        rent_range = room_rates.aggregate(min_rent=Min('per_head_rent'), max_rent=Max('per_head_rent'))
        
        hostel_data.append({
            'hostel': hostel,
            'total_capacity': total_capacity,
            'remaining_capacity': remaining_capacity,
            'rent_data': list(rent_data),
            'rent_range': rent_range,
        })
    return render(request, 'FEhostels.html', {'hostel_data': hostel_data})

def register(request):
    from coustom_admin.models import Student
    from django.contrib.auth.models import User
    from django.contrib.auth import authenticate, login
    from django.shortcuts import redirect
    from django.contrib import messages

    if request.method == 'POST':
        # Extract form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        contact_number = request.POST.get('contact_number')
        cnic = request.POST.get('cnic')
        gender = request.POST.get('gender')
        institute = request.POST.get('institute')
        street = request.POST.get('street')
        area = request.POST.get('area')
        city = request.POST.get('city')
        district = request.POST.get('district')
        guardian_name = request.POST.get('guardian_name')
        guardian_contact = request.POST.get('guardian_contact')
        guardian_cnic = request.POST.get('guardian_cnic')
        guardian_relation = request.POST.get('guardian_relation')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Validate required fields
        if not all([first_name, last_name, contact_number, cnic, gender, institute, email, username, password]):
            messages.error(request, "All required fields must be filled.")
            return render(request, 'register.html')

        # Check if username or email already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return render(request, 'register.html')
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return render(request, 'register.html')

        try:
            # Create a new user
            user = User.objects.create_user(username=username, email=email, password=password, first_name=first_name, last_name=last_name)
            
            # Create a new student record linked to the user
            student = Student.objects.create(
                user=user,
                contact_number=contact_number,
                cnic=cnic,
                gender=gender,
                institute=institute,
                street=street,
                area=area,
                city=city,
                district=district,
                guardian_name=guardian_name,
                guardian_contact=guardian_contact,
                guardian_cnic=guardian_cnic,
                guardian_relation=guardian_relation
            )
            
            # Log the user in after successful registration
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "Registration successful! You are now logged in.")
                return redirect('student_dashboard')  # Redirect to student dashboard or another page
            else:
                messages.error(request, "Authentication failed after registration.")
                return render(request, 'register.html')
                
        except Exception as e:
            messages.error(request, f"Registration failed: {str(e)}")
            return render(request, 'register.html')
            
    return render(request, 'register.html')
