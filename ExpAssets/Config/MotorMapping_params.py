### Klibs Parameter overrides ###

#########################################
# Runtime Settings
#########################################
collect_demographics = True
manual_demographics_collection = False
manual_trial_generation = False
run_practice_blocks = True
multi_user = False
view_distance = 57 # in centimeters, 57cm = 1 deg of visual angle per cm of screen
allow_hidpi = True

#########################################
# Available Hardware
#########################################
eye_tracker_available = False
eye_tracking = False

#########################################
# Environment Aesthetic Defaults
#########################################
default_fill_color = (128, 128, 128, 255)
default_color = (255, 255, 255, 255)
default_font_size = 0.45
default_font_unit = 'deg'
default_font_name = 'Roboto-Medium'

#########################################
# EyeLink Settings
#########################################
manual_eyelink_setup = False
manual_eyelink_recording = False

saccadic_velocity_threshold = 20
saccadic_acceleration_threshold = 5000
saccadic_motion_threshold = 0.15

#########################################
# Experiment Structure
#########################################
multi_session_project = False
trials_per_block = 50
blocks_per_experiment = 2
table_defaults = {}
conditions = ['PP', 'MI', 'CC']
default_condition = 'PP'

#########################################
# Development Mode Settings
#########################################
dm_trial_show_mouse = False
dm_ignore_local_overrides = False
show_gamepad_debug = False
max_trials_per_block = False

#########################################
# Data Export Settings
#########################################
primary_table = "trials"
unique_identifier = "userhash"
exclude_data_cols = ["created"]
append_info_cols = ["random_seed"]
datafile_ext = ".txt"

#########################################
# PROJECT-SPECIFIC VARS
#########################################
input_mappings = {
    'normal': (1, 1),
    'backwards': (-1, -1),
    'inverted_x': (-1, 1),
    'inverted_y': (1, -1),
}
training_mapping = 'normal'
test_mapping = 'normal'

collect_kviq = True
cursor_size = 1.0  # degrees
