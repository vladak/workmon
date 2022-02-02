"""
Wrapper class for controlling Adafruit USB light bulb.
"""

import logging
import os
import queue
import threading
import time

import serial


class Bulb:
    """
    Supports on/off/blink for red, green, yellow.
    """

    RED_ON = 0x11
    RED_OFF = 0x21
    RED_BLINK = 0x41

    YELLOW_ON = 0x12
    YELLOW_OFF = 0x22
    YELLOW_BLINK = 0x42

    GREEN_ON = 0x14
    GREEN_OFF = 0x24
    GREEN_BLINK = 0x44

    RED = "red"
    GREEN = "green"
    YELLOW = "yellow"

    on_cmds = {RED: RED_ON, GREEN: GREEN_ON, YELLOW: YELLOW_ON}
    off_cmds = {RED: RED_OFF, GREEN: GREEN_OFF, YELLOW: YELLOW_OFF}
    blink_cmds = {RED: RED_BLINK, GREEN: GREEN_BLINK, YELLOW: YELLOW_BLINK}

    # pylint: disable=too-few-public-methods
    class BlinkTask:
        """
        wrapper class for blink task
        """

        def __init__(self, color, timeout):
            self.color = color
            self.timeout = timeout

    def __init__(self, serial_device_path, baud_rate=9600):
        if not os.path.exists(serial_device_path):
            raise OSError(f"not a valid path: {serial_device_path}")

        self.serial_device_path = serial_device_path
        self.baud_rate = baud_rate

        self.bulb_serial = None

        self.logger = logging.getLogger(__name__)

        self.blink_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(
            target=self._process_queue,
            args=(self.blink_queue, self.stop_event),
            daemon=True,
        )
        self.thread.start()

    def _process_queue(self, blink_queue, stop_event):
        """
        Process the queue of blink tasks until the stop event is set.
        """
        while not stop_event.is_set():
            try:
                blink_task = blink_queue.get(timeout=3)
            except queue.Empty:
                continue

            self._blink(blink_task)
            blink_queue.task_done()

        # Drain the queue.
        self.logger.debug("draining the queue")
        while not blink_queue.empty():
            blink_queue.get_nowait()
            blink_queue.task_done()

    def cleanup(self):
        """
        Turn all the diodes off.
        """
        self.logger.debug("turning all colors off")
        self._send_command(self.RED_OFF)
        self._send_command(self.YELLOW_OFF)
        self._send_command(self.GREEN_OFF)

    def __enter__(self):
        self.bulb_serial = serial.Serial(self.serial_device_path, self.baud_rate)

        self.cleanup()

        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def _send_command(self, cmd):
        if self.bulb_serial:
            self.bulb_serial.write(bytes([cmd]))

    def close(self):
        """
        Turn all the diodes off, close the serial line and terminate the thread.
        """

        self.stop_event.set()
        self.blink_queue.join()

        self.cleanup()
        self.bulb_serial.close()

    def blink(self, color, timeout=10):
        """
        add a task to blink with given color for given time
        """
        self.blink_queue.put(self.BlinkTask(color, timeout))

    def _blink(self, blink_task):
        """
        perform the actual blinking
        """
        self.logger.debug(
            f"blinking with {blink_task.color} for {blink_task.timeout} seconds"
        )
        self._send_command(self.blink_cmds.get(blink_task.color.lower()))
        time.sleep(blink_task.timeout)
        self.off(blink_task.color)

    # pylint: disable=invalid-name
    def on(self, color):
        """
        turn on given color
        """
        self.logger.debug(f"turning {color} on")
        self._send_command(self.on_cmds.get(color.lower()))

    def off(self, color):
        """
        turn off given color
        """
        self.logger.debug(f"turning {color} off")
        self._send_command(self.off_cmds.get(color.lower()))
