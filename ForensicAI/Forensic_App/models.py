from django.db import models
from django.contrib.auth.models import User

class UserInfo(models.Model):
    USER_ROLE_CHOICES = [
        ('forensic_investigator', 'Forensic Investigator'),
        ('evidence_technician', 'Evidence Technician'),
        ('legal_officer', 'Legal Officer'),
        ('supervisor', 'Supervisor'),
        ('external_auditor', 'External Auditor'),
        ('system_user', 'System User'),
        ('admin', 'Admin'),
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
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_cases') 
    status = models.CharField(max_length=50, default='Open')  # Case status (Open, In Progress, Closed)
    created_at = models.DateTimeField(auto_now_add=True) 
    updated_at = models.DateTimeField(auto_now=True)  
    def __str__(self):
        return self.title
    
class Evidence(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="evidence")
    technician = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="evidence_collected")
    file = models.FileField(upload_to='evidence/')
    evidence_type = models.CharField(max_length=50, choices=[('DNA', 'DNA'), ('Weapon', 'Weapon'), ('Document', 'Document'), ('Other', 'Other')])
    location = models.CharField(max_length=255)
    collected_at = models.DateTimeField(auto_now_add=True)
    tags = models.TextField(help_text="Comma-separated tags for categorization")
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Verified', 'Verified'), ('Rejected', 'Rejected')], default='Pending')

    def __str__(self):
        return f"Evidence {self.id} for Case {self.case.title}"