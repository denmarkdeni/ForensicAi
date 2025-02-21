"""
URL configuration for ForensicAI project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from Forensic_App import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',views.index,name='index'),
    path('register/',views.register,name='register'),
    path('login/',views.Login,name='login'),
    path('dashboard/',views.dashboard,name='dashboard'),
    path('logout/',views.Logout,name='logout'),
    path('dashboard/create-case/',views.create_case,name='create_case'),
    path('dashboard/case_list/',views.case_list,name='case_list'),
    path('evidence/', views.evidence_list, name='evidence_list'),
    path('evidence/upload/', views.upload_evidence, name='upload_evidence'),
    path('update-evidence/<int:evidence_id>/', views.update_evidence, name='update_evidence'),
    path('evidence-review/', views.evidence_review, name='evidence_review'),
    path('live/', views.live_emotion, name='live_emotion'),
    path('detect_emotion/', views.detect_emotion, name='detect_emotion'),
    path("ai-dashboard/", views.ai_analysis_dashboard, name="ai_dashboard"),
    path("case/<str:case_id>/evidences/", views.case_evidences, name="case_evidences"),
    path("analyze/<int:evidence_id>/", views.analyze_evidence, name="analyze_evidence"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)