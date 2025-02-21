from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Evidence
from .ai_analysis import recognize_faces  # AI function

@receiver(post_save, sender=Evidence)
def trigger_ai_analysis(sender, instance, **kwargs):
    print('check')
    if instance.file_type == 'Verified':  # AI runs only after verification'
        print("ai started")
        recognize_faces(instance.file.path)




