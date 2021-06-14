import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pyautogui
import cv2
from datetime import datetime

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

    def __init__(self):
        self.marked_pos = None
        self.marked_uri = 'empty'
        self.prev_index_finger_tip_y = None
        self.prev_vol_datetime = None

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

            delay.reset_counter(20)
            delay.set_in_action(True)

        elif pose == 'connect_cycle':
            try:
                cur_dev_id = self.sp_client.current_playback()['device']['id']
                devs = self.sp_client.devices()['devices']
                cur_dev_idx = None
                for i, dev in enumerate(devs):
                    if dev['id'] == cur_dev_id:
                        cur_dev_idx = i

                new_dev_idx = cur_dev_idx - 1  # Loop backwards

                new_dev_id = devs[new_dev_idx]['id']
                self.sp_client.transfer_playback(new_dev_id)
            except spotipy.exceptions.SpotifyException as e:
                print("Tried to change device to connect_speaker (left)...")
                print(e)

            delay.reset_counter(20)
            delay.set_in_action(True)

        elif pose == 'next_track':
            try:
                self.sp_client.next_track()
            except spotipy.exceptions.SpotifyException as e:
                print("Tried to go to next track...")
                print(e)

            delay.reset_counter(10)
            delay.set_in_action(True)

        elif pose == 'previous_track':
            try:
                playback = self.sp_client.current_playback()
                if playback is not None:
                    cur_uri = playback['item']['uri']
                    cur_pos = playback['progress_ms']
                    # Check if we have a valid mark in this track to skip back to
                    if self.marked_pos is not None and self.marked_pos < cur_pos \
                            and cur_uri == self.marked_uri:
                        self.sp_client.seek_track(self.marked_pos)
                    else:
                        if cur_pos < 6*1000:  # Go to previous track
                            self.sp_client.previous_track(self.marked_pos)
                        else:  # Go back to beginning of track
                            self.sp_client.seek_track(0)
            except spotipy.exceptions.SpotifyException as e:
                print("Tried to go to previous track...")
                print(e)

            delay.reset_counter(10)
            delay.set_in_action(True)

        elif pose == 'volume_slider':
            try:
                playback = self.sp_client.current_playback()
                if playback is not None:
                    if self.prev_index_finger_tip_y is not None \
                            and self.prev_vol_datetime is not None \
                            and (datetime.now() - self.prev_vol_datetime).total_seconds() < 2.5:
                        cur_vol = playback['device']['volume_percent']
                        # print(f"DEBUG: Current volume {cur_vol}.")
                        # print(f"DEBUG: Landmarks: {lm[8*3+1]}")
                        cur_index_finger_tip_y = lm[8*3+1]
                        vol_diff = int((self.prev_index_finger_tip_y - cur_index_finger_tip_y)*200)
                        new_vol = max(0, min(100, cur_vol + vol_diff))
                        self.sp_client.volume(new_vol)
                        # print(f"DEBUG: New Volume: {new_vol}")
                        self.prev_index_finger_tip_y = lm[8*3+1]
                        self.prev_vol_datetime = datetime.now()
                    else:
                        self.prev_index_finger_tip_y = lm[8*3+1]
                        self.prev_vol_datetime = datetime.now()
                        # print(f"DEBUG: Setting volume reference point to {self.prev_index_finger_tip_y}")
                else:
                    print("No active playback device... start playing Spotify somewhere.")
            except spotipy.exceptions.SpotifyException as e:
                print("Tried to set volume...")
                print(e)

            delay.reset_counter()
            delay.set_in_action(True)

        # E.g. 'skipback_2' or 'skipfwd_5'
        elif pose[:9] == 'skipback_' or pose[:8] == 'skipfwd_':
            n = int(pose[-1]) * (-1 if pose[:9] == 'skipback_' else 1)
            try:
                playback = self.sp_client.current_playback()
                if playback is not None:
                    new_pos = max(playback['progress_ms']+int((3*n + 0.3)*1000), 0)
                    self.sp_client.seek_track(new_pos)
                    # print(f"DEBUG: Seek {(new_pos - playback['progress_ms'])/1000} seconds.")
                else:
                    print("No active playback device... start playing Spotify somewhere.")
            except spotipy.exceptions.SpotifyException as e:
                print("Tried to skipback...")
                print(e)

            self.angle_now = None
            delay.reset_counter()
            delay.set_in_action(True)

        elif pose == 'like':
            try:
                playback = self.sp_client.current_playback()
                if playback is not None and playback['is_playing']:
                    track_id = playback['progress_ms']
                    self.sp_client.current_user_saved_tracks_add(tracks=[track_id])
            except spotipy.exceptions.SpotifyException as e:
                print("Tried to like a song...")
                print(e)

            delay.reset_counter(20)
            delay.set_in_action(True)

        elif pose == 'mark_pos':
            try:
                playback = self.sp_client.current_playback()
                if playback is not None:  # and playback['is_playing']:
                    cur_uri = playback['item']['uri']
                    if self.marked_uri == 'empty' or self.marked_uri != cur_uri:
                        self.marked_pos = playback['progress_ms']
                        self.marked_uri = playback['item']['uri']
                        print(f"DEBUG: Position {self.marked_pos} marked.")
                    else:  # Delete old mark
                        print(f"DEBUG: Position {self.marked_pos} deleted.")
                        self.marked_pos = None
                        self.marked_uri = 'empty'

                else:
                    print("No active playback device... start playing Spotify somewhere.")
            except spotipy.exceptions.SpotifyException as e:
                print("Tried to mark_pos...")
                print(e)

            delay.reset_counter(20)  # Ignore a few more frames than usual to avoid undoing
            delay.set_in_action(True)




