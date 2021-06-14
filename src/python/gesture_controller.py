import numpy as np
import pyautogui
import imutils
from mss import mss
from PIL import Image

import cv2
import copy
import argparse

from hand_poses import HandPoses
from hand_detect import HandDetect
from delay import Delay
from spotify_controls import SpotifyControls


parser = argparse.ArgumentParser()
parser.add_argument("--detect_threshold", help="minimum percentage of a hand prediction",
                    type=float, default=0.90)
parser.add_argument("--pose_threshold", help="SVC threshold in classification confidence", 
                    type=float, default=0.90)
parser.add_argument("--path_classifier", help="path to classifier",
                    type=str, default='models/spotify_gesture_cmd_model.pkl')
parser.add_argument("--moving_average", help="minimum percentage of pose prediction of last frames",
                    type=float, default=0.85)
parser.add_argument("--frames_in", help="number of frames to consider to predict a pose when in action", 
                    type=int, default=20)
parser.add_argument("--frames_out", help="number of frames to consider to predict a pose", 
                    type=int, default=40)
parser.add_argument("--show_lm", help="show hand landmarks", 
                    type=bool, default=True)
args = parser.parse_args()


hand_detect = HandDetect(detect_threshold=args.detect_threshold)
hand_pose = HandPoses(pose_threshold=args.pose_threshold,
                      name_classifier=args.path_classifier)
# This will log into Spotify using your personal account with a separate popup window
spotify_controller = SpotifyControls()
delay = Delay(hand_pose.classifier.classes_, moving_average=args.moving_average, frames_in_action=args.frames_in, frames_out=args.frames_out)

webcam = True
if webcam:
    cap = cv2.VideoCapture(0)
else:
    sct = mss()

with hand_detect.mp_hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.5) as hands:
    while True:
        if webcam:
            ret, image = cap.read()
        else:  # screenshot
            ret = True
            # image = pyautogui.screenshot()
            # image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            # Higher fps with mss for screen grab:
            mon = sct.monitors[0]
            image = np.array(sct.grab(mon))
            image = np.flip(image[:, :, :3], 2)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


        if not ret:  # Image was not successfully read!
            print('\rNo image!  Is a webcam available?', '', end='')
            continue

        raw_frame = copy.deepcopy(image)

        image = cv2.flip(image, 1)
        image_height, image_width, _ = image.shape
        #spotify_controller.draw_mouse_rectangle(image)

        for (pose, confidence), (lm, mp_lm) in hand_detect.detect_hand(hands=hands,
                                                              image=raw_frame,
                                                              hand_pose=hand_pose,
                                                              delay=delay):
            if args.show_lm:
                hand_detect.mp_drawing.draw_landmarks(
                    image, mp_lm, hand_detect.mp_hands.HAND_CONNECTIONS)

            if pose is not None:
                cv2.putText(image, f"{pose}: ({confidence:.2f})",
                            (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 100), 2)
                print(f"\r{pose}: ({confidence:.2f})                   ", "", end="")

                spotify_controller.execute_cmd(pose=pose, lm=lm, delay=delay, frame=image)

            else:
                cv2.putText(image, f"Idle", (30, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 100), 2)
                if delay.ignore_frames:
                    cv2.putText(image, f"Position locked", (30, 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 100), 2)
        key = (cv2.waitKey(10) & 0xFF)

        image = cv2.resize(image, (int(image_width * .6),
                                   int(image_height * .6)), interpolation=cv2.INTER_AREA)
        # if webcam:
        cv2.imshow('frame', image)

        if key == ord('q'):
            break

if webcam:
    cap.release()
cv2.destroyAllWindows()
