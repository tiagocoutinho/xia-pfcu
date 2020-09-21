import json

from tango import DevState, GreenMode
from tango.server import Device, attribute, command, device_property
from connio import connection_for_url

import xia_pfcu


class PFCU(Device):

    green_mode = GreenMode.Asyncio

    url = device_property(dtype=str)
    baudrate = device_property(dtype=int, default_value=9600)
    bytesize = device_property(dtype=int, default_value=8)
    parity = device_property(dtype=str, default_value="N")

    module = device_property(dtype=str, default_value=xia_pfcu.BROADCAST)

    async def init_device(self):
        await super().init_device()
        kwargs = dict(concurrency="async", eol=b";\r\n")
        if self.url.startswith("serial") or self.url.startswith("rfc2217"):
            kwargs.update(
                dict(baudrate=self.baudrate, bytesize=self.bytesize, parity=self.parity)
            )
        self.connection = connection_for_url(self.url, **kwargs)
        self.pfcu = xia_pfcu.PFCU(self.connection, module=self.module)

    async def delete_device(self):
        await self.connection.close()

    async def dev_state(self):
        try:
            status = await self.pfcu.shutter_status()
        except xia_pfcu.PFCUError as error:
            if "disabled" in error.args[0].lower():
                return DevState.DISABLE
            else:
                return DevState.FAULT
        except:
            return DevState.FAULT
        if status == xia_pfcu.ShutterStatus.Closed:
            return DevState.CLOSE
        elif status == xia_pfcu.ShutterStatus.Open:
            return DevState.OPEN
        return DevState.UNKNOWN

    async def dev_status(self):
        try:
            self.__status = await self.pfcu.status()
        except Exception as error:
            self.__status = repr(error)
        return self.__status

    @command()
    async def enable_shutter(self):
        await self.pfcu.enable_shutter()

    @command()
    async def disable_shutter(self):
        await self.pfcu.disable_shutter()

    @command()
    async def open_shutter(self):
        await self.pfcu.open_shutter()

    @command()
    async def close_shutter(self):
        await self.pfcu.close_shutter()

    @command(dtype_in=float)
    async def start_exposure(self):
        await self.pfcu.start_exposure()

    @attribute(dtype=bool)
    async def exclusive_remote_control(self):
        info = await self.pfcu.info()
        return info["remote_control_only"]

    @exclusive_remote_control.write
    async def exclusive_remote_control(self, value):
        await (self.pfcu.lock() if value else self.pfcu.unlock())

    @command()
    async def clear_short_error(self):
        await self.pfcu.clear_short_error()

    @attribute(dtype=str)
    async def shutter_status(self):
        try:
            status = await self.pfcu.shutter_status()
        except xia_pfcu.PFCUError as error:
            if "disabled" in error.args[0].lower():
                return "Disabled"
            raise
        return status.name

    @attribute(dtype=[str], max_dim_x=4)
    async def filters_status(self):
        status = await self.pfcu.filters_status()
        return [f.name for f in status]

    @filters_status.write
    async def filters_status(self, value):
        assert len(value) == 4
        await self.pfcu.set_filters(*value)

    @attribute(dtype=str)
    async def json_status(self):
        return json.dumps(await self.pfcu.info())
