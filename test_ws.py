import cv2
import numpy as np
import sys
sys.stdout.reconfigure(errors='replace')
sys.stderr.reconfigure(errors='replace')

# Create a dummy image
img = np.zeros((480, 640, 3), dtype=np.uint8)
cv2.putText(img, 'iPhone 15', (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 255, 255), 5)

from src.vision.vision_analyzer import VisionAnalyzer
analyzer = VisionAnalyzer()

print("Using method:", analyzer._method)
result = analyzer._analyze_ws(
    base64.b64encode(cv2.imencode('.jpg', img)[1]).decode('utf-8') if analyzer._method == 'websocket' else "", 
    "請敘述這張圖片"
) if analyzer._method == 'websocket' else "Not WS"
print("WS RESULT:", result)
