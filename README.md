# Motor Imagery and Implicit Adaptation - Maillet 2024

This repository contains the experiment code for a study testing whether motor imagery can effectively practice implicit adaptation to a visuomotor rotation. The purpose of the study is to determine whether participants can adapt to sensorimotor distortions by *mentally simulating* visual and kinaesthetic feedback for their imagined movements in the absence of actual physical feedback.

![MotorMapping](task.gif)

On each trial, a target will appear on the screen at a random distance and angle from fixation after a random delay. Once the target appears, the task of the participant is to move the cursor (translucent red circle) from the middle of the screen to be hovering over the target (small white dot) using a joystick. They then need to squeeze the trigger on the joystick while over the target to end the trial.

The experiment has five phases: baseline, pre-test, training, post-test, and washout:

* The **baseline** phase consists of 40 non-rotated physical practice trials to familiarize participants with the task. 
* The **pre-test** phase consists of 10 physical practice trials with a 45° counter-clockwise rotation applied between the joystick movement and the cursor movement (such that moving the joystick straight forward will move the cursor to the top-left).
* The **training** phase differs depending on the experiment condition: some people continue to practice the rotation physically, some are asked to practice adapting to the rotation using motor imagery, and others are asked to simply squeeze the trigger 1.5 seconds after each target appears (control group). This phase consists of 200 trials.
* During the **post-test** phase, all participants perform 10 more trials of the rotated task physically using the joystick to measure overall adaptation.
* During the **washout** phase, all participants perform 40 more trials of the task physically *with the rotation removed*, allowing measurement of after-effects (i.e. implicit adaptation).

Reaction times to targets and initial angles of movement are recorded, allowing the magnitudes of adaptation and after-effects to be compared between phases and across groups.

## Requirements

This task is programmed in Python 3.9 using the [KLibs framework](https://github.com/a-hurst/klibs). It has been developed and tested on recent versions of macOS and Linux, but should also work without issue on Windows systems.

To use the task with a joystick (as intended), you will also need a USB or Bluetooth  that is supported by your computer. The task has been tested with Logitech Extreme 3D Pro joysticks, but other similar joysticks will likely work as long as an axis/button mapping is added to the code (see `mappings.py` in the `ExpAssets/Resources/code` folder). Additionally, most USB/wireless gamepads (e.g. Sony Dualshock 4) should work without any special configuration, though during piloting we noticed that participants would simply rotate the gamepad itself to realign the the movement of the joystick with that of the rotated cursor (thus undermining the main manipulation of the study).

If no joystick is available, mouse movement/clicking will be used in place of the joystick/trigger (respectively).


## Getting Started

### Installation

To install the task and its dependencies in a self-contained Python environment, run the following commands in a terminal window inside the same folder as this README:

```bash
pip install pipenv
pipenv install
```
These commands should create a fresh environment the task with all its dependencies installed. Note that to run commands using this environment, you will need to prefix them with `pipenv run` (e.g. `pipenv run klibs run 15.6`).

Alternatively, to install the dependencies for the task in your global Python environment, simply run the following command in a terminal window:

```bash
pip install https://github.com/a-hurst/klibs/releases/download/0.7.7b1/klibs-0.7.7b1.tar.gz
```

### Running the Experiment

This task is a KLibs experiment, meaning that it is run using the `klibs` command at the terminal (running the 'experiment.py' file using Python directly will not work).

To run the experiment, navigate to the task folder in Terminal and run `klibs run [screensize]`, replacing `[screensize]` with the diagonal size of your display in inches (e.g. `klibs run 21.5` for a 21.5-inch monitor). Note that the stimulus sizes for the study assume that a) the screen size for the monitor has been specified accurately, and b) that participants are seated approximately 57 cm from the screen.

If you just want to test the program out for yourself and skip demographics collection, you can add the `-d` flag to the end of the command to launch the experiment in development mode.

#### Optional Settings

This task has three possible between-subjects conditions: physical practice (PP), motor imagery (MI), and control condition (CC).

To choose which condition to run, launch the experiment with the `--condition` or `-c` flag, followed by either `PP`, `MI`, or `CC`. For example, if you wanted to run a participant in the motor imagery condition on a computer with a 15.6-inch monitor, you would run 

```
klibs run 15.6 --condition MI
```

If no condition is manually specified, the experiment program will default to physical practice.
 

### Exporting Data

To export data from the task, simply run

```
klibs export
```

while in the root of the task directory. This will export the trial data for each participant into individual tab-separated text files in the project's `ExpAssets/Data` subfolder.

KVIQ scores and raw gamepad joystick data can likewise be exported from the data base with `klibs export -t kviq` and `klibs export -t gamepad`, respectively.
