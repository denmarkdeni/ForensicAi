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
import tensorflow as tf
from pdf2image import convert_from_path
import speech_recognition as sr
import pytesseract  
from pydub import AudioSegment
from .ai_analysis import process_image,process_video

def index(request):
    return render(request,'index1.html')

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
            return redirect('dashboard')
            
        else:
            messages.error(request, 'Invalid username or password')
    return render(request,'signin.html')

def dashboard(request):
    return render(request, 'dashboard.html')

def Logout(request):
    logout(request)
    messages.success(request, 'Logged Out successfully!')
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
                investigator=assigned_to
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

def convert_to_wav(audio_path):
    """Convert MP3 to WAV format for speech recognition"""
    audio = AudioSegment.from_file(audio_path, format="mp3")
    wav_path = audio_path.replace(".mp3", ".wav")  # Save as WAV
    audio.export(wav_path, format="wav")
    return wav_path

def process_audio(audio_path):
    """Performs speech-to-text analysis on audio evidence."""
    # Convert if it's an MP3 file
    if audio_path.endswith(".mp3"):
        audio_path = convert_to_wav(audio_path)
    
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio)
        ai_results = {"message": "Audio transcript", "transcript": text}
        confidence = 0.8
    except sr.UnknownValueError:
        ai_results = {"error": "Could not transcribe"}
        confidence = 0.0
    except Exception as e:
        ai_results = {"error": str(e)}
        confidence = 0.0
    
    # Optional: Remove the converted WAV file
    if audio_path.endswith(".wav") and "preview" in audio_path:
        os.remove(audio_path)
    
    return ai_results, confidence


POPPLER_PATH = r"C:\poppler-24.08.0\Library\bin"

def process_document(doc_path):
    """Extracts text from documents using OCR."""

    images = convert_from_path(doc_path, poppler_path=POPPLER_PATH)
    text_results = []

    for i, image in enumerate(images):
        text = pytesseract.image_to_string(image)  # Run OCR on each page
        text_results.append(text)
    texts = " ".join(text_results)
    ai_results = {"message": "Extracted text", "text": texts}
    confidence = 0.75
    return ai_results, confidence

