from django.urls import path
from .views import *

urlpatterns = [
    path('', landing_page, name='landing'),
    path('admin_login/', admin_login, name='admin_login'),
    path('admin_dashboard/', admin_dashboard, name='admin_dashboard'),
    path('admin_logout/', admin_logout, name='admin_logout'),
    path('register/', candidate_register, name='candidate_register'),
    path('login/', candidate_login, name='candidate_login'),
    path('candidate_dashboard/', candidate_dashboard, name='candidate_dashboard'),
    path('candidate_logout/', candidate_logout, name='candidate_logout'),
    path('exams/create/', create_exam, name='create_exam'),
    path('candidate/exams/', candidate_exam_list, name='candidate_exam_list'),
    path('exam/start/<int:exam_id>/', start_exam, name='start_exam'),
    path('exam/<int:attempt_id>/', exam_page, name='exam_page'),
    path('proctoring/<int:attempt_id>/', proctoring_feed, name='proctoring_feed'),
    path('proctoring/audio/<int:attempt_id>/', audio_feed, name='audio_feed'),
    path('exam/submit/<int:attempt_id>/', submit_exam, name='submit_exam'),
    path('admin_reports/', admin_reports, name='admin_reports'),
    path('admin_reports/<int:attempt_id>/', attempt_report, name='attempt_report'),
    path('exams/<int:exam_id>/questions/', add_question, name='add_question'),
    path('upload-video/<int:attempt_id>/', upload_exam_video, name='upload_exam_video'),
    path(
    'upload-audio/<int:attempt_id>/',
    upload_exam_audio,
    name='upload_exam_audio'
),

]
