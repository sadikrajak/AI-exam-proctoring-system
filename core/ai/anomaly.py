def calculate_anomaly_score(logs):
    score = 0

    multi_face_count = logs.filter(
        event_type="Multiple Faces Detected"
    ).count()

    no_face_count = logs.filter(
        event_type="No Face Detected"
    ).count()

    audio_count = logs.filter(
        event_type="Background Voice Detected"
    ).count()

    fast_finish = logs.filter(
        event_type="Very Fast Exam Completion"
    ).count()

    # Multi-face logic (important)
    if multi_face_count >= 3:
        score += 40
    elif multi_face_count == 2:
        score += 25
    elif multi_face_count == 1:
        score += 10

    # Other violations
    score += no_face_count * 5
    score += audio_count * 10
    score += fast_finish * 30

    return min(score, 100)
