import cv2 as cv
import numpy as np
import requests
from datetime import datetime
import json

class Camera:
    def __init__(self, telegram_token, chat_id):
        # Telegram settings
        self.telegram_token = telegram_token
        self.chat_id = chat_id
        
        # Load pre-trained model
        self.net = cv.dnn.readNetFromCaffe('models/config.txt', 'models/mobilenet_iter_73000.caffemodel')
        self.cap = cv.VideoCapture(0)
        
        # Video Writer Initialization (but not writing yet)
        self.fourcc = cv.VideoWriter_fourcc(*'XVID')
        self.out = None
        self.recording = False
        self.no_detection_frames = 0
    
    def start_recording(self, frame):
        current_time = datetime.now()
        formatted_time = current_time.strftime('%Y%m%d_%H%M%S')
        self.out = cv.VideoWriter(f'videos/{formatted_time}.avi', self.fourcc, 30.0, (frame.shape[1], frame.shape[0]))
        self.recording = True

    def stop_recording(self):
        if self.out:
            self.out.release()
        self.recording = False
        self.no_detection_frames = 0

    def save_snapshot(self, frame):
        # Get the current time and format it
        current_time = datetime.now()
        formatted_time = current_time.strftime('%Y%m%d_%H%M%S')
        
        # Define the path for saving
        img_path = f"imgs/{formatted_time}.jpg"
        
        # Save the image using OpenCV
        cv.imwrite(img_path, frame)
        
        return img_path

    def send_telegram_notification(self, message, img_path):
        url = f'https://api.telegram.org/bot{self.telegram_token}/sendPhoto'
        with open(img_path, 'rb') as img_file:
            payload = {
                'chat_id': self.chat_id,
                'caption': message
            }
            files = {
                'photo': img_file
            }
            requests.post(url, data=payload, files=files)


    def run(self):
        print("Camera started...")

        while True:
            person_detected = False
            _, frame = self.cap.read()
            blob = cv.dnn.blobFromImage(frame, 0.007843, (300, 300), 127.5)
            self.net.setInput(blob)
            detections = self.net.forward()

            for i in range(detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                idx = int(detections[0, 0, i, 1])

                # Check if the detection is of a person and its confidence is greater than the minimum confidence
                if idx == 15 and confidence > 0.5:
                    person_detected = True
                    box = detections[0, 0, i, 3:7] * np.array([frame.shape[1], frame.shape[0], frame.shape[1], frame.shape[0]])
                    (startX, startY, endX, endY) = box.astype("int")
                    cv.rectangle(frame, (startX, startY), (endX, endY), (0, 255, 0), 2)

            # If a person is detected and not recording, start recording and send a notification
            if person_detected and not self.recording:
                self.start_recording(frame)
                img_path = self.save_snapshot(frame)  # Save the frame and get the image path
                self.send_telegram_notification("Person detected!", img_path)

            # If recording and no person detected for 30 frames, stop recording
            if not person_detected and self.recording:
                self.no_detection_frames += 1
                if self.no_detection_frames >= 30:
                    self.stop_recording()

            # Write frame to video if recording
            if self.recording:
                self.out.write(frame)

            # Display the frame with detections
            cv.imshow('Live Detection', frame)

            # Break the loop if 'q' key is pressed
            if cv.waitKey(1) & 0xFF == ord('q'):
                break
        
        self.cap.release()
        if self.recording:
            if hasattr(self, 'cap') and self.cap is not None:
                self.cap.release()
            self.stop_recording()
        cv.destroyAllWindows()
        print("Camera released...")

# Load the Telegram token and chat id from the json file
with open('telegram_token_chatid.json', 'r') as f:
    variables = json.load(f)

TOKEN = variables['TOKEN']
CHAT_ID = variables['CHAT_ID']

# To start the camera and view detections
cam = Camera(TOKEN, CHAT_ID)
cam.run()
