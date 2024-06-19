import obspython as obs
import logging
import cv2
import numpy as np
import math

# Configuration
check_interval = 1  # Check every 1 second
silence_threshold = -50.0  # dB
stillness_threshold = 0.01  # Percentage of change in the frame

# Global variables
is_paused = False
last_frame = None

# Set up logging
logging.basicConfig(filename='obs_auto_pause_resume.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def script_description():
    return "Automatically pauses and resumes recording based on stillness and silence."

def script_update(settings):
    global check_interval, silence_threshold, stillness_threshold
    check_interval = obs.obs_data_get_int(settings, "check_interval")
    silence_threshold = obs.obs_data_get_double(settings, "silence_threshold")
    stillness_threshold = obs.obs_data_get_double(settings, "stillness_threshold")
    logging.info(f"Updated settings: check_interval={check_interval}, silence_threshold={silence_threshold}, stillness_threshold={stillness_threshold}")

def script_defaults(settings):
    obs.obs_data_set_default_int(settings, "check_interval", 1)
    obs.obs_data_set_default_double(settings, "silence_threshold", -50.0)
    obs.obs_data_set_default_double(settings, "stillness_threshold", 0.01)

def script_properties():
    props = obs.obs_properties_create()
    obs.obs_properties_add_int(props, "check_interval", "Check Interval (seconds)", 1, 60, 1)
    obs.obs_properties_add_float(props, "silence_threshold", "Silence Threshold (dB)", -100.0, 0.0, 0.1)
    obs.obs_properties_add_float(props, "stillness_threshold", "Stillness Threshold (%)", 0.0, 1.0, 0.01)
    return props

def get_current_frame():
    source = obs.obs_frontend_get_current_scene()
    if source is None:
        return None
    source = obs.obs_scene_from_source(source)
    if source is None:
        return None
    item = obs.obs_scene_find_source_recursive(source, "Video Capture Device")
    if item is None:
        return None
    source = obs.obs_sceneitem_get_source(item)
    if source is None:
        return None
    frame = obs.obs_source_get_frame(source)
    if frame is None:
        return None
    return frame

def check_stillness_and_silence():
    global is_paused, last_frame

    try:
        # Get the current frame
        current_frame = get_current_frame()
        if current_frame is None:
            logging.warning("No video frame found.")
            return

        # Convert frame to grayscale
        current_frame_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)

        # Calculate frame difference
        if last_frame is not None:
            frame_diff = cv2.absdiff(last_frame, current_frame_gray)
            non_zero_count = np.count_nonzero(frame_diff)
            total_pixels = frame_diff.size
            stillness = (non_zero_count / total_pixels) < stillness_threshold
        else:
            stillness = False

        # Update last frame
        last_frame = current_frame_gray

        # Get the current audio level
        audio_source = obs.obs_get_output_source(0)
        if audio_source is not None:
            audio_level = obs.obs_source_get_volume(audio_source)
            obs.obs_source_release(audio_source)

            # Convert volume to dB
            audio_level_db = 20 * math.log10(audio_level) if audio_level > 0 else -100.0

            # Check for silence
            silence = audio_level_db < silence_threshold
        else:
            logging.warning("No audio source found.")
            silence = False

        # Pause or resume recording
        if stillness and silence and not is_paused:
            obs.obs_frontend_recording_pause()
            is_paused = True
            logging.info("Recording paused due to stillness and silence.")
        elif not stillness and not silence and is_paused:
            obs.obs_frontend_recording_resume()
            is_paused = False
            logging.info("Recording resumed due to activity.")
    except Exception as e:
        logging.error(f"Error in check_stillness_and_silence: {e}")

    # Schedule next check
    obs.timer_add(check_stillness_and_silence, check_interval * 1000)
