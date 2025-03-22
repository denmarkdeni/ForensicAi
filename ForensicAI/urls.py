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
    path('logout/',views.Logout,name='logout'),

    path('admin_dashboard/',views.admin_dashboard,name='admin_dashboard'),
    path('admin_user_manage/',views.admin_user_manage,name='admin_user_manage'),
    path('admin_case_manage/',views.admin_case_manage,name='admin_case_manage'),
    path('admin_evidence_manage/',views.admin_evidence_manage,name='admin_evidence_manage'),
    path('admin_ai_manage/',views.admin_ai_manage,name='admin_ai_manage'),
    path('admin_report_manage/',views.admin_report_manage,name='admin_report_manage'),

    path("add_user/", views.add_user, name="add_user"),
    path("update-user/<int:user_id>/", views.update_user, name="update-user"),
    path("delete-user/<int:user_id>/", views.delete_user, name="delete-user"),

    path('create_case/',views.create_case,name='create_case'),
    path('view_case_details/<str:case_id>/',views.view_case_details,name='view_case_details'),
    path("update-case/<str:case_id>/", views.update_case, name="update_case"),
    path("delete-case/<str:case_id>/", views.delete_case, name="delete_case"),

    path("upload-evidence/", views.upload_evidence, name="upload_evidence"),
    path("view_evidence_details/<int:evidence_id>/", views.view_evidence_details, name="view_evidence_details"),
    path("update-evidence/<int:evidence_id>/", views.update_evidence, name="update_evidence"),
    path("delete-evidence/<int:evidence_id>/", views.delete_evidence, name="delete_evidence"),

    path("generate_case_report_view/<str:case_id>/", views.generate_case_report_view, name="generate_case_report_view"),

    path('evidence-review/', views.evidence_review, name='evidence_review'),
    path('live/', views.live_emotion, name='live_emotion'),
    path('detect_emotion/', views.detect_emotion, name='detect_emotion'),
    path("ai-dashboard/", views.ai_analysis_dashboard, name="ai_dashboard"),
    path("case/<str:case_id>/evidences/", views.case_evidences, name="case_evidences"),
    path("analyze/<int:evidence_id>/", views.analyze_evidence, name="analyze_evidence"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)