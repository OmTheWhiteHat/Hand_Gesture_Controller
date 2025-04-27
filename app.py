import cv2
import mediapipe as mp
import subprocess
import time
import os
import ctypes
import psutil
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# --- Media Key Codes ---
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1

def press_media_key(vk_code):
    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", ctypes.c_ushort),
                    ("wScan", ctypes.c_ushort),
                    ("dwFlags", ctypes.c_ulong),
                    ("time", ctypes.c_ulong),
                    ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]

    class INPUT(ctypes.Structure):
        class _INPUT(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT)]
        _anonymous_ = ("_input",)
        _fields_ = [("type", ctypes.c_ulong), ("_input", _INPUT)]

    extra = ctypes.c_ulong(0)
    ii = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=vk_code, wScan=0, dwFlags=0, time=0, dwExtraInfo=ctypes.pointer(extra)))
    ctypes.windll.user32.SendInput(1, ctypes.pointer(ii), ctypes.sizeof(ii))

    ii.ki.dwFlags = KEYEVENTF_KEYUP
    ctypes.windll.user32.SendInput(1, ctypes.pointer(ii), ctypes.sizeof(ii))

def media_action(action):
    if action == "play_pause":
        press_media_key(VK_MEDIA_PLAY_PAUSE)
    elif action == "next":
        press_media_key(VK_MEDIA_NEXT_TRACK)
    elif action == "prev":
        press_media_key(VK_MEDIA_PREV_TRACK)

def close_last_app():
    global last_proc
    if last_proc:
        try:
            last_proc.terminate()
        except Exception as e:
            print("Failed to close subprocess:", e)
        last_proc = None
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] and 'Spotify.exe' in proc.info['name']:
            try:
                proc.terminate()
            except Exception as e:
                print(f"Failed to terminate {proc.info['name']}: {e}")

# --- Init MediaPipe ---
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, model_complexity=0,
                       min_detection_confidence=0.5, min_tracking_confidence=0.5)
mp_draw = mp.solutions.drawing_utils

# --- Volume setup ---
devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume_ctrl = cast(interface, POINTER(IAudioEndpointVolume))

# --- Webcam ---
cap = cv2.VideoCapture(0)
terminate_ready = False
terminate_time = 0
prev_gesture = None
last_action_time = 0
last_proc = None

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

    img = cv2.resize(img, (640, 480))
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    result = hands.process(img_rgb)

    gesture = "UNKNOWN"

    if result.multi_hand_landmarks:
        hand_landmarks = result.multi_hand_landmarks[0]
        lm = hand_landmarks.landmark

        fingers = [
            1 if lm[4].x > lm[3].x else 0,
            1 if lm[8].y < lm[6].y else 0,
            1 if lm[12].y < lm[10].y else 0,
            1 if lm[16].y < lm[14].y else 0,
            1 if lm[20].y < lm[18].y else 0
        ]

        gestures_map = {
            (1, 1, 1, 1, 1): "OPEN",
            (0, 1, 1, 0, 0): "PEACE",
            (0, 1, 0, 0, 0): "PLAY/PAUSE",
            (1, 1, 1, 0, 0): "NEXT",
            (0, 0, 0, 0, 1): "PREV",
            (1, 0, 0, 0, 1): "VOLUME UP",
            (0, 0, 1, 0, 0): "VOLUME DOWN",
            (1, 1, 0, 0, 1): "CLOSE",
            (1, 1, 1, 0, 1): "TERMINATE"
        }

        gesture = gestures_map.get(tuple(fingers), "UNKNOWN")
        mp_draw.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)

        cv2.putText(img, f'Gesture: {gesture}', (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        if time.time() - last_action_time > 1.5 and gesture != prev_gesture:
            if gesture not in ["OPEN", "UNKNOWN"]:
                if gesture == "TERMINATE":
                    if terminate_ready and (time.time() - terminate_time <= 5):
                        cap.release()
                        cv2.destroyAllWindows()
                        exit()
                    else:
                        terminate_time = time.time()
                        terminate_ready = True
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
                last_action_time = time.time()
                prev_gesture = gesture

    cv2.imshow("Gesture Controller", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()