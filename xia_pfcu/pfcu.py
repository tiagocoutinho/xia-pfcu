"""
# Shutter control
"""

import logging

from .protocol import (
    Protocol,
    parse_status,
    decode_status,
    decode_shutter_status,
    decode_filters_status,
    BROADCAST,
)


class PFCU:
    """
    PFCU-4 - Filter Set & Relay Control Unit

    """

    def __init__(self, connection, module=BROADCAST):
        self._log = logging.getLogger("xia_pfcu.{}".format(type(self).__name__))
        self.protocol = Protocol(connection, module=module, log=self._log)

    def write_readline(self, command):
        return self.protocol.write_readline(command)

    def enable_shutter(self):
        """
        Enables the shutter commands (Close, Open, Exposure). Useful for
        controlling the XIA Model PF2S2 Filter unit with focal plane shutter.
        """
        return self.write_readline("2")

    def disable_shutter(self):
        """
        Disable the shutter commands. This is the default condition at power-up.
        """
        return self.write_readline("4")

    def open_shutter(self):
        """
        Immediately opens the PF2S2 shutter, beginning an indefinite exposure.
        This command only works if shutter mode is enabled.
        """
        return self.write_readline("O")

    def close_shutter(self):
        """
        Immediately closes the PF2S2 shutter. If an exposure is in progress,
        it is terminated. This command only works if shutter mode is enabled
        """
        return self.write_readline("C")

    def shutter_status(self):
        return decode_shutter_status(self.write_readline("H"))

    def status(self):
        return decode_status(self.write_readline("S"))

    def info(self):
        return parse_status(self.status())

    def filters_status(self):
        return decode_filters_status(self.write_readline("F"))

    def set_filters(self, a=None, b=None, c=None, d=None):
        """
        Set multiple filters at the same time
        Default value (None) indicates that the filter should not change state.
        "IN", "I", "1" or 1 (case insensitive) indicate the filter should be inserted,
        "OUT", "O", "0" or 0 (case insensitive) indicate the filter should be removed.

        Returns the state of each filter
        """
        a = "=" if a is None else str(a)
        b = "=" if b is None else str(b)
        c = "=" if c is None else str(c)
        d = "=" if d is None else str(d)
        vmap = {
            "out": "0",
            "o": "0",
            "0": "0",
            "in": "1",
            "i": "1",
            "1": "1",
            "-": "=",
            "": "=",
            "=": "=",
        }
        values = [vmap[v.lower()] for v in (a, b, c, d)]
        status = self.write_readline("W " + "".join(values))
        return decode_filters_status(status)

    def start_exposure(self, duration):
        """
        Initiates a fixed length exposure using the focal plane shutter
        (enabled only in shutter mode (and RS232 control is enabled))
        """
        return self.protocol.start_exposure(duration)

    def lock(self):
        """
        Set the PFCU such that the non-RS232 controls are ignored. This means
        that the front panel switches and the TTL control lines would be
        ignored, until either an unlock command is issued (see below) or RS232
        control is disabled (using the front panel slide switch).
        """
        return self.write_readline("L")

    def unlock(self):
        """
        Unlocks exclusive RS232 control and allows filter control by the front
        panel switches and the TTL inputs, as well as RS232 commands (as long
        as RS232 control is enabled with the front panel switch)
        """
        return self.write_readline("U")

    def clear_short_error(self):
        """
        Clears any short conditions existing on any of the 4 channels.
        When a short condition is detected, power is immediately removed, and
        the short condition is latched. To clear the latched short state, the
        channel must be turned off by all enabled control inputs (ie, the
        overall control state for the shorted channel must be set to the ‘OUT’
        state), or this command must be issued. This command very briefly
        sets all channels to the ‘OUT’ state then returns the channels to their
        original state. The cycle time is much much shorter than the response
        time of the filters, so non-shorted filters are not affected.
        """
        return self.write_readline("Z")

    def set_decimation(self, value):
        return self.protocol.set_decimation(value)
