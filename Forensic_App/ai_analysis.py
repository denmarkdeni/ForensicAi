import cv2
import os
from deepface import DeepFace
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
KNOWN_FACES_DIR = os.path.join(BASE_DIR, "media", "known_faces")
TEMP_FACE_DIR = os.path.join(BASE_DIR, "media", "temp_face")
TEMP_FACE_PATH = os.path.join(TEMP_FACE_DIR, "temp_face.jpg")

# Ensure directories exist
os.makedirs(KNOWN_FACES_DIR, exist_ok=True)
os.makedirs(TEMP_FACE_DIR, exist_ok=True)

def detect_faces(image_path):
    """Detect faces in an image using OpenCV"""
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    
    detected_faces = []
    for (x, y, w, h) in faces:
        face = img[y:y+h, x:x+w]  # Crop detected face
        detected_faces.append(face)

    return detected_faces, img

def recognize_faces(image_path):
    """Recognize faces using DeepFace"""
    detected_faces, original_img = detect_faces(image_path)

    results = []
    for face in detected_faces:
        cv2.imwrite(TEMP_FACE_PATH, face)

        try:
            analysis = DeepFace.find(TEMP_FACE_PATH, db_path=KNOWN_FACES_DIR, enforce_detection=False)
            if analysis:
                match = analysis[0].to_dict(orient="records")[0]
                results.append({
                    "name": match["identity"].split("/")[-1].split(".")[0],  # Extract name from file path
                    "distance": match["distance"]
                })
            else:
                results.append({"name": "Unknown", "distance": None})
        except Exception as e:
            print(f"Error in face recognition: {e}")
            results.append({"name": "Unknown", "distance": None})

    return results

# Example usage
if __name__ == "__main__":
    test_image = r"C:\Users\Admin\Desktop\ForensicAi\ForensicAi\Forensic_App\static\images\face.jpg"  # Replace with actual image path
    results = recognize_faces(test_image)
    print(results)
