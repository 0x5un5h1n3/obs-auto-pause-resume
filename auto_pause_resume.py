import obspython as obs
import logging

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
