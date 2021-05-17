import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pyautogui
import cv2

from utils import *


class SpotifyControls:
    """
        This class execute Spotify API commands based on the hand pose predicted from HandPoses.
        The gesture controller uses a specific spotipy API call for each pose.

        Keyword Arguments:
            screen_proportion {float}: the proportion of gesture controller interaction area in 'mouse'
                class, ie, proportion of area to mapper mouse movement.
                (default: {0.75})
            len_moving_average {float}: the moving average is used to
                calculate the average of midpoint of five-fingers landmarks
                in an array with the history of this midpoint. To this calculus, the
                len_moving_average will be the length of this midpoint history array.
                When this value has the tradeoff: increase this number improves the mouse
                sensitivity, but delays the mouse iteration (midpoint update)
                (default: {10})
    """

    def __init__(self, screen_proportion=0.75, len_moving_average=10):
        self.screen_proportion = screen_proportion

        self.screen_width, self.screen_height = pyautogui.size()
        self.camera_width, self.camera_height = None, None
        self.x_start_screen, self.y_start_screen = None, None
        self.x_end_screen, self.y_end_screen = None, None

        self.angle_now = None

        self.x_moving_average = np.array([])
        self.y_moving_average = np.array([])
        self.len_moving_average = len_moving_average

        self.username = os.environ['USERNAME']

        # Authenticate with proper scopes
        self.scope = "user-read-playback-state,user-modify-playback-state,user-library-modify"

        self.sp_client = spotipy.Spotify(
            client_credentials_manager=SpotifyOAuth(
                scope=self.scope,
                cache_path='/tmp/.cache-'+self.username,
                username=self.username,
            )
        )

    def draw_mouse_rectangle(self, frame):
        """
        This method draw a rectangle of the effective interaction area to mapping mouse movement
        """

        if self.camera_width is None:
            image_height, image_width, _ = frame.shape

            self.update_width_height(image_height, image_width)

        cv2.rectangle(frame, (self.x_start_screen, self.y_start_screen),
                      (self.x_end_screen, self.y_end_screen), (255, 255, 255), 2)

    def update_width_height(self, image_height, image_width):
        """
        This method update the width and height of the camera and the points
        that limit the effective interaction area to mapping mouse movement
        """

        self.camera_width, self.camera_height = image_width, image_height
        self.x_start_screen = int((1 - self.screen_proportion) * self.camera_width / 2)
        self.y_start_screen = int((1 - self.screen_proportion) * self.camera_height / 2)
        self.x_end_screen = int((1 + self.screen_proportion) * self.camera_width / 2)
        self.y_end_screen = int((1 + self.screen_proportion) * self.camera_height / 2)

    def execute_cmd(self, pose, lm, delay, frame):
        """
            Execute Movement Method

            This method execute movements (gesture controller) using pose class.

            Arguments:
                pose {string}: predicted hand pose
                lm {string}: hands landmarks detected by HandDetect
                delay {Delay}: class responsible to provoke delays on the execution frames
                frame {cv2 Image, np.ndarray}: webcam frame
        """
        if pose == 'pause_or_play':
            print(pose)
            try:
                playback = self.sp_client.current_playback()
                if playback is None or not playback['is_playing']:
                    self.sp_client.start_playback()
                else:
                    self.sp_client.pause_playback()
            except spotipy.exceptions.SpotifyException as e:
                # print(e)
                # print("Trying to find an active device...")
                devs = self.sp_client.devices()['devices']
                if len(devs) > 0:
                    dev_id = devs[0]['id']
                    self.sp_client.transfer_playback(dev_id)
                else:
                    print("Tried to turn the volume up...")
                    print("Sorry, user needs to log into a device with Spotify!")

            self.angle_now = None
            delay.reset_counter()
            delay.set_in_action(True)

        elif pose == 'volume_up':
            print(pose)
            try:
                cur_vol = self.sp_client.current_playback()['device']['volume_percent']
                new_vol = min(cur_vol+10, 100)
                self.sp_client.volume(new_vol)
            except spotipy.exceptions.SpotifyException as e:
                print("Tried to turn the volume up...")
                print(e)

            self.angle_now = None
            delay.reset_counter()
            delay.set_in_action(True)

        elif pose == 'volume_down':
            print(pose)
            try:
                cur_vol = self.sp_client.current_playback()['device']['volume_percent']
                new_vol = max(cur_vol-10, 0)
                self.sp_client.volume(new_vol)
            except spotipy.exceptions.SpotifyException as e:
                print("Tried to turn the volume down...")
                print(e)

            self.angle_now = None
            delay.reset_counter()
            delay.set_in_action(True)

        elif pose == 'connect_cycle':
            try:
                cur_dev_id = self.sp_client.current_playback()['device']['id']
                devs = self.sp_client.devices()['devices']
                cur_dev_idx = None
                for i, dev in enumerate(devs):
                    if dev['id'] == cur_dev_id:
                        cur_dev_idx = i

                # Still testing this logic to move to different Connect devices
                new_dev_idx = \
                    cur_dev_idx - 1 if pose == 'connect_speaker' else (cur_dev_idx + 1) % len(devs)

                new_dev_id = devs[new_dev_idx]['id']
                self.sp_client.transfer_playback(new_dev_id)
            except spotipy.exceptions.SpotifyException as e:
                print("Tried to change device to connect_speaker (left)...")
                print(e)

            self.angle_now = None
            delay.reset_counter()
            delay.set_in_action(True)

        elif pose == 'next_track':
            try:
                self.sp_client.next_track()
            except spotipy.exceptions.SpotifyException as e:
                print("Tried to go to next track...")
                print(e)

            self.angle_now = None
            delay.reset_counter()
            delay.set_in_action(True)

        elif pose == 'previous_track':
            try:
                self.sp_client.previous_track()
            except spotipy.exceptions.SpotifyException as e:
                print("Tried to go to previous track...")
                print(e)

            self.angle_now = None
            delay.reset_counter()
            delay.set_in_action(True)

        elif pose == 'like':
            try:
                playback = self.sp_client.current_playback()
                if playback is not None and playback['is_playing']:
                    track_id = playback['item']['id']
                    self.sp_client.current_user_saved_tracks_add(tracks=[track_id])
            except spotipy.exceptions.SpotifyException as e:
                print("Tried to like a song...")
                print(e)

            self.angle_now = None
            delay.reset_counter()
            delay.set_in_action(True)

        else:
            self.angle_now = None
        return None



