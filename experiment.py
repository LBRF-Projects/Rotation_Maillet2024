# -*- coding: utf-8 -*-

__author__ = "Austin Hurst"

from math import sqrt
from random import randrange, shuffle
from ctypes import c_int, byref

import sdl2
import klibs
from klibs import P
from klibs.KLExceptions import TrialException
from klibs.KLTrialFactory import TrialIterator
from klibs.KLGraphics import fill, flip, blit
from klibs.KLGraphics import KLDraw as kld
from klibs.KLEventQueue import flush, pump
from klibs.KLUtilities import angle_between, point_pos, deg_to_px, px_to_deg
from klibs.KLUtilities import line_segment_len as linear_dist
from klibs.KLTime import CountDown, precise_time
from klibs.KLText import add_text_style
from klibs.KLCommunication import message
from klibs.KLUserInterface import (
    any_key, mouse_pos, ui_request, hide_cursor, smart_sleep,
)

from KVIQ import KVIQ
from gamepad import gamepad_init, get_controllers
from klibs_wip import Block

# Define colours for use in the experiment
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
MIDGREY = (128, 128, 128)
TRANSLUCENT_RED = (255, 0, 0, 96)

# Define constants for working with gamepad data
AXIS_MAX = 32768
TRIGGER_MAX = 32767


class MotorMapping(klibs.Experiment):

    def setup(self):

        # Prior to starting the task, run through the KVIQ
        handedness = self.db.select(
            'participants', columns=['handedness'], where={'id': P.participant_id}
        )[0][0]
        if P.collect_kviq:
            kviq = KVIQ(handedness == "l")
            responses = kviq.run()
            for movement, dat in responses.items():
                dat['participant_id'] = P.participant_id
                dat['movement'] = movement
                self.db.insert(dat, table='kviq')

        # Initialize stimulus sizes and layout
        screen_h_deg = (P.screen_y / 2.0) / deg_to_px(1.0)
        fixation_size = deg_to_px(0.5)
        fixation_thickness = deg_to_px(0.06)
        self.cursor_size = deg_to_px(P.cursor_size)
        self.target_size = deg_to_px(0.3)
        self.target_dist_min = deg_to_px(5.0)
        self.target_dist_max = deg_to_px(7.0)
        self.cursor_dist_max = deg_to_px(8.0)
        self.lower_middle = (P.screen_c[0], int(P.screen_y * 0.75))
        self.msg_loc = (P.screen_c[0], int(P.screen_y * 0.4))

        # Initialize task stimuli
        self.cursor = kld.Ellipse(self.cursor_size, fill=TRANSLUCENT_RED)
        self.target = kld.Ellipse(self.target_size, fill=WHITE)
        self.fixation = kld.FixationCross(
            fixation_size, fixation_thickness, rotation=45, fill=WHITE
        )
        if P.development_mode and P.show_gamepad_debug:
            add_text_style('debug', '0.3deg')

        # Generate additional task demo stimuli
        target_dist = (2 * self.target_dist_min + self.target_dist_max) / 3
        dist = target_dist / 2 # Distance between screen center & arrow midpoint
        tl = deg_to_px(3.5) # Arrow tail length
        tls = deg_to_px(1.5) # Arrow tail length (small)
        tw = deg_to_px(0.15) # Arrow tail thickness
        hlw = deg_to_px(0.4) # Arrow head length/width
        lt = deg_to_px(0.05) # Arrow outline thickness
        self.demo_arrows = {
            'cursor90': demo_arrow(tl, tw, hlw, hlw, dist, angle=90),
            'cursor135': demo_arrow(tl, tw, hlw, hlw, dist, angle=135),
            'joystick135': demo_arrow(tl, tw, hlw, hlw, dist, outline=lt, angle=135),
            'joystick180': demo_arrow(tl, tw, hlw, hlw, dist, outline=lt, angle=180),
            'cursor90_small': demo_arrow(tls, tw, hlw, hlw, dist * 0.65, angle=90),
            'cursor_adj': demo_arrow(
                (tl + tls) / 2, tw, hlw, hlw, dist * 1.4, angle=120, rotation=162
            ),
        }

        # Define quadrants for targets
        self.quadrants = {
            'a': (0, 90),
            'b': (90, 180),
            'c': (180, 270),
            'd': (270, 360),
        }

        # Initialize gamepad (if present)
        self.gamepad = None
        gamepad_init()
        controllers = get_controllers()
        if len(controllers):
            self.gamepad = controllers[0]
            self.gamepad.initialize()
            print(self.gamepad._info)
        self.joystick_map = "normal"
        self.rotation = 0

        # Define error messages for the task
        err_txt = {
            "too_soon": (
                "Too soon!\nPlease wait for the target to appear before responding."
            ),
            "too_slow": "Too slow!\nPlease try to respond faster.",
            "start_triggers": (
                "Please fully release the trigger before the start of each trial."
            ),
            "stick_mi": (
                "Joystick moved!\n"
                "Please try to only *imagine* moving the joystick to the target\n"
                "without actually performing the movement."
            ),
            "stick_cc": (
                "Joystick moved!\n"
                "Please respond using the trigger alone, without\n"
                "moving the cursor."
            ),
            "continue": "Press any button to continue.",
        }
        self.errs = {}
        for key, txt in err_txt.items():
            self.errs[key] = message(txt, align="center")

        # Define custom session structure & trial counts
        structure = [
            Block({}, label='baseline', trials=40),
            Block({}, label='pretest', trials=10),
            Block({}, label='training', trials=200),
            Block({}, label='posttest', trials=10),
            Block({}, label='washout', trials=40),
        ]
        self.blocks, self.block_labels = generate_trials(structure)
        P.blocks_per_experiment = len(self.blocks)
        self.phase = None

        # Run a visual demo explaining the task
        self.task_demo()


    def block(self):
        # Hide mouse cursor if not already hidden
        hide_cursor()

        # Generate target quadrants for the block to avoid repeat locations
        trial_count = self.blocks[P.block_number - 1].length
        self.quadrant_list = []
        while len(self.quadrant_list) < trial_count:
            tmp = list(self.quadrants.keys())
            shuffle(tmp)
            # Avoid repeating the same quadrant twice
            if len(self.quadrant_list) and self.quadrant_list[-1] == tmp[0]:
                tmp.reverse()
            self.quadrant_list += tmp

        block_msgs = {
            "baseline": (
                "For this first set of trials, please respond to targets physically "
                "by\nusing the joystick to move the cursor over them."
            ),
            "pretest": (
                "Now you will have a chance to practice the rotated task yourself.\n"
                "Try your best to still respond quickly as you adapt to the 45° shift."
            ),
            "training_PP": (
                "For the next phase of the task, please continue to respond quickly "
                "to\ntargets using the joystick. Try your best to adapt to the "
                "rotation."
            ),
            "training_MI": (
                "When you are ready, you will begin to practice the rotated task using "
                "motor imagery.\nRemember to not physically move the joystick when "
                "imagining the movement!\n\n"
                "Try your best to mentally practice adapting to the rotation."
            ),
            "training_CC": (
                "For the next phase of the task, please respond to targets *without*\n"
                "moving the joystick by simply pressing the trigger after a brief "
                "delay.\n\n"
                "Try to get a reaction time as close to 1.500 as you can."
            ),
            "posttest": (
                "For this next part of the task, you will perform a few more rotated "
                "trials\n*physically* to assess how well you adjusted to the rotation."
            ),
            "washout": (
                "For the final phase of the task, please continue to respond to "
                "targets\nphysically by using the joystick to move the cursor.\n\n"
                "Note that the rotation may feel a little different than before."
            )
        }

        # Handle different phases of the experiment
        self.phase = self.block_labels[P.block_number - 1]
        self.trial_type = P.condition if self.phase == "training" else "PP"
        self.rotation = 0 if self.phase in ["baseline", "washout"] else -45
        if self.phase == "training":
            block_msg = block_msgs["training_" + P.condition]
            if P.condition == "MI":
                self.training_instructions_mi()
        else:
            block_msg = block_msgs[self.phase]
            if self.phase == "pretest":
                self.rotation_instructions()

        # Show block start message
        msg = message(block_msg, align="center")
        msg2 = message("Press any button to start.")
        self.show_feedback(msg, duration=2.0, location=self.msg_loc)
        fill()
        blit(msg, 5, self.msg_loc)
        blit(msg2, 5, self.lower_middle)
        flip()
        wait_for_input(self.gamepad)


    def trial_prep(self):

        # Every 40 trials during training block, do block break
        msgs = {
            "CC": "the time estimation task.",
            "MI": "practicing the task mentally.",
            "PP": "practicing the task physically.",
        }
        break_txt = [
            "Take a short break!",
            "Whenever you're ready, press any button to resume " + msgs[self.trial_type]
        ]
        if self.trial_type != "CC":
            break_txt.append("\nKeep in mind the 45° counter-clockwise rotation!")
        if self.phase == "training" and P.trial_number > 1:
            if (P.trial_number - 1) % 40 == 0:
                self.show_demo_text(
                    break_txt, stim_set=[], msg_y=int(0.45 * P.screen_y)
                )

        # Generate trial factors
        quadrant = self.quadrant_list[P.trial_number - 1]
        angle_min, angle_max = self.quadrants[quadrant]
        self.target_angle = randrange(angle_min, angle_max, 1)
        self.target_dist = randrange(self.target_dist_min, self.target_dist_max)
        self.target_loc = vector_to_pos(P.screen_c, self.target_dist, self.target_angle)
        self.target_onset = randrange(1000, 3000, 100)

        # Add timecourse of events to EventManager
        self.evm.add_event('target_on', onset=self.target_onset)
        self.evm.add_event('timeout', onset=15000, after='target_on')

        # Set mouse to screen centre & ensure mouse pointer hidden
        mouse_pos(position=P.screen_c)
        hide_cursor()


    def trial(self):

        # Initialize trial response data
        movement_rt = None
        contact_rt = None
        response_rt = None
        initial_angle = None
        axis_data = []
        last_x, last_y = (-1, -1)

        # Get joystick mapping for the trial
        mod_x, mod_y = P.input_mappings[self.joystick_map]

        # Initialize trial stimuli
        fill(MIDGREY)
        blit(self.fixation, 5, P.screen_c)
        blit(self.cursor, 5, P.screen_c)
        flip()

        target_on = None
        target_drawn = False
        first_loop = True
        over_target = False
        while self.evm.before('timeout'):
            q = pump()
            ui_request(queue=q)

            # Get latest joystick/trigger data from gamepad
            if self.gamepad:
                self.gamepad.update()

            # Filter, standardize, and possibly invert the axis & trigger data
            lt, rt = self.get_triggers()
            jx, jy = self.get_stick_position(rotation=self.rotation)
            input_time = precise_time()
            cursor_pos = (
                P.screen_c[0] + int(jx * self.cursor_dist_max * mod_x),
                P.screen_c[1] + int(jy * self.cursor_dist_max * mod_y)
            )

            # Handle input based on trial type and trials phase
            triggers_released = lt < 0.2 and rt < 0.2
            cursor_movement = linear_dist(cursor_pos, P.screen_c)
            if target_on:
                # As soon as cursor moves after target onset, log movement RT
                if not movement_rt and cursor_movement > 0:
                    movement_rt = input_time - target_on
                # Once cursor has moved slightly away from origin, log initial angle
                if not initial_angle and px_to_deg(cursor_movement) > 1.0:
                    # Wait at least 50 ms after first movement before calculating angle
                    # (otherwise we get lots of 270s due to no y-axis change)
                    if input_time - (target_on + movement_rt) > 0.05:
                        initial_angle = vector_angle(P.screen_c, cursor_pos)

            # Detect/handle different types of trial error
            err = "NA"
            if cursor_movement > self.cursor_size:
                if self.trial_type == "MI":
                    err = "stick_mi"
                elif self.trial_type == "CC":
                    err = "stick_cc"
                elif self.trial_type == "PP" and not target_on:
                    err = "too_soon"
            if first_loop:
                first_loop = False
                if not triggers_released:
                    err = "start_triggers"
            elif self.evm.before('target_on'):
                if not triggers_released:
                    err = "too_soon"

            # If the participant did something wrong, show them a feedback message
            if err != "NA":
                self.show_feedback(self.errs[err], duration=2.0)
                fill()
                blit(self.errs[err], 5, P.screen_c)
                blit(self.errs['continue'], 5, self.lower_middle)
                flip()
                wait_for_input(self.gamepad)
                if target_on:
                    # NOTE: Do we want to recycle stick MI/CC errors as well?
                    # If so, should we still record when people make these errors
                    # regardless?
                    break
                else:
                    # If target hasn't appeared yet, recycle the trial
                    raise TrialException("Recycling trial!")

            # Log continuous cursor x/y data for each frame
            if target_on and cursor_movement:
                # Only log samples where position actually changes (to save space)
                any_change = (cursor_pos[0] != last_x) or (cursor_pos[1] != last_y)
                if any_change:
                    axis_sample = (
                        int((input_time - target_on) * 1000), # timestamp
                        cursor_pos[0], # joystick x
                        cursor_pos[1], # joystick y
                    )
                    axis_data.append(axis_sample)
                last_x = cursor_pos[0]
                last_y = cursor_pos[1]
            
            # Actually draw stimuli to the screen
            redraw = self.trial_type == "PP" or not target_on
            if redraw:
                fill()
                blit(self.fixation, 5, P.screen_c)
                if self.evm.after('target_on'):
                    blit(self.target, 5, self.target_loc)
                    target_drawn = True
                blit(self.cursor, 5, cursor_pos)
                if P.development_mode and P.show_gamepad_debug:
                    self.show_gamepad_debug()
                flip()

            # Get timestamp for when target drawn to the screen
            if not target_on and target_drawn:
                target_on = precise_time()
                
            # Check if the cursor is currently over the target
            dist_to_target = linear_dist(cursor_pos, self.target_loc)
            if dist_to_target < (self.cursor_size / 2):
                # Get timestamp for when cursor first touches target
                if not contact_rt:
                    contact_rt = precise_time() - target_on
                # To prevent participants from holding triggers down while moving the
                # stick (making the task much easier), the experiment only counts the
                # cursor as being over the target if both triggers are released while
                # over it.
                triggers_released = lt < 0.2 and rt < 0.2
                if not over_target and triggers_released:
                    over_target = True
            else:
                over_target = False

            # If either trigger pressed when it is possible to respond, end the trial
            can_respond = over_target or self.trial_type != "PP"
            if can_respond and (lt > 0.5 or rt > 0.5):
                response_rt = precise_time() - target_on
                break

        # Show RT feedback for 1 second (may remove this)
        if response_rt:
            rt_sec = "{:.3f}".format(response_rt)
            feedback = message(rt_sec)
            self.show_feedback(feedback, duration=1.5)
        elif err == "NA":
            feedback = self.errs['too_slow']
            self.show_feedback(feedback, duration=2.5)

        # Write raw axis data to database
        if err == "NA":
            rows = []
            for timestamp, stick_x, stick_y in axis_data:
                rows.append({
                    'participant_id': P.participant_id,
                    'block_num': P.block_number,
                    'trial_num': P.trial_number,
                    'time': timestamp,
                    'stick_x': stick_x,
                    'stick_y': stick_y,
                })
            self.db.insert(rows, table='gamepad')

        return {
            "block_num": P.block_number,
            "trial_num": P.trial_number,
            "phase": self.phase,
            "trial_type": self.trial_type,
            "rotation": self.rotation,
            "target_onset": self.target_onset if target_on else "NA",
            "target_dist": px_to_deg(self.target_dist),
            "target_angle": self.target_angle,
            "movement_rt": "NA" if movement_rt is None else movement_rt * 1000,
            "contact_rt": "NA" if contact_rt is None else contact_rt * 1000,
            "response_rt": "NA" if response_rt is None else response_rt * 1000,
            "initial_angle": "NA" if initial_angle is None else initial_angle,
            "err": err,
            "target_x": self.target_loc[0],
            "target_y": self.target_loc[1],
        }


    def trial_clean_up(self):
        pass


    def clean_up(self):
        
        end_txt = (
            "You're all done, thanks for participating!\nPress any button to exit."
        )
        end_msg = message(end_txt, align='center')
        fill()
        blit(end_msg, 5, P.screen_c)
        flip()
        wait_for_input(self.gamepad)

        if self.gamepad:
            self.gamepad.close()


    def show_demo_text(self, msgs, stim_set, duration=2.0, wait=True, msg_y=None):
        msg_x = int(P.screen_x / 2)
        msg_y = int(P.screen_y * 0.25) if msg_y is None else msg_y
        half_space = deg_to_px(0.5)

        fill()
        if not isinstance(msgs, list):
            msgs = [msgs]
        for msg in msgs:
            txt = message(msg, align="center")
            blit(txt, 8, (msg_x, msg_y))
            msg_y += txt.height + half_space
    
        for stim, locs in stim_set:
            if not isinstance(locs, list):
                locs = [locs]
            for loc in locs:
                blit(stim, 5, loc)
        flip()
        if P.development_mode and wait:
            smart_sleep(500)
        else:
            smart_sleep(duration * 1000)
        if wait:
            wait_for_input(self.gamepad)


    def task_demo(self):
        # Initialize task stimuli for the demo
        target_dist = (2 * self.target_dist_min + self.target_dist_max) / 3
        target_loc = vector_to_pos(P.screen_c, target_dist, 250)
        feedback = message("{:.3f}".format(1.841))
        base_layout = [
            (self.fixation, P.screen_c),
            (self.cursor, P.screen_c),
        ]
        
        # Actually run through demo
        self.show_demo_text(
            "Welcome to the experiment! This tutorial will help explain the task.",
            [(self.fixation, P.screen_c), (self.cursor, P.screen_c)]
        )
        self.show_demo_text(
            ("On each trial of the task, a small white target will appear at a random "
             "distance\nfrom the fixation cross at the middle of the screen."),
            [(self.fixation, P.screen_c), (self.target, target_loc),
             (self.cursor, P.screen_c)]
        )
        self.show_demo_text(
            ("Your job will be to quickly move the red cursor over top of the target "
             "when it appears,\nusing the joystick to control it."),
            [(self.fixation, P.screen_c), (self.target, target_loc),
             (self.cursor, (target_loc[0] + 4, target_loc[1] + 6))]
        )
        self.show_demo_text(
            ("Once you have moved the cursor over the target, please squeeze the "
             "trigger on the\njoystick to end the trial. You will be shown "
             "your reaction time."),
            [(feedback, P.screen_c)]
        )
        target_dist = (self.target_dist_min + self.target_dist_max) / 2
        target_loc = vector_to_pos(P.screen_c, target_dist, 165)
        if P.condition == "MI":
            feedback = message("{:.3f}".format(3.347))
            self.show_demo_text(
                ("In some parts of the study, you will be asked to perform this task "
                "using motor imagery,\ni.e. imagine what it would *look and feel like* "
                "to move the cursor using the joystick."),
                [(self.fixation, P.screen_c), (self.target, target_loc),
                (self.cursor, P.screen_c)]
            )
            self.show_demo_text(
                ("When the target appears on an imagery trial, try to mentally "
                 "simulate performing\nthe arm movements required to move the cursor "
                 "over the target (without actually moving)."),
                [(self.fixation, P.screen_c), (self.target, target_loc),
                 (self.cursor, P.screen_c)]
            )
            self.show_demo_text(
                ("Please keep your hand resting on the joystick normally as you "
                 "imagine\nperforming the movement."),
                [(self.fixation, P.screen_c), (self.target, target_loc),
                 (self.cursor, P.screen_c)]
            )
            self.show_demo_text(
                ("Once you have imagined the movement and are over the target (in your "
                 "mind's eye),\nplease physically squeeze the trigger on the "
                 "joystick to end the trial."),
                [(feedback, P.screen_c)]
            )
        if P.condition == "CC":
            self.show_demo_text(
                ("In some parts of the study, instead of moving the cursor to the "
                "target, you will be\nasked to simply press the trigger 1.5 seconds "
                "after the target appears."),
                [(self.fixation, P.screen_c), (self.target, target_loc),
                (self.cursor, P.screen_c)]
            )
            self.show_demo_text(
                ("As usual, pressing the trigger will end the trial and display your "
                 "reaction time.\nPlease try to get a reaction time as close to 1.500 "
                 "as possible."),
                [(feedback, P.screen_c)]
            )


    def rotation_instructions(self):
        # Initialize task stimuli for the demo
        target_dist = (2 * self.target_dist_min + self.target_dist_max) / 3
        cursor_loc = vector_to_pos(P.screen_c, target_dist, 225)
        cursor_loc_miss = vector_to_pos(P.screen_c, target_dist, 180)
        target_loc = (cursor_loc[0] + 4, cursor_loc[1] + 6)
        feedback = message("{:.3f}".format(2.431))
        
        # Actually run through demo
        self.show_demo_text(
            ("Now that you have gotten the hang of the task, we are going to\n"
             "make it a bit more challenging."),
            [(self.fixation, P.screen_c), (self.cursor, P.screen_c)]
        )
        self.show_demo_text(
            ("Specifically, cursor movement will now be rotated 45° counter-clockwise "
             "such that\njoystick movement (arrow outline) and cursor movement (solid "
             "arrow) are no longer aligned."),
            [(self.fixation, P.screen_c), (self.target, target_loc),
             self.demo_arrows["cursor90"], self.demo_arrows["joystick135"],
             (self.cursor, cursor_loc_miss)]
        )
        self.show_demo_text(
            ("This may take some time to get used to. Do your best to try and adapt "
             "to\nthe rotation by adjusting your joystick movement to compensate."),
            [(self.fixation, P.screen_c), (self.target, target_loc),
             self.demo_arrows["cursor135"], self.demo_arrows["joystick180"],
             (self.cursor, cursor_loc)]
        )
        self.show_demo_text(
            ("Your job is to try and adapt your movements to the rotation so that "
             "moving the\ncursor straight to the target eventually feels normal "
             "and automatic again."),
            [(self.fixation, P.screen_c), (self.target, target_loc),
             self.demo_arrows["cursor135"],
             (self.cursor, cursor_loc)]
        )
        self.show_demo_text(
            ("Despite the rotation, please continue to try and respond to targets\n"
             "as quickly as possible!"),
            [(feedback, P.screen_c)]
        )


    def training_instructions_mi(self):
        # Initialize task stimuli for the demo
        target_dist = (2 * self.target_dist_min + self.target_dist_max) / 3
        cursor_loc = vector_to_pos(P.screen_c, target_dist, 225)
        cursor_loc_miss = vector_to_pos(P.screen_c, target_dist, 180)
        target_loc = (cursor_loc[0] + 4, cursor_loc[1] + 6)
        
        # Actually run through demo
        self.show_demo_text(
            ("Now that you have had a chance to practice the rotated task "
             "*physically*, in the\nnext phase you will practice the rotation "
             "*mentally* using motor imagery."),
            [(self.fixation, P.screen_c), (self.cursor, P.screen_c)]
        )
        self.show_demo_text(
            ("Do your best to mentally simulate the arm and wrist movements needed to\n"
             "bring the cursor to the target, keeping in mind the 45° rotation."),
            [(self.fixation, P.screen_c), (self.target, target_loc),
             self.demo_arrows["joystick180"],
             (self.cursor, P.screen_c)]
        )
        self.show_demo_text(
            ("Make sure to imagine how the movements would *feel* in your arm and "
             "wrist\nin addition to how the cursor would move on screen in response."),
            [(self.fixation, P.screen_c), (self.target, target_loc),
             self.demo_arrows["joystick180"], self.demo_arrows["cursor135"], 
             (self.cursor, P.screen_c)]
        )
        self.show_demo_text(
            ("If you imagine yourself making mistakes at first (e.g. moving the "
             "joystick directly towards\nthe target instead of compensating for the "
             "rotation) this is normal and expected!"),
            [(self.fixation, P.screen_c), (self.target, target_loc),
             self.demo_arrows["cursor90_small"],
             (self.cursor, P.screen_c)]
        )
        self.show_demo_text(
            ("When this happens, simply imagine performing a correction movement\n"
             "to bring the cursor to the target before responding."),
            [(self.fixation, P.screen_c), (self.target, target_loc),
             self.demo_arrows["cursor90_small"], self.demo_arrows["cursor_adj"],
             (self.cursor, P.screen_c)]
        )


    def show_gamepad_debug(self):
        if not self.gamepad:
            return

        # Get latest axis info
        rs_x, rs_y = self.gamepad.right_stick()
        ls_x, ls_y = self.gamepad.left_stick()
        lt = self.gamepad.left_trigger()
        rt = self.gamepad.right_trigger()
        dpad_x, dpad_y = self.gamepad.dpad()

        # Blit axis state info to the bottom-right of the screen
        info_txt = "\n".join([
            "Left Stick: ({0}, {1})",
            "Right Stick: ({2}, {3})",
            "Left Trigger: {4}",
            "Right Trigger: {5}",
            "D-Pad: ({6}, {7})",
        ]).format(ls_x, ls_y, rs_x, rs_y, lt, rt, dpad_x, dpad_y)
        pad_info = message(info_txt, style='debug')
        blit(pad_info, 1, (0, P.screen_y))


    def show_feedback(self, msg, duration=1.0, location=None):
        feedback_time = CountDown(duration)
        if not location:
            location = P.screen_c
        while feedback_time.counting():
            ui_request()
            if self.gamepad:
                self.gamepad.update()
            fill()
            blit(msg, 5, location)
            flip()
        
    
    def get_stick_position(self, left=False, rotation=0):
        if self.gamepad:
            if left:
                raw_x, raw_y = self.gamepad.left_stick()
            else:
                raw_x, raw_y = self.gamepad.right_stick()
        else:
            # If no gamepad, approximate joystick with mouse movement
            mouse_x, mouse_y = mouse_pos()
            scale_factor = AXIS_MAX / self.cursor_dist_max
            raw_x = int((mouse_x - P.screen_c[0]) * scale_factor)
            raw_y = int((mouse_y - P.screen_c[1]) * scale_factor)

        return joystick_scaled(raw_x, raw_y, rotation=rotation)

    
    def get_triggers(self):
        if self.gamepad:
            raw_lt = self.gamepad.left_trigger()
            raw_rt = self.gamepad.right_trigger()
        else:
            # If no gamepad, emulate trigger press with mouse click
            raw_lt, raw_rt = (0, 0)
            mouse_x, mouse_y = c_int(0), c_int(0)
            if sdl2.SDL_GetMouseState(byref(mouse_x), byref(mouse_y)) != 0:
                # Ignore mouse button down for first 100 ms to ignore start-trial click
                if self.evm.trial_time_ms > 100:
                    raw_lt, raw_rt = (32767, 32767)

        return (raw_lt / TRIGGER_MAX, raw_rt / TRIGGER_MAX)


def generate_trials(structure):

    block_set = []
    block_labels = []

    for block in structure:
        if block.practice and not P.run_practice_blocks:
            continue

        block_labels.append(block.label)
        tmp = block.get_trials()
        if P.max_trials_per_block != False:
            tmp = tmp[:P.max_trials_per_block]

        trials = TrialIterator(tmp)
        trials.practice = block.practice
        block_set.append(trials)

    return block_set, block_labels


def joystick_scaled(x, y, deadzone = 0.2, rotation = 0):

    # Check whether the current stick x/y exceeds the specified deadzone
    amplitude = min(1.0, sqrt(x ** 2 + y ** 2) / AXIS_MAX)
    if amplitude < deadzone:
        return (0, 0)

    # Smooth/standardize output coordinates to be on a circle, by capping
    # maximum amplitude at AXIS_MAX and converting stick angle/amplitude
    # to coordinates.
    angle = angle_between((0, 0), (x, y))
    amp_new = (amplitude - deadzone) / (1.0 - deadzone)
    xs, ys = point_pos((0, 0), amp_new, angle, rotation=-rotation, return_int=False)

    return (xs, ys)

    
def wait_for_input(gamepad=None):
    valid_input = [
        sdl2.SDL_KEYDOWN,
        sdl2.SDL_MOUSEBUTTONDOWN,
        sdl2.SDL_CONTROLLERBUTTONDOWN,
    ]
    flush()
    user_input = False
    while not user_input:
        if gamepad:
            gamepad.update()
        q = pump()
        ui_request(queue=q)
        for event in q:
            if event.type in valid_input:
                user_input = True
                break


def vector_angle(p1, p2):
    # Gets the angle of a vector relative to directly upwards
    return angle_between(p1, p2, rotation=-90, clockwise=True)


def vector_to_pos(origin, amplitude, angle, return_int=True):
    # Gets the (x,y) coords of a vector's endpoint given its origin/angle/length
    # (0 degrees is directly up, 90 deg. is directly right, etc.)
    return point_pos(origin, amplitude, angle, rotation=-90, clockwise=True)


def demo_arrow(tl, tt, hl, ht, dist, angle, rotation=None, outline=None):
    # Creates an arrow with a given rotation and location for the task instructions
    if not rotation:
        rotation = angle
    if outline:
        stroke = [outline, WHITE, klibs.STROKE_CENTER]
        arrow = kld.Arrow(tl, tt, hl, ht, fill=None, stroke=stroke, rotation=rotation)
    else:
        arrow = kld.Arrow(tl, tt, hl, ht, fill=WHITE, rotation=rotation)
    loc = vector_to_pos(P.screen_c, dist, angle + 90)
    return (arrow, loc)
