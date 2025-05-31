from django.shortcuts import render

# Create your views here.
def index(request):
    return render(request, 'index.html')

def aboutus(request):
    return render(request, 'aboutus.html')

def contactus(request):
    return render(request, 'contact us.html')

def ourhostels(request):
    return render(request, 'FEhostels.html')

def applynow(request):
    return render(request, 'apply.html')




