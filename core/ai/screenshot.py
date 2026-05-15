import cv2
import os
from django.conf import settings
from datetime import datetime

def save_screenshot(frame, attempt_id):
    folder = os.path.join(settings.MEDIA_ROOT, "screenshots")
    os.makedirs(folder, exist_ok=True)

    filename = f"attempt_{attempt_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
    path = os.path.join(folder, filename)

    cv2.imwrite(path, frame)
    return f"screenshots/{filename}"
