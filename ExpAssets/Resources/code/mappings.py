import re
from sdl2 import gamecontroller as gc
from sdl2.ext.common import raise_sdl_err

# To add a mapping for an unrecognized controller, simply add a new line to the
# CUSTOM_MAPPINGS list with its name, GUID, and mapping. The first two values
# can be copied from the console after launching the task with an unknown
# controller. For the mapping itself you can try using the default 'stick_map'
# and modify it as needed, mapping axes (e.g. 'a0') and buttons (e.g. 'b1')
# to specific standard names (e.g. 'a', 'b', 'x', 'y', 'righty', 'leftx').

stick_map = {
    'rightx': 'a0',
    'righty': 'a1',
    'a': 'b1',
    'righttrigger': 'b0',
}

CUSTOM_MAPPINGS = [
    ['03007a126d04000014c2000005020', 'Logitech Attack 3', stick_map],
    ['0300ea9f6d04000015c2000011570000', 'Logitech Extreme 3D pro', stick_map],
]


def _sanitize_mapping_name(name):
    sdlname = re.sub(r"[\s_-]", "", name).lower()
    b = gc.SDL_GameControllerGetButtonFromString(sdlname.encode('utf-8'))
    if b != gc.SDL_CONTROLLER_BUTTON_INVALID:
        return sdlname
    axis = gc.SDL_GameControllerGetAxisFromString(sdlname.encode('utf-8'))
    if axis != gc.SDL_CONTROLLER_AXIS_INVALID:
        return sdlname
    return None

def _axis_from_name(name):
    sdlname = re.sub(r"[\s_-]", "", name).lower()
    axis = gc.SDL_GameControllerGetAxisFromString(sdlname.encode('utf-8'))
    if axis == gc.SDL_CONTROLLER_AXIS_INVALID:
        raise ValueError("Invalid axis name '{0}'.".format(name))
    return axis

def _button_from_name(name):
    sdlname = re.sub(r"[\s_-]", "", name).lower()
    b = gc.SDL_GameControllerGetButtonFromString(sdlname.encode('utf-8'))
    if b == gc.SDL_CONTROLLER_BUTTON_INVALID:
        raise ValueError("Invalid button name '{0}'.".format(name))
    return b

def _create_controller_mapping(guid, name, buttonmap):
    # External-facing version should accept joystick as input, do validation
    mappings = []
    for control, value in buttonmap.items():
        sdlcontrol = _sanitize_mapping_name(control)
        if not sdlcontrol:
            e = "'{0}' is not a valid SDL2 game controller binding name."
            raise ValueError(e.format(control))
        mappings.append("{0}:{1}".format(sdlcontrol, value))
    return "{0},{1},{2},".format(guid, name, ",".join(mappings))

def add_controller_mapping(guid, name, buttonmap):
    mapping = _create_controller_mapping(guid, name, buttonmap)
    ret = gc.SDL_GameControllerAddMapping(mapping.encode('utf-8'))
    if ret == -1:
        raise_sdl_err("adding button map for '{0}' joystick".format(name))
