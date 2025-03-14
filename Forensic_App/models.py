from django.db import models
from django.contrib.auth.models import User
import os
from django.core.exceptions import ValidationError
from django.conf import settings

class UserInfo(models.Model):
    USER_ROLE_CHOICES = [
        ('investigator', 'Investigator'), # create cases and upload evidence.
        ('analyst', 'Analyst'), # review evidence and verify AI analysis.
        ('admin', 'Admin'), # manages users and assigns roles.
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    fullname = models.CharField(max_length=255)
    userRole = models.CharField(max_length=30, choices=USER_ROLE_CHOICES, default='not specified')

    def __str__(self):
        return f"{self.fullname} ({self.userRole})"

class Case(models.Model):
    case_id = models.CharField(max_length=50, unique=True, primary_key=True)  
    title = models.CharField(max_length=200) 
    description = models.TextField()  
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_cases') 
    investigator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='cases')
    analyst = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_cases') 
    status = models.CharField(max_length=50, default='Open')  # Case status (Open, In Progress, Closed)
    created_at = models.DateTimeField(auto_now_add=True) 
    updated_at = models.DateTimeField(auto_now=True)  
    def __str__(self):
        return self.title

# Evidence model

ALLOWED_FILE_TYPES = [
    ('image', 'Image'),
    ('video', 'Video'),
    ('document', 'Document'),
    ('audio', 'Audio'),
]
STATUS_CHOICES = [
    ("pending", "Pending Review"),
    ("analyzing", "Under AI Analysis"),
    ("reviewed", "Reviewed"),
    ("rejected", "Rejected"),
]

def evidence_upload_path(instance, filename):
    """Generate file path dynamically: evidence/case_<case_id>/<filename>"""
    return f"evidence/case_{instance.case.case_id}/{filename}"

def validate_evidence_file(value):
    """Validate file type based on its extension."""
    ext = os.path.splitext(value.name)[1].lower()
    allowed_extensions = {
        'image': ['.jpg', '.jpeg', '.png', '.gif'],
        'video': ['.mp4', '.avi', '.mov'],
        'document': ['.pdf', '.docx', '.txt'],
        'audio': ['.mp3', '.wav','mpeg'],
    }
    
    file_type = None
    for type_key, extensions in allowed_extensions.items():
        if ext in extensions:
            file_type = type_key
            break

    if not file_type:
        raise ValidationError(f"File type not supported: {ext}")
    
    return file_type

class Evidence(models.Model):
    case = models.ForeignKey("Case", on_delete=models.CASCADE, related_name="evidences")
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to=evidence_upload_path)
    file_type = models.CharField(max_length=10, choices=ALLOWED_FILE_TYPES, blank=True)
    description = models.TextField(blank=True, null=True)
    upload_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="verified_evidences")
    verified_at = models.DateTimeField(blank=True, null=True)
    is_approved = models.BooleanField(default=False)
    remarks = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        """Auto-detect file type before saving."""
        self.file_type = validate_evidence_file(self.file)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Evidence {self.id} - {self.case.case_id} ({self.file_type})"

class AIAnalysis(models.Model):
    evidence = models.OneToOneField("Evidence", on_delete=models.CASCADE, related_name="ai_analysis")
    analyzed_by_ai = models.BooleanField(default=False)  # AI processed this file?
    ai_results = models.JSONField(blank=True, null=True)  # AI-generated insights
    confidence_score = models.FloatField(blank=True, null=True)  # AI's confidence level (0-1)
    
    reviewed_by_analyst = models.BooleanField(default=False)  # Has an analyst verified the AI output?
    analyst = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    analyst_feedback = models.TextField(blank=True, null=True)  # Analyst's manual notes
    is_approved = models.BooleanField(default=False)  # Analyst approves AI findings?
    
    created_at = models.DateTimeField(auto_now_add=True)  # When AI analysis happened
    reviewed_at = models.DateTimeField(blank=True, null=True)  # When analyst reviewed

    def __str__(self):
        return f"AI Analysis for Evidence {self.evidence.id} (Approved: {self.is_approved})"

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='messages')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.sender.username} to {self.receiver.username} on Case {self.case.case_id}"
