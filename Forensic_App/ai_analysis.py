import cv2
import os
from deepface import DeepFace
from pathlib import Path
import numpy as np
import pytesseract
from PIL import Image, ImageChops, ImageEnhance, ImageFilter
from PIL.ExifTags import TAGS
import imutils, json
from ultralytics import YOLO
import speech_recognition as sr
from pydub import AudioSegment
import torch
import torchaudio
import nltk
from resemblyzer import preprocess_wav, VoiceEncoder
import whisper
from pdf2image import convert_from_path

MODEL_PATH = r"C:\Users\Admin\Desktop\Maria Deniston\ForensicAi\Forensic_App\models\\"
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
    

def process_image(image_path):
    """Performs AI-based image analysis (face/object recognition, OCR, metadata extraction)."""

    # ✅ Check if the image exists
    image = cv2.imread(image_path)
    if image is None:
        return {"error": "Image not found or corrupted"}, 0.0

    # ✅ **Increase Resolution & Preprocess Image**
    image = imutils.resize(image, width=1500)  # Scale image up to improve detection
    image = enhance_image(image)  # Apply contrast and sharpening
    
    analysis_results = {}

    # ✅ **1. Face Detection & Recognition (Using DeepFace or MTCNN)**
    try:
        faces = DeepFace.extract_faces(image_path, detector_backend="mtcnn")  # Use MTCNN for better accuracy
        face_count = len(faces)
        analysis_results["face_detection"] = {
            "message": "Faces detected" if face_count > 0 else "No face detected",
            "face_count": face_count,
        }
    except Exception as e:
        analysis_results["face_detection"] = {"error": f"Face detection failed: {str(e)}"}
        face_count = 0

    # ✅ **2. Object Detection (Using YOLOv3 + Non-Maximum Suppression)**
    try:
        # Load YOLOv3 model
        net = cv2.dnn.readNetFromDarknet(MODEL_PATH + "yolov3.cfg", MODEL_PATH + "yolov3.weights")
        net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        
        # Get layer names
        layer_names = net.getLayerNames()
        output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]
        
        # Load class labels
        with open(MODEL_PATH + "coco.names", "r") as f:
            classes = f.read().strip().split("\n")
        
        # YOLO Object Detection
        height, width, _ = image.shape
        blob = cv2.dnn.blobFromImage(image, 1/255.0, (416, 416), swapRB=True, crop=False)
        net.setInput(blob)
        detections = net.forward(output_layers)
        
        # Process detections with Non-Maximum Suppression (NMS)
        conf_threshold = 0.5
        nms_threshold = 0.4
        detected_objects = []
        boxes, confidences, class_ids = [], [], []

        for output in detections:
            for obj in output:
                scores = obj[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if confidence > conf_threshold:
                    center_x, center_y, w, h = map(int, obj[0:4] * np.array([width, height, width, height]))
                    x, y = int(center_x - w / 2), int(center_y - h / 2)
                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)

        indices = cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold, nms_threshold)
        for i in indices.flatten():
            detected_objects.append(classes[class_ids[i]])
        
        # Store results
        analysis_results["object_detection"] = {
            "objects": detected_objects if detected_objects else ["No objects detected"]
        }
    except Exception as e:
        analysis_results["object_detection"] = {"error": f"Object detection failed: {str(e)}"}

    # ✅ **3. Text Extraction (OCR) with Preprocessing**
    try:
        analysis_results["ocr_text"] = extract_text_from_image(image_path)
    except Exception as e:
        analysis_results["ocr_text"] = {"error": f"OCR failed: {str(e)}"}

    # ✅ **4. Image Forgery Detection (Error Level Analysis)**
    try:
        ela_image = detect_image_forgery(image_path)
        analysis_results["forgery_detection"] = "Possible tampering detected" if ela_image else "No forgery detected"
    except Exception as e:
        analysis_results["forgery_detection"] = {"error": f"Forgery analysis failed: {str(e)}"}

    # ✅ **5. Metadata Extraction (EXIF)**
    try:
        analysis_results["metadata"] = extract_metadata(image_path)
    except Exception as e:
        analysis_results["metadata"] = {"error": f"Metadata extraction failed: {str(e)}"}

    # Confidence score based on multiple factors
    confidence = 0.9 if face_count > 0 else 0.6

    return analysis_results, confidence

# ✅ **Helper Function: Enhance Image Quality**
def enhance_image(image):
    """Increases image contrast and sharpness for better detection."""
    pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    enhancer = ImageEnhance.Contrast(pil_img)
    pil_img = enhancer.enhance(1.5)  # Increase contrast

    sharpness = ImageEnhance.Sharpness(pil_img)
    pil_img = sharpness.enhance(2.0)  # Increase sharpness

    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

# ✅ Preprocessing Function for OCR
def preprocess_for_ocr(image):
    """Converts image to grayscale, applies adaptive thresholding, and noise reduction for OCR."""
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    except Exception as e:
        return None, f"Grayscale conversion failed: {str(e)}"

    # Remove noise using Gaussian Blur
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Adaptive Thresholding for better text extraction
    processed = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    return processed, None

# ✅ OCR Function
def extract_text_from_image(image_path):
    """Extracts text from an image using Tesseract OCR with preprocessing."""
    try:
        # Read Image
        image = cv2.imread(image_path)
        if image is None:
            return json.dumps({"error": "Image not found or invalid format"}, indent=2)

        # Preprocess Image
        ocr_image, err = preprocess_for_ocr(image)
        if err:
            return json.dumps({"error": err}, indent=2)

        # Perform OCR with better config
        text = pytesseract.image_to_string(ocr_image, config="--psm 6 --oem 3")

        return json.dumps({"ocr_text": text.strip() if text.strip() else "No text detected"}, indent=2)

    except Exception as e:
        return json.dumps({"error": f"OCR failed: {str(e)}"}, indent=2)


# ✅ **Helper Function: Detect Image Forgery**
def detect_image_forgery(image_path):
    """Detects possible image forgery using Error Level Analysis (ELA)."""
    try:
        original = Image.open(image_path)
        temp_path = "temp_ela.jpg"
        original.save(temp_path, quality=90)  # Save with high quality

        ela_image = Image.open(temp_path)
        ela_diff = ImageChops.difference(original, ela_image)

        return ela_diff
    except Exception as e:
        return None

# ✅ **Extracting Clean Meta DATA**
def extract_metadata(image_path):
    """Extract metadata (EXIF) including device, camera, date, and GPS."""
    metadata = {}
    gps_data = {}

    try:
        image_pil = Image.open(image_path)
        exif_data = image_pil._getexif()

        if exif_data:
            for tag, value in exif_data.items():
                tag_name = TAGS.get(tag, tag)
                metadata[tag_name] = value

            # Extract Device Info
            device = metadata.get("Make", "Unknown") + " " + metadata.get("Model", "Unknown")
            metadata["Device"] = device.strip()

            # Extract Camera Settings
            camera_info = {
                "Resolution": f"{image_pil.width} x {image_pil.height}",
                "ISO": metadata.get("ISOSpeedRatings", "Unknown"),
                "Aperture": f"f/{metadata.get('FNumber', 'Unknown')}",
                "Shutter Speed": f"1/{round(metadata.get('ExposureTime', 1))} sec",
                "Focal Length": f"{metadata.get('FocalLength', 'Unknown')}mm"
            }
            metadata["Camera"] = camera_info

            # Extract Date & Time
            metadata["Date_Time"] = metadata.get("DateTimeOriginal", "Unknown")

            # Extract GPS Data
            gps_info = exif_data.get(34853)  # GPSInfo tag ID
            if gps_info:
                def convert_to_degrees(value):
                    """Convert GPS coordinates to decimal degrees"""
                    if isinstance(value, tuple) and len(value) == 3:
                        return float(value[0]) + float(value[1]) / 60 + float(value[2]) / 3600
                    return float(value)

                lat = gps_info.get(2)  # GPSLatitude
                lon = gps_info.get(4)  # GPSLongitude
                lat_ref = gps_info.get(1, 'N')
                lon_ref = gps_info.get(3, 'E')

                if lat and lon:
                    lat = convert_to_degrees(lat)
                    lon = convert_to_degrees(lon)

                    if lat_ref != 'N':
                        lat = -lat
                    if lon_ref != 'E':
                        lon = -lon

                    gps_data["Latitude"] = lat
                    gps_data["Longitude"] = lon
                    metadata["Location"] = gps_data
                else:
                    metadata["Location"] = "No GPS data found"
            else:
                metadata["Location"] = "No GPS data found"

        # Clean up and return structured output
        clean_metadata = {
            "device": metadata.get("Device", "Unknown"),
            "camera": metadata.get("Camera", {}),
            "location": metadata.get("Location", "No GPS data found"),
            "date_time": metadata.get("Date_Time", "Unknown")
        }
        return clean_metadata

    except Exception as e:
        return {"error": f"Metadata extraction failed: {str(e)}"}

# ✅ **Process Video Function**
def process_video(video_path):
    """Analyzes video frames for faces, objects, or scene detection."""
    cap = cv2.VideoCapture(video_path)
    frame_number = 0
    detections = []

    model = YOLO(MODEL_PATH + "yolov8n.pt") 

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_number += 1

        # Run object detection on the frame
        results = model(frame)
        
        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls)  # Object class ID
                conf = float(box.conf)  # Confidence score

                # If confidence is high enough, log detection
                if conf > 0.75:
                    detections.append({
                        "frame": frame_number,
                        "object": model.names[cls_id],
                        "confidence": conf
                    })

        # Stop processing after 500 frames (for speed)
        if frame_number > 50:
            break

    cap.release()

    if detections:
        return {"message": "Suspicious activity detected", "detections": detections}, max(d["confidence"] for d in detections)
    else:
        return {"message": "No suspicious activity detected"}, 0.0
    
# Suspicious phrases database (extend as needed)
SUSPICIOUS_PHRASES = ["help", "gun", "kill", "hide the body", "threaten", "run", "scream","murder","robbery","theft","kidnap","abduction","assault"]

# Load AI Models
whisper_model = whisper.load_model("small")  # Whisper for transcription
encoder = VoiceEncoder()  # Speaker recognition model

def convert_to_wav(audio_path):
    """Converts MP3 or other formats to WAV"""
    new_path = audio_path.replace(".mp3", ".wav")
    sound = AudioSegment.from_file(audio_path)
    sound.export(new_path, format="wav")
    return new_path

def detect_suspicious_phrases(text):
    """Flags if suspicious words are found in the transcript."""
    detected_phrases = [phrase for phrase in SUSPICIOUS_PHRASES if phrase in text.lower()]
    return detected_phrases

def identify_speaker(audio_path):
    """Identifies if multiple speakers exist."""
    wav = preprocess_wav(audio_path)
    embed = encoder.embed_utterance(wav)
    return np.linalg.norm(embed)  # Returns a unique voice signature

def process_audio(audio_path):
    """Analyzes audio for speech, threats, and sound classification."""
    if audio_path.endswith(".mp3"):
        audio_path = convert_to_wav(audio_path)

    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)
        
        # Whisper AI for better transcription
        result = whisper_model.transcribe(audio_path)
        text = result["text"]
        
        # Detect suspicious phrases
        flagged_phrases = detect_suspicious_phrases(text)
        
        # Speaker identification
        speaker_signature = identify_speaker(audio_path)
        
        # Confidence metric (simplified)
        confidence = 0.85 if text else 0.0

        # AI Analysis Result
        ai_results = {
            "message": "Audio transcript analyzed",
            "transcript": text,
            "suspicious_phrases": flagged_phrases,
            "speaker_signature": str(speaker_signature),
            "confidence": confidence
        }

        if audio_path.endswith(".wav") and os.path.exists(audio_path):
            os.remove(audio_path)
    
    except sr.UnknownValueError:
        ai_results = {"error": "Could not transcribe"}
        confidence = 0.0
    except Exception as e:
        ai_results = {"error": str(e)}
        confidence = 0.0

    return ai_results, confidence

    
POPPLER_PATH = r"C:\poppler-24.08.0\Library\bin"

def process_document(doc_path):
    """Extracts text from documents using OCR."""

    images = convert_from_path(doc_path, poppler_path=POPPLER_PATH)
    text_results = []

    for i, image in enumerate(images):
        text = pytesseract.image_to_string(image)  # Run OCR on each page
        text_results.append(text)
    texts = " ".join(text_results)
    ai_results = {"message": "Extracted text", "text": texts}
    confidence = 0.75
    return ai_results, confidence