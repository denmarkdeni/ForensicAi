from django.shortcuts import render, redirect, get_object_or_404
from .models import UserInfo, Case, Evidence, AIAnalysis
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json, cv2, os, base64, logging
from deepface import DeepFace
import numpy as np
from .ai_analysis import process_image, process_video, process_audio, process_document

def index(request):
    return render(request,'index.html')

def register(request):
    if request.method == 'POST':
        
        fullname = request.POST['fullname']
        email = request.POST['email']
        username = request.POST['username']
        password = request.POST['password']
        user_role = request.POST['role']

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('register')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return redirect('register')
        
        user = User.objects.create_user(username=username, email=email, password=password)

        UserInfo.objects.create(user=user, fullname=fullname, userRole=user_role)

        messages.success(request, 'Your account has been created successfully!')
        return redirect('login')
    return render(request,'signup.html')

def Login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Signed In successfully!')
            return redirect('admin_dashboard')
            
        else:
            messages.error(request, 'Invalid username or password')
    return render(request,'signin.html')

def admin_dashboard(request):
    users_count = UserInfo.objects.all().count()
    cases_count = Case.objects.all().count()
    pending_cases = Case.objects.filter(status='In Progress').count()
    solved_cases = Case.objects.filter(status='Closed').count()
    return render(request, 'admin_dashboard.html', {'users_count': users_count, 'cases_count': cases_count, 'pending_cases': pending_cases, 'solved_cases': solved_cases})

def admin_user_manage(request):
    users = User.objects.filter(is_superuser=False)
    users_count = UserInfo.objects.all().count()
    investigators_count = UserInfo.objects.filter(userRole='investigator').count()
    analysts_count = UserInfo.objects.filter(userRole='analyst').count()
    system_user_count = UserInfo.objects.filter(userRole='system_user').count()
    return render(request, 'admin_user_manage.html', {'users': users, 'users_count': users_count, 'investigators_count': investigators_count, 'analysts_count': analysts_count, 'system_user_count': system_user_count})

def admin_case_manage(request):
    cases = Case.objects.all()
    investigators = UserInfo.objects.filter(userRole='investigator')
    total_cases = Case.objects.all().count()
    open_cases = Case.objects.filter(status='Open').count()
    in_progress_cases = Case.objects.filter(status='In Progress').count()
    closed_cases = Case.objects.filter(status='Closed').count()
    return render(request, 'admin_case_manage.html', {'cases': cases, 'investigators': investigators, 'total_cases': total_cases, 'open_cases': open_cases, 'in_progress_cases': in_progress_cases, 'closed_cases': closed_cases})

def Logout(request):
    logout(request)
    messages.success(request, 'Logged Out successfully!')
    return redirect('login')

def add_user(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            username = data.get("username")
            email = data.get("email")
            role = data.get("role")
            password = data.get("password")

            if User.objects.filter(username=username).exists():
                return JsonResponse({"success": False, "error": "Username already exists."}, status=400)

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            UserInfo.objects.create(user=user, userRole=role)

            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    return JsonResponse({"success": False, "error": "Invalid request"}, status=400)

def update_user(request, user_id):
    if request.method == "POST":
        data = json.loads(request.body)
        try:
            user = User.objects.get(id=user_id)
            user.username = data["username"]
            user.email = data["email"]
            user.userinfo.userRole = data["role"]
            user.save()
            return JsonResponse({"success": True})
        except User.DoesNotExist:
            return JsonResponse({"success": False, "error": "User not found"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
        
def delete_user(request, user_id):
    if request.method == "POST":
        try:
            user = User.objects.get(id=user_id)
            user.delete()
            return JsonResponse({"success": True})
        except User.DoesNotExist:
            return JsonResponse({"success": False, "error": "User not found"})

def create_case(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            case_id = data.get("case_id")
            case_name = data.get("case_name")
            assigned_to_id = data.get("assigned_to")
            description = data.get("description")

            if not (case_id and case_name and assigned_to_id and description):
                return JsonResponse({"success": False, "message": "All fields are required!"}, status=400)

            assigned_to = User.objects.get(id=assigned_to_id)  # Fetch investigator
            new_case = Case(case_id=case_id, title=case_name, investigator=assigned_to, description=description, created_by=request.user)
            new_case.save()

            return JsonResponse({"success": True, "message": "Case created successfully!"})
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)
    return JsonResponse({"success": False, "message": "Invalid request"}, status=400)

def view_case_details(request, case_id):
    case = Case.objects.get(case_id=case_id)
    analysts = UserInfo.objects.filter(userRole='analyst')
    return render(request, 'case_details.html', {'case': case, 'analysts': analysts})

def update_case(request, case_id):
    if request.method == "POST":
        try:
            case = Case.objects.get(id=case_id)
            data = json.loads(request.body)

            case.title = data.get("case_name", case.title)
            case.description = data.get("description", case.description)
            case.status = data.get("status", case.status)
            case.analyst = data.get("analyst_id", case.analyst)

            case.save()
            return JsonResponse({"success": True, "message": "Case updated successfully!"})
        except Case.DoesNotExist:
            return JsonResponse({"success": False, "message": "Case not found"}, status=404)
    return JsonResponse({"success": False, "message": "Invalid request"}, status=400)

def delete_case(request, case_id):
    if request.method == "DELETE":
        try:
            case = Case.objects.get(id=case_id)
            case.delete()
            return JsonResponse({"success": True, "message": "Case deleted successfully!"})
        except Case.DoesNotExist:
            return JsonResponse({"success": False, "message": "Case not found"}, status=404)
    return JsonResponse({"success": False, "message": "Invalid request"}, status=400)

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
        # fs = FileSystemStorage()
        # filename = fs.save(f"evidence/{file.name}", file)
        # file_url = fs.url(filename)

        case = Case.objects.get(case_id=case_id)

        evidence = Evidence.objects.create(
            case=case,
            uploaded_by=request.user,
            file=file,
            file_type=evidence_type,
            description=tags
        )
        case.status = "In Progress"
        case.save()
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

def live_emotion(request):
    return render(request,'live_emotion.html')

@csrf_exempt
def detect_emotion(request):
    if request.method == "POST":
        data = json.loads(request.body)
        image_data = data.get("image", "")

        # Decode Base64 image
        image_data = image_data.split(",")[1]
        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Perform Emotion Detection
        result = DeepFace.analyze(img, actions=["emotion"], enforce_detection=False)
        emotion = result[0]["dominant_emotion"]

        return JsonResponse({"emotion": emotion})

    return JsonResponse({"error": "Invalid request"}, status=400)

def ai_analysis_dashboard(request):
    """Shows all cases with 'View Evidence' buttons."""
    cases = Case.objects.all()
    return render(request, "ai_analysis_dashboard.html", {"cases": cases})

def case_evidences(request, case_id):
    """Shows all evidence for a specific case with 'Analyze' buttons."""
    case = get_object_or_404(Case, case_id=case_id)
    evidences = case.evidences.all()  # Fetch all related evidence
    return render(request, "case_evidences.html", {"case": case, "evidences": evidences})

def analyze_evidence(request, evidence_id):
    """Perform AI analysis based on file type (image, video, audio, doc)."""
    evidence = get_object_or_404(Evidence, id=evidence_id)

    # Check if AIAnalysis already exists for this evidence
    ai_analysis, created = AIAnalysis.objects.get_or_create(evidence=evidence)

    if not ai_analysis.analyzed_by_ai:
        # Perform AI analysis based on file type
        if "image" in evidence.file_type:
            ai_results, confidence = process_image(evidence.file.path)
        elif "video" in evidence.file_type:
            ai_results, confidence = process_video(evidence.file.path)
        elif "audio" in evidence.file_type:
            ai_results, confidence = process_audio(evidence.file.path)
        elif "document" in evidence.file_type:
            ai_results, confidence = process_document(evidence.file.path)
        else:
            ai_results, confidence = {"error": "Unsupported file type"}, 0.0

        # Save AI results
        ai_analysis.ai_results = ai_results
        ai_analysis.confidence_score = confidence
        ai_analysis.analyzed_by_ai = True
        ai_analysis.evidence.status = "reviewed"
        ai_analysis.save()
        ai_analysis.evidence.save()

    return render(request, "ai_analysis_results.html", {"evidence": evidence, "ai_analysis": ai_analysis})



