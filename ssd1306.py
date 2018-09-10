# MicroPython SSD1306 OLED driver, I2C and SPI interfaces

import time
import framebuf


# register definitions
SET_CONTRAST        = const(0x81)
SET_ENTIRE_ON       = const(0xa4)
SET_NORM_INV        = const(0xa6)
SET_DISP            = const(0xae)
SET_MEM_ADDR        = const(0x20)
SET_COL_ADDR        = const(0x21)
SET_PAGE_ADDR       = const(0x22)
SET_DISP_START_LINE = const(0x40)
SET_SEG_REMAP       = const(0xa0)
SET_MUX_RATIO       = const(0xa8)
SET_COM_OUT_DIR     = const(0xc0)
SET_DISP_OFFSET     = const(0xd3)
SET_COM_PIN_CFG     = const(0xda)
SET_DISP_CLK_DIV    = const(0xd5)
SET_PRECHARGE       = const(0xd9)
SET_VCOM_DESEL      = const(0xdb)
SET_CHARGE_PUMP     = const(0x8d)


class SSD1306:
    """A base class for drivers targetting SSD1306 based display.

    :param width: Width of the screen in pixels.
    :param height: Height of the screen in pixels.
    :param external_vcc: True if an external high-voltage source is connected.
    """
    def __init__(self, width, height, external_vcc):
        self.width = width
        self.height = height
        self.external_vcc = external_vcc
        self.pages = self.height // 8
        # Note the subclass must initialize self.framebuf to a framebuffer.
        # This is necessary because the underlying data buffer is different
        # between I2C and SPI implementations (I2C needs an extra byte).
        self.poweron()
        self.init_display()

    def init_display(self):
        for cmd in (
            SET_DISP | 0x00, # off
            # address setting
            SET_MEM_ADDR, 0x00, # horizontal
            # resolution and layout
            SET_DISP_START_LINE | 0x00,
            SET_SEG_REMAP | 0x01, # column addr 127 mapped to SEG0
            SET_MUX_RATIO, self.height - 1,
            SET_COM_OUT_DIR | 0x08, # scan from COM[N] to COM0
            SET_DISP_OFFSET, 0x00,
            SET_COM_PIN_CFG, 0x02 if self.height == 32 else 0x12,
            # timing and driving scheme
            SET_DISP_CLK_DIV, 0x80,
            SET_PRECHARGE, 0x22 if self.external_vcc else 0xf1,
            SET_VCOM_DESEL, 0x30, # 0.83*Vcc
            # display
            SET_CONTRAST, 0xff, # maximum
            SET_ENTIRE_ON, # output follows RAM contents
            SET_NORM_INV, # not inverted
            # charge pump
            SET_CHARGE_PUMP, 0x10 if self.external_vcc else 0x14,
            SET_DISP | 0x01): # on
            self.write_cmd(cmd)
        self.fill(0)
        self.show()

    def poweroff(self):
        """Turn off the display."""
        self.write_cmd(SET_DISP | 0x00)

    def contrast(self, contrast):
        """Set contrast.

        :param contrast: Constrast value between 0 and 255.
        """
        self.write_cmd(SET_CONTRAST)
        self.write_cmd(contrast)

    def invert(self, invert):
        self.write_cmd(SET_NORM_INV | (invert & 1))

    def show(self):
        """Sends the framebuffer to the screen."""
        x0 = 0
        x1 = self.width - 1
        if self.width == 64:
            # displays with width of 64 pixels are shifted by 32
            x0 += 32
            x1 += 32
        self.write_cmd(SET_COL_ADDR)
        self.write_cmd(x0)
        self.write_cmd(x1)
        self.write_cmd(SET_PAGE_ADDR)
        self.write_cmd(0)
        self.write_cmd(self.pages - 1)
        self.write_framebuf()

    def fill(self, col):
        """Fill the entire screen with a particular color.

        :param col: Color between 0x000000 and 0xFFFFFF.
        """
        self.framebuf.fill(col)

    def pixel(self, x, y, col):
        """Set the color of a particular pixel.

        :param x: Horizontal coordinate.
        :param y: Vertical coordinate.
        :param col: Color between 0x000000 and 0xFFFFFF.
        """
        self.framebuf.pixel(x, y, col)

    def scroll(self, dx, dy):
        """Translates the screen content.

        :param dx: Horizontal shifting value in pixels.
        :param dy: Vertical shifting value in pixels.
        """
        self.framebuf.scroll(dx, dy)

    def text(self, string, x, y, col=1):
        """Display a text.

        :param x: Horizontal coordinate.
        :param y: Vertical coordinate.
        :param col: Color between 0x000000 and 0xFFFFFF (optional).
        """
        self.framebuf.text(string, x, y, col)

    def triangle_gauge(self, x, y, value):
        """A 16x8 triangle gauge.

        :param x: Horizontal coordinate.
        :param y: Vertical coordinate.
        :param value: Gauge value between 0.0 and 1.0.
        """

        if(value > 1.0):
            value = 1.0
        elif(value < 0.0):
            value = 0.0

        #Draw contour of the gauge
        for i in range(0, 16):
            #Horizontal line
            self.framebuf.pixel(x+i, y+7, 0xFFFFFF)
        for i in range(0, 8):
            #Vertical line
            self.framebuf.pixel(x+15, y+i, 0xFFFFFF)
            #Diagonal
            self.framebuf.pixel(x+2*i, y+7-i, 0xFFFFFF)
            self.framebuf.pixel(x+2*i+1, y+7-i, 0xFFFFFF)

        #Fill gauge depending on value
        num_bar = round(value*10.0)
        for i in range(0,num_bar+1):
            x_bar = x + i + 4
            ymin = y + 7 - int(i/2.0) - 1
            ymax = y + 7

            for y_bar in range(ymin, ymax):
                self.framebuf.pixel(x_bar, y_bar, 0xFFFFFF)


    def battery_gauge(self, x, y, value):
        """A 16x8 battery gauge.

        :param x: Horizontal coordinate.
        :param y: Vertical coordinate.
        :param value: Gauge value between 0.0 and 1.0.
        """

        if(value > 1.0):
            value = 1.0
        elif(value < 0.0):
            value = 0.0

        #Draw contour of the gauge
        for i in range(0, 14):
            #Upper and lower horizontal line
            self.framebuf.pixel(x+i, y, 0xFFFFFF)
            self.framebuf.pixel(x+i, y+7, 0xFFFFFF)
        for i in range(0, 8):
            #Left Vertical line
            self.framebuf.pixel(x, y+i, 0xFFFFFF)
        for i in range(1, 7):
            #Right Vertical line
            self.framebuf.pixel(x+15, y+i, 0xFFFFFF)
        #Finishig touches
        self.framebuf.pixel(x+13, y+1, 0xFFFFFF)
        self.framebuf.pixel(x+14, y+1, 0xFFFFFF)
        self.framebuf.pixel(x+14, y+6, 0xFFFFFF)
        self.framebuf.pixel(x+13, y+6, 0xFFFFFF)

        #Fill gauge depending on value
        num_bar = round(value*13.0)
        for i in range(0,num_bar+1):
            x_bar = x + i + 1
            ymin = 1
            ymax = 6
            if(i == 13 or i == 14):
                ymin = 2
                ymax = 5

            for i in range(ymin, ymax+1):
                self.framebuf.pixel(x_bar, y+i, 0xFFFFFF)


    def signal_gauge(self, x, y, value):
        """A 8x8 4 level signal gauge.

        :param x: Horizontal coordinate.
        :param y: Vertical coordinate.
        :param value: Gauge value between 0.0 and 1.0.
        """

        if(value > 1.0):
            value = 1.0
        elif(value < 0.0):
            value = 0.0

        #Fill gauge depending on value
        num_bar = round(value*4.0)

        if(num_bar > 0):
            self.framebuf.pixel(x, y+7, 0xFFFFFF)

        if(num_bar > 1):
            self.framebuf.pixel(x, y+5, 0xFFFFFF)
            self.framebuf.pixel(x+1, y+5, 0xFFFFFF)
            self.framebuf.pixel(x+2, y+6, 0xFFFFFF)
            self.framebuf.pixel(x+2, y+7, 0xFFFFFF)

        if(num_bar > 2):
            self.framebuf.pixel(x, y+3, 0xFFFFFF)
            self.framebuf.pixel(x+1, y+3, 0xFFFFFF)
            self.framebuf.pixel(x+2, y+3, 0xFFFFFF)
            self.framebuf.pixel(x+3, y+4, 0xFFFFFF)
            self.framebuf.pixel(x+4, y+5, 0xFFFFFF)
            self.framebuf.pixel(x+4, y+6, 0xFFFFFF)
            self.framebuf.pixel(x+4, y+7, 0xFFFFFF)

        if(num_bar > 3):
            self.framebuf.pixel(x, y+1, 0xFFFFFF)
            self.framebuf.pixel(x+1, y+1, 0xFFFFFF)
            self.framebuf.pixel(x+2, y+1, 0xFFFFFF)
            self.framebuf.pixel(x+3, y+1, 0xFFFFFF)
            self.framebuf.pixel(x+4, y+2, 0xFFFFFF)
            self.framebuf.pixel(x+5, y+2, 0xFFFFFF)
            self.framebuf.pixel(x+5, y+3, 0xFFFFFF)
            self.framebuf.pixel(x+6, y+4, 0xFFFFFF)
            self.framebuf.pixel(x+6, y+5, 0xFFFFFF)
            self.framebuf.pixel(x+6, y+6, 0xFFFFFF)
            self.framebuf.pixel(x+6, y+7, 0xFFFFFF)

class SSD1306_I2C(SSD1306):
    """A I2C driver for SSD1306 based display.

    :param width: Width of the screen in pixels.
    :param height: Height of the screen in pixels.
    :param i2c: The `I2C` object to use.
    :param address: The I2C address of the device (optional).
    :param external_vcc: True if an external high-voltage source is connected (optional).
    :param res: The `Pin` object of the pin connected to the `RES` line.
    """
    def __init__(self, width, height, i2c, addr=0x3c, external_vcc=False, res=None):
        self.i2c = i2c
        self.addr = addr
        self.temp = bytearray(2)
        self.res = res
        # Add an extra byte to the data buffer to hold an I2C data/command byte
        # to use hardware-compatible I2C transactions.  A memoryview of the
        # buffer is used to mask this byte from the framebuffer operations
        # (without a major memory hit as memoryview doesn't copy to a separate
        # buffer).
        self.buffer = bytearray(((height // 8) * width) + 1)
        self.buffer[0] = 0x40  # Set first byte of data buffer to Co=0, D/C=1
        self.framebuf = framebuf.FrameBuffer1(memoryview(self.buffer)[1:], width, height)
        super().__init__(width, height, external_vcc)

    def write_cmd(self, cmd):
        self.temp[0] = 0x80 # Co=1, D/C#=0
        self.temp[1] = cmd
        self.i2c.writeto(self.addr, self.temp)

    def write_framebuf(self):
        # Blast out the frame buffer using a single I2C transaction to support
        # hardware I2C interfaces.
        self.i2c.writeto(self.addr, self.buffer)

    def poweron(self):
        if(self.res != None):
            self.res.value(1)
            time.sleep_ms(5)
            self.res.value(0)
            time.sleep_ms(10)
            self.res.value(1)


class SSD1306_SPI(SSD1306):
    """A SPI driver for SSD1306 based display.

    :param width: Width of the screen in pixels.
    :param height: Height of the screen in pixels.
    :param spi: The `SPI` object to use.
    :param dc: The `Pin` object of the pin connected to the `DC` line.
    :param res: The `Pin` object of the pin connected to the `RES` line.
    :param cs: The `Pin` object of the pin connected to the `CS` line.
    :param external_vcc: True if an external high-voltage source is connected (optional).
    """
    def __init__(self, width, height, spi, dc, res, cs, external_vcc=False):
        self.rate = 10 * 1024 * 1024
        dc.init(dc.OUT, value=0)
        res.init(res.OUT, value=0)
        cs.init(cs.OUT, value=1)
        self.spi = spi
        self.dc = dc
        self.res = res
        self.cs = cs
        self.buffer = bytearray((height // 8) * width)
        self.framebuf = framebuf.FrameBuffer1(self.buffer, width, height)
        super().__init__(width, height, external_vcc)

    def write_cmd(self, cmd):
        self.spi.init(baudrate=self.rate, polarity=0, phase=0)
        self.cs.high()
        self.dc.low()
        self.cs.low()
        self.spi.write(bytearray([cmd]))
        self.cs.high()

    def write_framebuf(self):
        self.spi.init(baudrate=self.rate, polarity=0, phase=0)
        self.cs.high()
        self.dc.high()
        self.cs.low()
        self.spi.write(self.buffer)
        self.cs.high()

    def poweron(self):
        self.res.value(1)
        time.sleep_ms(5)
        self.res.value(0)
        time.sleep_ms(10)
        self.res.value(1)
