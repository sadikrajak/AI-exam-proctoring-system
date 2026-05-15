from django.shortcuts import render, redirect
from django.utils import timezone
from django.http import JsonResponse
import base64
import numpy as np

from .models import Exam, ExamAttempt, ProctoringLog, ExamReport, User, Question, ExamVideo, ExamAudio, ExamAnswer
from .ai.face import detect_faces
from .ai.screenshot import save_screenshot
from .ai.audio import detect_audio_cheating
from .ai.anomaly import calculate_anomaly_score
import cv2
from .ai.speech_to_text import transcribe_audio

def landing_page(request):
    return render(request, 'landing.html')

# =========================
# ADMIN AUTH (FIXED)
# =========================
def admin_login(request):
    if request.method == "POST":
        if request.POST['username'] == "admin" and request.POST['password'] == "admin":
            request.session['admin'] = True
            return redirect('admin_dashboard')
        return render(request, 'auth/admin_login.html', {'error': 'Invalid admin credentials'})
    return render(request, 'auth/admin_login.html')


def admin_dashboard(request):
    if not request.session.get('admin'):
        return redirect('admin_login')

    exams = Exam.objects.all().order_by('-id')  # get all created exams
    total_exams = exams.count()
    total_candidates = User.objects.filter(role='candidate').count()
    total_attempts = ExamAttempt.objects.count()

    return render(request, 'dashboard/admin_dashboard.html', {
        'exams': exams,                  # ← important
        'total_exams': total_exams,
        'total_candidates': total_candidates,
        'total_attempts': total_attempts,
    })


def admin_logout(request):
    request.session.flush()
    return redirect('admin_login')



# =========================
# CANDIDATE AUTH
# =========================
import base64
import os
from django.conf import settings

def candidate_register(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        full_name = request.POST['full_name']
        email = request.POST['email']
        image_data = request.POST.get('photo_data')

        user = User.objects.create(
            username=username,
            password=password,
            role='candidate',
            full_name=full_name,
            email=email
        )

        if image_data:
            header, encoded = image_data.split(',', 1)
            data = base64.b64decode(encoded)

            filename = f"user_{user.id}.jpg"
            path = os.path.join(settings.MEDIA_ROOT, 'profiles', filename)
            os.makedirs(os.path.dirname(path), exist_ok=True)

            with open(path, 'wb') as f:
                f.write(data)

            user.photo = f"profiles/{filename}"
            user.save()

        return redirect('candidate_login')

    return render(request, 'auth/candidate_register.html')


def candidate_login(request):
    if request.method == "POST":
        user = User.objects.filter(
            username=request.POST['username'],
            password=request.POST['password'],
            role='candidate'
        ).first()

        if user:
            request.session['candidate_id'] = user.id
            return redirect('candidate_dashboard')

        return render(request, 'auth/candidate_login.html', {'error': 'Invalid credentials'})
    return render(request, 'auth/candidate_login.html')


def candidate_dashboard(request):
    if not request.session.get('candidate_id'):
        return redirect('candidate_login')

    user = User.objects.get(id=request.session['candidate_id'])
    return render(request, 'dashboard/candidate_dashboard.html', {'user': user})


def candidate_logout(request):
    request.session.flush()
    return redirect('candidate_login')


# =========================
# EXAM MANAGEMENT
# =========================
def create_exam(request):
    if not request.session.get('admin'):
        return redirect('admin_login')

    if request.method == "POST":
        exam = Exam.objects.create(
            title=request.POST['title'],
            description=request.POST['description'],
            duration=request.POST['duration'],
            start_time=request.POST['start_time'],
            end_time=request.POST['end_time']
        )
        return redirect('admin_dashboard')  # go back to dashboard after save

    return render(request, 'exams/create_exam.html')


def candidate_exam_list(request):
    exams = Exam.objects.all()
    return render(request, 'exams/candidate_exam_list.html', {'exams': exams})


def start_exam(request, exam_id):
    if not request.session.get('candidate_id'):
        return redirect('candidate_login')

    exam = Exam.objects.get(id=exam_id)
    candidate = User.objects.get(id=request.session['candidate_id'])

    attempt, _ = ExamAttempt.objects.get_or_create(
        exam=exam,
        candidate=candidate
    )

    return redirect('exam_page', attempt.id)


def exam_page(request, attempt_id):
    if not request.session.get('candidate_id'):
        return redirect('candidate_login')

    attempt = ExamAttempt.objects.get(id=attempt_id)
    questions = attempt.exam.questions.all()

    return render(request,'exams/exam_page.html',{
        'attempt':attempt,
        'duration':attempt.exam.duration*60,
        'questions':questions
    })


# =========================
# AI PROCTORING
# =========================
def proctoring_feed(request, attempt_id):
    if not request.session.get('candidate_id'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    if request.method != "POST":
        return JsonResponse({'error': 'Invalid request'}, status=400)

    attempt = ExamAttempt.objects.get(id=attempt_id)

    # ✅ HANDLE TAB SWITCH EVENT
    event_type = request.POST.get("event_type")
    if event_type == "TAB_SWITCH":
        ProctoringLog.objects.create(
            attempt=attempt,
            event_type="Tab Switch Detected",
            confidence_score=0.8
        )
        return JsonResponse({'alert': 'Tab switching detected'})

    # ✅ HANDLE IMAGE FRAME
    image_data = request.POST.get('image')
    if not image_data or ',' not in image_data:
        return JsonResponse({'status': 'ignored'})

    try:
        header, encoded = image_data.split(',', 1)
        img = base64.b64decode(encoded)
        np_img = np.frombuffer(img, np.uint8)
        frame = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

        if frame is None:
            return JsonResponse({'status': 'invalid_frame'})
    except Exception:
        return JsonResponse({'status': 'decode_error'})

    # ✅ FACE DETECTION
    face_count = detect_faces(frame)

    if face_count == 0:
        event = "No Face Detected"
    elif face_count > 1:
        event = "Multiple Faces Detected"
    else:
        return JsonResponse({'status': 'ok'})

    # ✅ SAVE SCREENSHOT
    screenshot_path = save_screenshot(frame, attempt.id)

    ProctoringLog.objects.create(
        attempt=attempt,
        event_type=event,
        confidence_score=0.9,
        screenshot=screenshot_path
    )

    return JsonResponse({'alert': event})


def audio_feed(request, attempt_id):
    if not request.session.get('candidate_id'):
        return JsonResponse({'error': 'Unauthorized'})

    if request.method == "POST":
        level = float(request.POST.get('level', 0))
        attempt = ExamAttempt.objects.get(id=attempt_id)

        if detect_audio_cheating(level):
            ProctoringLog.objects.create(
                attempt=attempt,
                event_type="Background Voice Detected",
                confidence_score=level
            )
            return JsonResponse({'alert': 'Audio violation'})

        return JsonResponse({'status': 'ok'})


from django.utils import timezone

def submit_exam(request, attempt_id):
    candidate_id = request.session.get('candidate_id')
    if not candidate_id:
        return redirect('candidate_login')

    try:
        attempt = ExamAttempt.objects.get(id=attempt_id)
    except ExamAttempt.DoesNotExist:
        raise Http404("Invalid exam attempt")

    if attempt.candidate_id != candidate_id:
        return redirect('candidate_dashboard')

    # ⛔ Prevent double submission
    if attempt.submitted:
        report = ExamReport.objects.filter(attempt=attempt).first()
        return render(request, 'exams/exam_submitted.html', {
            'score': report.anomaly_score if report else 0,
            'remarks': report.remarks if report else "Already Submitted"
        })

    # 📝 SAVE ANSWERS
    questions = Question.objects.filter(exam=attempt.exam)
    for question in questions:
        field_name = f"answer_{question.id}"
        answer_text = request.POST.get(field_name)
        if answer_text:
            ExamAnswer.objects.create(
                attempt=attempt,
                question=question,
                answer_text=answer_text
            )

    # 🕒 SAVE TIME
    attempt.submit_time = timezone.now()
    time_taken = (attempt.submit_time - attempt.start_time).total_seconds()
    attempt.time_taken_seconds = int(time_taken)
    attempt.submitted = True
    attempt.save()

    # ⏱️ FAST COMPLETION CHECK
    exam_total_time = attempt.exam.duration * 60
    if time_taken < (0.3 * exam_total_time):
        ProctoringLog.objects.create(
            attempt=attempt,
            event_type="Very Fast Exam Completion",
            confidence_score=0.8
        )

    # 🎤 SPEECH TO TEXT (SAFE)
    exam_audio = ExamAudio.objects.filter(attempt=attempt).first()
    if exam_audio and exam_audio.audio and not exam_audio.transcript:
        try:
            exam_audio.transcript = transcribe_audio(exam_audio.audio.path)
            exam_audio.save()
        except Exception as e:
            print("Audio transcription failed:", e)

    # 🧠 ANOMALY SCORE
    logs = ProctoringLog.objects.filter(attempt=attempt)
    score = calculate_anomaly_score(logs)

    remarks = "Clean Attempt" if score < 30 else "Suspicious Attempt"

    ExamReport.objects.update_or_create(
        attempt=attempt,
        defaults={
            "anomaly_score": score,
            "remarks": remarks
        }
    )

    return render(request, 'exams/exam_submitted.html', {
        'score': score,
        'remarks': remarks
    })



# =========================
# ADMIN REPORTS
# =========================
def admin_reports(request):
    if not request.session.get('admin'):
        return redirect('admin_login')

    attempts = ExamAttempt.objects.all()
    return render(request, 'dashboard/admin_reports.html', {'attempts': attempts})


def attempt_report(request, attempt_id):
    if not request.session.get('admin'):
        return redirect('admin_login')

    attempt = ExamAttempt.objects.get(id=attempt_id)
    logs = ProctoringLog.objects.filter(attempt=attempt)
    report = ExamReport.objects.get(attempt=attempt)

    return render(request, 'dashboard/attempt_report.html', {
        'attempt': attempt,
        'logs': logs,
        'report': report
    })


def add_question(request, exam_id):
    if not request.session.get('admin'):
        return redirect('admin_login')

    exam = Exam.objects.get(id=exam_id)

    if request.method == "POST":
        Question.objects.create(
            exam=exam,
            text=request.POST['text']
        )
        return redirect('add_question', exam_id=exam.id)

    questions = exam.questions.all()
    return render(request, 'exams/add_question.html', {
        'exam': exam,
        'questions': questions
    })

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def upload_exam_video(request, attempt_id):
    if not request.session.get('candidate_id'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    if request.method == "POST" and request.FILES.get("video"):
        attempt = ExamAttempt.objects.get(id=attempt_id)

        video_file = request.FILES['video']

        exam_video, created = ExamVideo.objects.get_or_create(
            attempt=attempt
        )
        exam_video.video.save(video_file.name, video_file)
        exam_video.save()

        return JsonResponse({'status': 'video_saved'})

    return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt
def upload_exam_audio(request, attempt_id):
    if not request.session.get('candidate_id'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    if request.method == "POST" and request.FILES.get("audio"):
        attempt = ExamAttempt.objects.get(id=attempt_id)

        exam_audio, _ = ExamAudio.objects.get_or_create(attempt=attempt)
        exam_audio.audio.save(request.FILES['audio'].name, request.FILES['audio'])
        exam_audio.save()

        return JsonResponse({'status': 'audio_saved'})

    return JsonResponse({'error': 'Invalid request'}, status=400)
