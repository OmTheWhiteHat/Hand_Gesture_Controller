import cv2
import mediapipe as mp
import pyautogui
import sys
import math
import time

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

# Open webcam
cap = cv2.VideoCapture(0)

# Function to find distance between two landmarks
def find_distance(lm1, lm2):
    return math.hypot(lm2.x - lm1.x, lm2.y - lm1.y)

# Finger tip landmarks
TIP_IDS = {
    "Thumb": 4,
    "Index": 8,
    "Middle": 12,
    "Ring": 16,
    "Pinky": 20
}

last_action = None
no_gesture_counter = 0
terminate_counter = 0
last_action_time = time.time()

while True:
    success, img = cap.read()
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    results = hands.process(img_rgb)

    current_action = None

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            thumb_tip = hand_landmarks.landmark[TIP_IDS["Thumb"]]
            index_tip = hand_landmarks.landmark[TIP_IDS["Index"]]
            middle_tip = hand_landmarks.landmark[TIP_IDS["Middle"]]
            ring_tip = hand_landmarks.landmark[TIP_IDS["Ring"]]
            pinky_tip = hand_landmarks.landmark[TIP_IDS["Pinky"]]

            # Calculate distances
            thumb_index_dist = find_distance(thumb_tip, index_tip)
            thumb_middle_dist = find_distance(thumb_tip, middle_tip)
            thumb_ring_dist = find_distance(thumb_tip, ring_tip)
            thumb_pinky_dist = find_distance(thumb_tip, pinky_tip)
            index_middle_dist = find_distance(index_tip, middle_tip)
            middle_ring_dist = find_distance(middle_tip, ring_tip)

            # Define actions based on finger touches
            threshold = 0.05  # Adjust threshold based on hand/camera distance

            if thumb_index_dist < threshold:
                current_action = "Play/Pause"
            elif thumb_middle_dist < threshold:
                current_action = "Next Track"
            elif thumb_ring_dist < threshold:
                current_action = "Previous Track"
            elif thumb_pinky_dist < threshold:
                current_action = "Terminate"
            elif index_middle_dist < threshold:
                current_action = "Volume Up"
            elif middle_ring_dist < threshold:
                current_action = "Volume Down"

            # Perform action if different or enough time passed
            if current_action:
                current_time = time.time()
                if (current_action != last_action) or (current_time - last_action_time > 0.8):  # 0.8 sec gap

                    if current_action == "Terminate":
                        terminate_counter += 1
                        print(f"Terminate gesture detected {terminate_counter}/2")
                        if terminate_counter >= 2:
                            print("Terminating by gesture...")
                            cap.release()
                            cv2.destroyAllWindows()
                            sys.exit()
                    else:
                        terminate_counter = 0  # Reset if other gesture

                        if current_action == "Play/Pause":
                            pyautogui.press('playpause')
                        elif current_action == "Next Track":
                            pyautogui.press('nexttrack')
                        elif current_action == "Previous Track":
                            pyautogui.press('prevtrack')
                        elif current_action == "Volume Up":
                            pyautogui.press('volumeup')
                        elif current_action == "Volume Down":
                            pyautogui.press('volumedown')

                    last_action = current_action
                    last_action_time = current_time
                    no_gesture_counter = 0  # Reset no gesture counter

            # Show current action on screen
            if current_action:
                color = (0, 255, 255) if current_action != "Terminate" else (0, 0, 255)
                cv2.putText(img, current_action, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 2, color, 3)

    else:
        no_gesture_counter += 1

    # Reset last action if no gesture detected for some frames
    if no_gesture_counter > 10:
        last_action = None
        terminate_counter = 0

    cv2.imshow("Hand Gesture Music Controller", img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        print("Terminating by 'q' key...")
        break

cap.release()
cv2.destroyAllWindows()
