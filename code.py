import asyncio
import time
from adafruit_macropad import MacroPad
from app import App
from keys import Keys
from screen import ScreenListener
from pixels import PixelListener
from hid import InputDeviceListener
import usb_hid # type: ignore (part of CircuitPython standard libs)
from commands import Sleep, Resume

## DEPRECATED 
# Ensure backwards compatibility for the 2.x series
# So we don't have to change import statements in old macros
import sys
import commands
sys.modules['keyboard'] = commands
sys.modules['mouse'] = commands
sys.modules['pause'] = commands
sys.modules['sleep'] = commands
sys.modules['midi'] = commands
sys.modules['consumer'] = commands

MACRO_FOLDER = '/macros'

# Core objects
macropad = MacroPad()
screen = ScreenListener(macropad)
pixels = PixelListener(macropad)
hid = InputDeviceListener(macropad)

# State variables
last_time_seconds = time.monotonic()
keys = None
app_index = 0

class SleepTimer:
    def __init__(self, awake_ev, action_ev):
        self.timeout = None
        self.awake = awake_ev
        self.action = action_ev

    def set_timeout(self, timeout):
        self.timeout = timeout
        self.action.set()

    def register(self, keys):
        pass

    def pressed(self, keys, index):
        commands = keys[index].commands
        if not commands: return
        if isinstance(commands[0], Sleep):
            self.sleep()
        elif isinstance(commands[0], Resume):
            self.resume()

    def released(self, keys, index):
        pass

    def sleep(self):
        self.awake.clear()
        self.action.set()

    def resume(self):
        self.awake.set()
        self.action.set()

    def tick(self, keys, frames):
        pass

    async def loop(self):
        global keys
        while True:
            try:
                timeout = self.timeout if self.awake.is_set() else None
                await asyncio.wait_for(self.action.wait(), timeout)
                self.action.clear()
            except asyncio.TimeoutError:
                keys.press(Keys.KEY_SLEEP)
                keys.release(Keys.KEY_SLEEP)

awake_ev = asyncio.Event()
awake_ev.set()
action_ev = asyncio.Event()
sleep_timer = SleepTimer(awake_ev, action_ev)

# Fractions of a second that have elapsed since this method's last run
def elapsed_seconds():
    global last_time_seconds
    current_seconds = time.monotonic()
    elapsed_seconds = current_seconds - last_time_seconds
    last_time_seconds = current_seconds
    return elapsed_seconds

# Set the macro page (app) at the given index
def set_app(index):
    global app_index, keys, screen, sleep_timer

    macropad.keyboard.release_all()
    del keys
    screen.initialize()
    app_index = index
    sleep_timer.set_timeout(apps[app_index].timeout)

    screen.setTitle(apps[app_index].name)
    try:
        keys = Keys(apps[app_index])
        keys.addListener(sleep_timer)
        keys.addListener(hid)
        keys.addListener(screen)
        keys.addListener(pixels)
    except Exception as err:
        print(err)
        screen.setText("Error loading macro")

# Load available macros
screen.initialize()
apps = App.load_all(MACRO_FOLDER)
if not apps:
    screen.setTitle('NO MACRO FILES FOUND')
    while True:
        time.sleep(60.0)

# Load our first app page
screen.setTitle(' CONNECTING... ')
set_app(app_index)

async def keys_loop():
    global awake_ev, keys
    while True:
        event = macropad.keys.events.get()
        if (event and event.released):
            keys.press(Keys.KEY_RESUME)                  # Don't go to sleep!
            keys.release(Keys.KEY_RESUME)
        if not awake_ev.is_set():
            try:
                await asyncio.wait_for(awake_ev.wait(), 1.0)
            except asyncio.TimeoutError:
                pass
        elif event and event.pressed:                    # Key was pressed
            keys.press(event.key_number)
        elif event and event.released:                   # Key was released
            keys.release(event.key_number)

        await asyncio.sleep(0)

async def encoder_loop():
    global app_index, keys

    last_position = macropad.encoder
    macro_changed = False

    while True:
        macropad.encoder_switch_debounced.update()
        if last_position != macropad.encoder or macropad.encoder_switch_debounced.released:
            keys.press(Keys.KEY_RESUME)                  # Don't go to sleep!
            keys.release(Keys.KEY_RESUME)
        if not awake_ev.is_set():
            try:
                await asyncio.wait_for(awake_ev.wait(), 1.0)
            except asyncio.TimeoutError:
                pass
        elif macropad.encoder_switch and macropad.encoder < last_position:
            last_position = macropad.encoder             # Push down and turn (left)
            set_app((app_index - 1) % len(apps))
            macro_changed = True
        elif macropad.encoder_switch and macropad.encoder > last_position:
            last_position = macropad.encoder             # Push down and turn (right)
            set_app((app_index + 1) % len(apps))
            macro_changed = True
        elif macropad.encoder < last_position:           # Encoder counter-clockwise
            while macropad.encoder < last_position:
                keys.press(Keys.KEY_ENC_LEFT)
                last_position -= 1
            keys.release(Keys.KEY_ENC_LEFT)
        elif macropad.encoder > last_position:           # Encoder clockwise
            while macropad.encoder > last_position:
                keys.press(Keys.KEY_ENC_RIGHT)
                last_position += 1
            keys.release(Keys.KEY_ENC_RIGHT)
        elif macropad.encoder_switch_debounced.released and macro_changed:
            keys.press(Keys.KEY_LAUNCH)                  # Press the "new page" button
            keys.release(Keys.KEY_LAUNCH)
            macro_changed = False
        elif macropad.encoder_switch_debounced.released: # Encoder button "pressed"
            keys.press(Keys.KEY_ENC_BUTTON)
            keys.release(Keys.KEY_ENC_BUTTON)

        await asyncio.sleep(0)

async def ticks_loop():
    while True:
        keys.tick(elapsed_seconds())
        await asyncio.sleep(0.1)

async def main():
    await asyncio.gather(sleep_timer.loop(), keys_loop(), encoder_loop(), ticks_loop())

asyncio.run(main())
