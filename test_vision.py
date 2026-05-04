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

result = analyzer.send_photo(img)
print("RESULT:", result)
