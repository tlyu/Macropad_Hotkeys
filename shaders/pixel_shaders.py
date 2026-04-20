import asyncio

class PressedShader:
    MAX_FRAMES = 4
    neopixels = None
    key_index = None
    frame_index = None
    start_color = None

    def __init__(self, neopixels, key_index):
        self.neopixels = neopixels
        self.key_index = key_index

    async def loop(self):
        if self.key_index < len(self.neopixels): # This is an addressable range
            start_color = self.neopixels[self.key_index]
        else:
            return
        for frame_index in range(PressedShader.MAX_FRAMES, 0, -1):
            color_val =  0xFF * (frame_index / PressedShader.MAX_FRAMES)
            self.neopixels[self.key_index] = (color_val, color_val, color_val)
            self.neopixels.show()
            await asyncio.sleep(0.1)

        self.neopixels[self.key_index] = start_color
        self.neopixels.show()
