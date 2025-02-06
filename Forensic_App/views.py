from django.shortcuts import render, redirect
from .models import UserInfo, Case, Evidence
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json, cv2, os
from deepface import DeepFace
import tensorflow as tf


os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"  # Disable oneDNN logs
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"   # Suppress TensorFlow warnings

def index(request):
    return render(request,'index.html')

def register(request):
    if request.method == 'POST':
        
        fullname = request.POST['name']
        email = request.POST['email']
        username = request.POST['username']
        password = request.POST['password']
        user_role = request.POST['role']

        user = User.objects.create_user(username=username, email=email, password=password)

        UserInfo.objects.create(user=user, fullname=fullname, userRole=user_role)

        messages.success(request, 'Your account has been created successfully!')
        return redirect('login')
    return render(request,'register.html')

def Login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
            
        else:
            messages.error(request, 'Invalid username or password')
    return render(request,'login.html')

def dashboard(request):
    return render(request, 'dashboard.html')

def Logout(request):
    logout(request)
    return redirect('login')

def create_case(request):
    if request.method == 'POST':
        # Extract data from the form
        case_id = request.POST.get('case_id')
        title = request.POST.get('title')
        description = request.POST.get('description')
        assigned_to_id = request.POST.get('assigned_to')

        if case_id and title and description and assigned_to_id:
            assigned_to = User.objects.get(id=assigned_to_id)
            case = Case(
                case_id=case_id,
                title=title,
                description=description,
                created_by=request.user, 
                assigned_to=assigned_to
            )
            case.save()
            return redirect('case_list')  
        else:
            return render(request, 'create_case.html', {'error': 'Please fill out all fields.'})
    
    users = User.objects.all()
    return render(request, 'create_case.html', {'users': users})

def case_list(request):
    cases = Case.objects.all()
    return render(request, 'case_list.html',{'cases':cases})

@login_required
def evidence_list(request):
    evidence_items = Evidence.objects.all()
    return render(request, 'evidence_list.html', {'evidence_items': evidence_items})

@login_required
def upload_evidence(request):
    if request.method == "POST":
        case_id = request.POST.get("case_id")
        evidence_type = request.POST.get("evidence_type")
        location = request.POST.get("location")
        tags = request.POST.get("tags")
        file = request.FILES["file"]

        # Save file manually
        fs = FileSystemStorage()
        filename = fs.save(f"evidence/{file.name}", file)
        file_url = fs.url(filename)

        case = Case.objects.get(case_id=case_id)

        evidence = Evidence.objects.create(
            case=case,
            technician=request.user,
            file=file,
            evidence_type=evidence_type,
            location=location,
            tags=tags,
        )
        return redirect("evidence_list")

    cases = Case.objects.all()
    return render(request, "upload_evidence.html", {"cases": cases})

def evidence_review(request):
    evidences = Evidence.objects.all()
    return render(request, 'evidence_review.html', {'evidences': evidences})

@csrf_exempt
def update_evidence(request, evidence_id):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            evidence = Evidence.objects.get(id=evidence_id)
            evidence.status = data.get("status", evidence.status)
            evidence.save()
            return JsonResponse({"success": True, "status": evidence.status})
        except Evidence.DoesNotExist:
            return JsonResponse({"success": False, "error": "Evidence not found"}, status=404)
    return JsonResponse({"success": False, "error": "Invalid request"}, status=400)

