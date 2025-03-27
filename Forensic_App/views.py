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
            messages.success(request, f"Welcome 😊, {user.username} , you are logged in successfully!...🤝")
            return redirect('admin_dashboard')
           
        else:
            messages.error(request, 'Invalid username or password')
            redirect('login')
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

def admin_evidence_manage(request):
    cases = Case.objects.all()
    evidences = Evidence.objects.all()
    total_evidences = Evidence.objects.all().count()
    pending_evidences = Evidence.objects.filter(status='pending').count()
    reviewed_evidences = Evidence.objects.filter(status='reviewed').count()
    return render(request, 'admin_evidence_manage.html', {'evidences': evidences, 'total_evidences': total_evidences, 'pending_evidences': pending_evidences, 'reviewed_evidences': reviewed_evidences, 'cases': cases})

def admin_ai_manage(request):
    ai_analyses = AIAnalysis.objects.all()
    return render(request, 'admin_ai_manage.html', {'ai_analyses': ai_analyses})

def admin_report_manage(request):
    cases = Case.objects.all()
    total_cases = Case.objects.all().count()
    total_evidences = Evidence.objects.all().count()    
    total_ai_analyses = AIAnalysis.objects.all().count()
    total_reports = Case.objects.filter(is_reported=True).count()
    pending_reports = Case.objects.filter(is_reported=False).count()
    return render(request, 'admin_report_manage.html', {'total_cases': total_cases, 'total_evidences': total_evidences, 'total_ai_analyses': total_ai_analyses, 'total_reports': total_reports, 'pending_reports': pending_reports, 'cases': cases})

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
    investigators = UserInfo.objects.filter(userRole='investigator')
    return render(request, 'case_details.html', {'case': case, 'analysts': analysts, 'investigators': investigators})

def update_case(request, case_id):
    if request.method == "POST":
        try:
            case = Case.objects.get(case_id=case_id)
            data = json.loads(request.body)

            case.title = data.get("case_name", case.title)
            case.description = data.get("description", case.description)
            case.status = data.get("status", case.status)

            investigator_id = data.get("investigator_id")
            if investigator_id:
                case.investigator = User.objects.get(id=investigator_id)
            else:
                case.investigator = None

            analyst_id = data.get("analyst_id")
            if analyst_id:
                case.analyst = User.objects.get(id=analyst_id)
            else:
                case.analyst = None 

            case.save()
            return JsonResponse({"success": True, "message": "Case updated successfully!"})
        except Case.DoesNotExist:
            return JsonResponse({"success": False, "message": "Case not found"}, status=404)
    return JsonResponse({"success": False, "message": "Invalid request"}, status=400)

def delete_case(request, case_id):
    if request.method == "DELETE":
        try:
            case = Case.objects.get(case_id=case_id)
            case.delete()
            return JsonResponse({"success": True, "message": "Case deleted successfully!"})
        except Case.DoesNotExist:
            return JsonResponse({"success": False, "message": "Case not found"}, status=404)
    return JsonResponse({"success": False, "message": "Invalid request"}, status=400)

def upload_evidence(request):
    if request.method == "POST":
        case_id = request.POST.get("case_id")
        evidence_type = request.POST.get("evidence_type")
        description = request.POST.get("description")
        evidence_file = request.FILES.get("evidence")

        if not case_id or not evidence_file:
            return JsonResponse({"success": False, "error": "Missing required fields."})

        case = get_object_or_404(Case, case_id=case_id)

        # Save the evidence
        Evidence.objects.create(
            case=case,
            file=evidence_file,
            file_type=evidence_type,
            description=description,
            uploaded_by=request.user
        )

        return JsonResponse({"success": True})

    return JsonResponse({"success": False, "error": "Invalid request."})

def update_evidence(request, evidence_id):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            evidence = get_object_or_404(Evidence, id=evidence_id)
            evidence.status = data.get("status", evidence.status)
            evidence.save()
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

def delete_evidence(request, evidence_id):
    if request.method == "DELETE":
        try:
            evidence = get_object_or_404(Evidence, id=evidence_id)
            evidence.delete()
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

def view_evidence_details(request, evidence_id):
    evidence = get_object_or_404(Evidence, id=evidence_id)
    return render(request, "evidence_details.html", {"evidence": evidence})

#-----------------------------------------------------------------------------------------------------------------

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
    return render(request, "ai_analysis_evidences.html", {"case": case, "evidences": evidences})

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

# ------------------------------------->>>> 📌 Case Analysis Report

def get_case_analysis(case_id):
    # Fetch case details
    case = Case.objects.get(case_id=case_id)
    
    # Fetch all evidences related to the case
    evidences = Evidence.objects.filter(case_id=case_id)

    # Fetch all AI analysis results for those evidences
    ai_results = AIAnalysis.objects.filter(evidence__in=evidences)

    return case, evidences, ai_results

from django.http import FileResponse, HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from xml.sax.saxutils import escape
import re , tempfile

def format_ai_analysis(ai_results):
    formatted_results = []
    styles = getSampleStyleSheet()

    for result in ai_results:
        file_type = result.evidence.file_type.lower()
        analysis = result.ai_results  # Dictionary with AI results

        formatted_text = f"<b>{escape(file_type.capitalize())} Analysis:</b><br/>"

        if file_type == "image":
            formatted_text += f"Face Detection: {escape(str(analysis.get('face_detection', {}).get('message', 'No data')))}<br/>"
            formatted_text += f"Objects Detected: {', '.join(analysis.get('object_detection', {}).get('objects', ['None']))}<br/>"
            
            # Extract OCR text safely from nested dictionary
            ocr_data = analysis.get("ocr_text", {})  
            if isinstance(ocr_data, str):
                try:
                    import json
                    ocr_data = json.loads(ocr_data)  # Convert string to dictionary
                except json.JSONDecodeError:
                    ocr_data = {}
            ocr_text = ocr_data.get("ocr_text", "No OCR data") 

            # Extract first line
            first_line = ocr_text.split("\n")[0]

            # Count special characters (excluding spaces and alphanumeric characters)
            special_chars = re.findall(r"[^A-Za-z0-9\s]", first_line)

            # Filter based on conditions
            if len(ocr_text) < 300 and len(special_chars) < 5:
                formatted_text += f"OCR Text: {escape(ocr_text)}<br/>"
            else:
                formatted_text += "OCR Text: No Text found...<br/>"
            
            formatted_text += f"Forgery Detection: {escape(str(analysis.get('forgery_detection', 'No data')))}<br/>"
            metadata = analysis.get("metadata", {})

            if not isinstance(metadata, dict):
                metadata = {}  # If metadata is a string or None, reset it to an empty dict

            formatted_text += f"Metadata: Device: {metadata.get('device', 'Unknown')}, "
            formatted_text += f"Location: {metadata.get('location', 'No GPS')}, "
            formatted_text += f"Date: {metadata.get('date_time', 'Unknown')}<br/>"

        elif file_type == "document":
            extracted_text = analysis.get('text', 'No extracted text available')
            confidence = analysis.get('confidence', 'Unknown')

            formatted_text += f"Extracted Text:<br/>{escape(extracted_text)}<br/>"
            
            formatted_text += f"Confidence Score: {escape(str(confidence))}<br/>"

        elif file_type == "audio":
            formatted_text += f"Transcript:<br/>{escape(analysis.get('transcript', 'No transcript available'))}<br/>"
            formatted_text += f"Suspicious Phrases: {escape(', '.join(analysis.get('suspicious_phrases', ['None'])))}<br/>"
            formatted_text += f"Confidence Score: {escape(str(analysis.get('confidence', 'Unknown')))}<br/>"

        elif file_type == "video":
            formatted_text += f"Alert: {escape(analysis.get('message', 'No alerts detected'))}<br/>"
            formatted_text += f"Suspicious Objects:<br/>"
            for frame, obj in enumerate(analysis.get('objects', []), start=1):
                formatted_text += f"Frame {frame}: {escape(obj)}<br/>"
            
            formatted_text += f"Confidence Score: {escape(str(analysis.get('confidence', 'Unknown')))}<br/>"

        formatted_results.append(Paragraph(formatted_text, styles["BodyText"]))
        formatted_results.append(Spacer(1, 6))

    return formatted_results

def generate_case_report(case_id):
    case, evidences, ai_results = get_case_analysis(case_id)

     # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    file_path = temp_file.name 
    
    # 📝 Create PDF document
    pdf = SimpleDocTemplate(file_path, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # 🎯 **Title**
    title = Paragraph(f"<b>Forensic Case Report</b>", styles["Title"])
    elements.append(title)
    elements.append(Spacer(1, 12))

    # 📝 **Case Details**
    case_info = [
        ["Case ID:", case.case_id],
        ["Case Name:", case.title],
        ["Description:", case.description],
        ["Status:", case.status]
    ]
    case_table = Table(case_info, colWidths=[100, 400])
    case_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
    ]))
    elements.append(case_table)
    elements.append(Spacer(1, 12))

    # 📂 **Evidence List**
    elements.append(Paragraph("<b>Evidence Details:</b>", styles["Heading2"]))
    evidence_data = [["File Type", "File Name"]]
    for evidence in evidences:
        evidence_data.append([evidence.file_type, evidence.file])

    evidence_table = Table(evidence_data, colWidths=[150, 350])
    evidence_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
    ]))
    elements.append(evidence_table)
    elements.append(Spacer(1, 12))

    # 📊 **AI Analysis Results**
    elements.append(Paragraph("<b>AI Analysis:</b>", styles["Heading2"]))
    elements.extend(format_ai_analysis(ai_results))

    # Add Copyright Notice
    copyright_text = Paragraph("<b>Copyright © 2025 Forensic AI. All rights reserved.</b>", styles["BodyText"])
    elements.append(Spacer(1, 12))  
    elements.append(copyright_text)

    # 📝 **Build and Save PDF**
    pdf.build(elements)

    # ✅ Mark the case as reported
    case.is_reported = True
    case.save()

    return file_path

# 🎯 **Django View to Download PDF**
def generate_case_report_view(request, case_id):
    file_path = generate_case_report(case_id)

    # Serve the PDF for download
    response = FileResponse(open(file_path, "rb"), as_attachment=True, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="case_{case_id}_report.pdf"'

    return response

# ----------------------------------------------------------------->>>>>>>>>>>>>>>>>


def investigator_dashboard(request):
    investigator = request.user 

    cases = Case.objects.filter(investigator=investigator)
    total_cases = cases.count()
    open_cases = cases.filter(status="Open").count()
    closed_cases = cases.filter(status="Closed").count()

    # Count evidence for each case
    for case in cases:
        case.evidence_count = Evidence.objects.filter(case=case).count()

    # Get AI analysis related to assigned cases
    evidence = Evidence.objects.filter(case__in=cases)

    context = {
        "cases": cases,
        "total_cases": total_cases,
        "open_cases": open_cases,
        "closed_cases": closed_cases,
        "ai_results": evidence,
    }
    
    return render(request, "investigator_dashboard.html", context)

def analyst_dashboard(request):
    analyst = request.user 

    cases = Case.objects.filter(analyst=analyst)
    total_cases = cases.count()
    open_cases = cases.filter(status="Open").count()
    closed_cases = cases.filter(status="Closed").count()

    # Count evidence for each case
    for case in cases:
        case.evidence_count = Evidence.objects.filter(case=case).count()

    # Get AI analysis related to assigned cases
    evidence = Evidence.objects.filter(case__in=cases)

    context = {
        "cases": cases,
        "total_cases": total_cases,
        "open_cases": open_cases,
        "closed_cases": closed_cases,
        "ai_results": evidence,
    }
    
    return render(request, "analyst_dashboard.html", context)
