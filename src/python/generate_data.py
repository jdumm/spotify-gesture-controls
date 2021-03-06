import cv2
import os
import mediapipe as mp
import pandas as pd
import argparse
from collections import defaultdict

parser = argparse.ArgumentParser()
parser.add_argument("-f", "--file", help="data file name",
                    type=str, required=True)
parser.add_argument("-p", "--path", help="directory to save the data", type=str, default='.')
args = parser.parse_args()

file_name = args.file
path = args.path
if not file_name.endswith('.csv'):
    file_name += '.csv'
file_path = os.path.join(path, file_name)

mp_drawing = mp.solutions.drawing_utils
mp_hands = mp.solutions.hands
landmarks = [x.name for x in mp_hands.HandLandmark]
key2cmd = {
    'c': 'connect_cycle',
    'n': 'next_track',
    'b': 'previous_track',
    'p': 'pause_or_play',
    # 'v': 'volume_up',
    # 'd': 'volume_down',
    'l': 'like',
    # '1': 'skipback_1',
    '2': 'skipback_2',
    '3': 'skipback_3',
    '4': 'skipback_4',
    '5': 'skipback_5',
    '6': 'skipfwd_1',
    '7': 'skipfwd_2',
    '8': 'skipfwd_3',
    '9': 'skipfwd_4',
    '0': 'skipfwd_5',
    'm': 'mark_pos',
}
counts = defaultdict(lambda: 0)
data = []

cap = cv2.VideoCapture(0)
with mp_hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5) as hands:

    while True:
        ret, image = cap.read()

        image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)

        image.flags.writeable = False
        results = hands.process(image)

        key = chr(cv2.waitKey(10) & 0xFF)

        image.flags.writeable = True
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

        if results.multi_hand_landmarks:
            for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
                if handedness.classification[0].score <= .9:
                    continue

                new_data = {}
                for lm in landmarks:
                    new_data[lm + '_x'] = hand_landmarks.landmark[mp_hands.HandLandmark[lm]].x
                    new_data[lm + '_y'] = hand_landmarks.landmark[mp_hands.HandLandmark[lm]].y
                    new_data[lm + '_z'] = hand_landmarks.landmark[mp_hands.HandLandmark[lm]].z
                new_data['hand'] = handedness.classification[0].label

                if key2cmd.get(key, 'unknown') != 'unknown':
                    counts[key2cmd[key]] += 1
                    new_data['class'] = key2cmd[key]
                    data.append(new_data)

            mp_drawing.draw_landmarks(
                    image, hand_landmarks, mp_hands.HAND_CONNECTIONS)

        cv2.imshow('frame', image)

        s = f'\r'
        for k in counts:
            s += f'{k}: {counts[k]} '
        print(s, end='', flush=True)

        # Quit
        if key == 'q':
            break

        # Undo
        if key == 'z':
            last_key = data[-1]['class']
            counts[last_key] -= 1
            data.pop(-1)

        # Write what you have w/o exit
        if key == 'w':
            pd.DataFrame(data).to_csv(file_path, index=False)

print()
pd.DataFrame(data).to_csv(file_path, index=False)

cap.release()
cv2.destroyAllWindows()
