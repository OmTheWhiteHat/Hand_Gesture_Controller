import cv2
import mediapipe as mp
import pyautogui
import subprocess
import time
import os
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# Initialize MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1)
mp_draw = mp.solutions.drawing_utils

# Volume control setup
devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume_ctrl = cast(interface, POINTER(IAudioEndpointVolume))

cap = cv2.VideoCapture(0)

prev_gesture = None
last_action_time = 0
last_proc = None

# App launcher with return handle
def open_app(app_name):
    global last_proc
    if app_name == 'notepad':
        last_proc = subprocess.Popen(['notepad.exe'])
    elif app_name == 'calculator':
        last_proc = subprocess.Popen(['calc.exe'])
    elif app_name == 'cmd':
        last_proc = subprocess.Popen(['cmd.exe'])
    elif app_name == 'chrome':
        last_proc = subprocess.Popen(['start', 'chrome'], shell=True)

# Kill previous app
def close_last_app():
    global last_proc
    if last_proc:
        try:
            last_proc.terminate()
            print("Closed previous app.")
        except Exception as e:
            print("Failed to close app:", e)
        last_proc = None

# Media control
def media_action(action):
    if action == "play_pause":
        pyautogui.press('playpause')
    elif action == "next":
        pyautogui.press('nexttrack')
    elif action == "prev":
        pyautogui.press('prevtrack')

# Volume control
def set_volume(direction):
    current = volume_ctrl.GetMasterVolumeLevelScalar()
    if direction == "up":
        volume_ctrl.SetMasterVolumeLevelScalar(min(current + 0.1, 1.0), None)
    elif direction == "down":
        volume_ctrl.SetMasterVolumeLevelScalar(max(current - 0.1, 0.0), None)

while True:
    success, img = cap.read()
    if not success:
        break

    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    result = hands.process(img_rgb)

    if result.multi_hand_landmarks:
        for hand_landmarks in result.multi_hand_landmarks:
            mp_draw.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            lm = hand_landmarks.landmark

            fingers = []

            # Thumb
            fingers.append(1 if lm[4].x > lm[3].x else 0)

            # Other fingers
            tips = [8, 12, 16, 20]
            for tip in tips:
                fingers.append(1 if lm[tip].y < lm[tip - 2].y else 0)

            gesture = "UNKNOWN"

            if fingers == [1, 1, 1, 1, 1]:
                gesture = "OPEN"
            elif fingers == [1, 1, 1, 0, 1]:
                gesture = "CUSTOME"
            elif fingers == [0, 1, 1, 0, 0]:
                gesture = "PEACE"
            elif fingers == [0, 1, 0, 0, 0]:
                gesture = "PLAY/PAUSE"
            elif fingers == [0, 1, 1, 0, 0]:
                gesture = "NEXT"
            elif fingers == [0, 0, 0, 0, 1]:
                gesture = "PREV"
            elif fingers == [1, 0, 0, 0, 1]:
                gesture = "VOLUME UP"
            elif fingers == [0, 0, 1, 0, 0]:
                gesture = "VOLUME DOWN"
            elif fingers == [1, 1, 0, 0, 1]:
                gesture = "CLOSE"
            elif fingers == [1, 1, 1, 1, 0]:
                gesture = "TERMINATE"

            cv2.putText(img, f'Gesture: {gesture}', (10, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # Trigger only if it's not OPEN hand
            if time.time() - last_action_time > 2 and gesture != prev_gesture:
                if gesture not in ["OPEN", "UNKNOWN"]:
                    # Inside the gesture actions:
                    # Remove THUMBS UP gesture entirely
                    if gesture == "TERMINATE":
                        print("Terminate detected. Exiting program...")
                        cap.release()
                        cv2.destroyAllWindows()
                        exit()  # Clean exit
                    elif gesture == "PEACE":
                        try:
                            # Try to open Windows Media Player
                            last_proc = subprocess.Popen(['wmplayer.exe'])
                        except FileNotFoundError:
                            try:
                                # Fallback to open any .mp3 file with default music player
                                music_file = os.path.expanduser('./music/Wistoria_ Wand and Sword E1  Rigarden Magical Academy  OST REMIX.mp3')  # You can change the file path
                                if os.path.exists(music_file):
                                    last_proc = subprocess.Popen(['start', '', music_file], shell=True)
                                else:
                                    print("Music file not found.")
                            except Exception as e:
                                print("Could not open music player:", e)
                    elif gesture == "PLAY/PAUSE":
                        media_action("play_pause")
                    elif gesture == "NEXT":
                        media_action("next")
                    elif gesture == "PREV":
                        media_action("prev")
                    elif gesture == "VOLUME UP":
                        set_volume("up")
                    elif gesture == "VOLUME DOWN":
                        set_volume("down")
                    elif gesture == "CLOSE":
                        close_last_app()
                    elif gesture == "CUSTOME1":
                        try:
                            # Open File Explorer
                            subprocess.Popen(['explorer'])
                            # Open Google Chrome (ensure it's in PATH or use full path)
                            print("Opened Explorer")
                        except Exception as e:
                            print("Failed to open apps:", e)
                    last_action_time = time.time()
                    prev_gesture = gesture

    cv2.imshow("Gesture Controller", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()