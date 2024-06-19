import obspython as obs
import math
import numpy as np
import cv2
import logging

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler = logging.FileHandler('obs_auto_pause_resume.log')
handler.setFormatter(formatter)
logger.addHandler(handler)

class AutoPauseResume:
    def __init__(self):
        self.check_interval = 1  # Check every 1 second
        self.silence_threshold = -50.0  # dB
        self.stillness_threshold = 0.01  # Percentage of change in the frame
        self.is_paused = False
        self.last_frame = None
        self.timer = None

    def script_description(self):
        return "Automatically pauses and resumes recording based on stillness and silence."

    def script_update(self, settings):
        self.check_interval = obs.obs_data_get_int(settings, "check_interval")
        self.silence_threshold = obs.obs_data_get_double(settings, "silence_threshold")
        self.stillness_threshold = obs.obs_data_get_double(settings, "stillness_threshold")
        logger.info(f"Updated settings: check_interval={self.check_interval}, silence_threshold={self.silence_threshold}, stillness_threshold={self.stillness_threshold}")

    def script_defaults(self, settings):
        obs.obs_data_set_default_int(settings, "check_interval", 1)
        obs.obs_data_set_default_double(settings, "silence_threshold", -50.0)
        obs.obs_data_set_default_double(settings, "stillness_threshold", 0.01)

    def script_properties(self):
        props = obs.obs_properties_create()
        obs.obs_properties_add_int(props, "check_interval", "Check Interval (seconds)", 1, 60, 1)
        obs.obs_properties_add_float(props, "silence_threshold", "Silence Threshold (dB)", -100.0, 0.0, 0.1)
        obs.obs_properties_add_float(props, "stillness_threshold", "Stillness Threshold (%)", 0.0, 1.0, 0.01)
        return props

    def get_current_frame(self):
        source = obs.obs_frontend_get_current_scene()
        if source is None:
            logger.warning("No video frame found.")
            return None
        source = obs.obs_scene_from_source(source)
        if source is None:
            logger.warning("No video frame found.")
            return None
        item = obs.obs_scene_find_source_recursive(source, "Video Capture Device")
        if item is None:
            logger.warning("No video frame found.")
            return None
        source = obs.obs_sceneitem_get_source(item)
        if source is None:
            logger.warning("No video frame found.")
            return None
        frame = obs.obs_source_get_frame(source)
        if frame is None:
            logger.warning("No video frame found.")
            return None
        return frame

    def check_stillness_and_silence(self):
        try:
            # Get the current frame
            current_frame = self.get_current_frame()
            if current_frame is None:
                return

            # Convert frame to grayscale
            current_frame_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)

            # Calculate frame difference
            if self.last_frame is not None:
                frame_diff = cv2.absdiff(self.last_frame, current_frame_gray)
                non_zero_count = np.count_nonzero(frame_diff)
                total_pixels = frame_diff.size
                stillness = (non_zero_count / total_pixels) < self.stillness_threshold
            else:
                stillness = False

            # Update last frame
            self.last_frame = current_frame_gray

            # Get the current audio level
            audio_source = obs.obs_get_output_source(0)
            if audio_source is not None:
                audio_level = obs.obs_source_get_volume(audio_source)
                obs.obs_source_release(audio_source)

                # Convert volume to dB
                audio_level_db = 20 * math.log10(audio_level) if audio_level > 0 else -100.0

                # Check for silence
                silence = audio_level_db < self.silence_threshold
            else:
                logger.warning("No audio source found.")
                silence = False

            # Pause or resume recording
            if stillness and silence and not self.is_paused:
                obs.obs_frontend_recording_pause()
                self.is_paused = True
                logger.info("Recording paused due to stillness and silence.")
            elif not stillness and not silence and self.is_paused:
                obs.obs_frontend_recording_resume()
                self.is_paused = False
                logger.info("Recording resumed due to activity.")
        except Exception as e:
            logger.error(f"Error in check_stillness_and_silence: {e}")

        # Schedule next check
        if self.timer is None:
            self.timer = obs.timer_add(self.check_stillness_and_silence, self.check_interval * 1000)
        else:
            obs.timer_reset(self.timer, self.check_interval * 1000)

    def script_load(self, settings):
        logger.info("Script loaded.")
        self.check_stillness_and_silence()

    def script_unload(self):
        logger.info("Script unloaded.")
        if self.timer is not None:
            obs.timer_remove(self.timer)
            self.timer = None

auto_pause_resume = AutoPauseResume()
