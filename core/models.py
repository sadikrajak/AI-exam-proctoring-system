from django.db import models
from django.utils import timezone

class User(models.Model):
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    role = models.CharField(max_length=20)  # candidate

    full_name = models.CharField(max_length=150, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    photo = models.ImageField(upload_to='profiles/', null=True, blank=True)

    def __str__(self):
        return self.username



class Exam(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    duration = models.IntegerField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()


class ExamAttempt(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    candidate = models.ForeignKey(User, on_delete=models.CASCADE)

    start_time = models.DateTimeField(auto_now_add=True)
    submit_time = models.DateTimeField(null=True, blank=True)
    time_taken_seconds = models.IntegerField(default=0)

    submitted = models.BooleanField(default=False)

class ProctoringLog(models.Model):
    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=100)
    confidence_score = models.FloatField()
    screenshot = models.ImageField(upload_to='screenshots/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ExamReport(models.Model):
    attempt = models.OneToOneField(ExamAttempt, on_delete=models.CASCADE)
    anomaly_score = models.FloatField()
    remarks = models.CharField(max_length=100)


class Question(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()

    def __str__(self):
        return f"Q for {self.exam.title}"


class ExamVideo(models.Model):
    attempt = models.OneToOneField(ExamAttempt, on_delete=models.CASCADE)
    video = models.FileField(upload_to='exam_videos/')
    created_at = models.DateTimeField(auto_now_add=True)

class ExamAudio(models.Model):
    attempt = models.OneToOneField(ExamAttempt, on_delete=models.CASCADE)
    audio = models.FileField(upload_to='exam_audio/')
    transcript = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ExamAnswer(models.Model):
    attempt = models.ForeignKey(
        ExamAttempt,
        on_delete=models.CASCADE,
        related_name="answers"
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE
    )
    answer_text = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
