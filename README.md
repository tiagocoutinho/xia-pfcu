# XIA PFCU library

<img align="right" alt="XIA PF4" height="300" src="docs/pf4.png" />

This library is used to control basic features of XIA PFCU equipment.
It is composed of a core library, an optional simulator and an optional
[tango](https://tango-controls.org/) device server.

It has been tested with PF4 model, but should work with
other models too.

It can be used with either with a direct serial line (read below
on the recommended way to setup a serial line connection) or remotely
through TCP socket (either raw socket or rfc2217). In the latter case
the master device to which the Julabo serial line is connected must
provide a raw socket or rfc2217 interface.

## Installation

From within your favorite python environment type:

`$ pip install xia-pfcu`

## Library

The core of the library consists of PFCU object.
To create a PFCU object you need to pass a connection object.
A compatible connection object can be created using the companion
[connio](https://github.com/tiagocoutinho/connio) library which
should already be installed as a dependency.

Here is how to connect to a PFCU through a local serial line:

```python
from connio import connection_for_url
from xia_pfcu import PFCU


async def main():
    conn = connection_for_url("serial://dev/ttyS0")
    dev = PFCU(conn)

    raw_status = await dev.raw_status()
    print(raw_status)

    status = await dev.status()
    if status['shutter_enabled']:
        shutter_status = (await dev.shutter_status()).name
    else:
        shutter_status = "Disabled"
    print(f"Shutter status: {shutter_status}")

    # open shutter
    await dev.open_shutter()


asyncio.run(main())
```

#### Serial line

To access a serial line based PFCU device it is strongly recommended you spawn
a serial to tcp bridge using [ser2net](https://linux.die.net/man/8/ser2net),
[ser2sock](https://github.com/tiagocoutinho/ser2sock) or
[socat](https://linux.die.net/man/1/socat)

Assuming your device is connected to `/dev/ttyS0` and the baudrate is set to 9600,
here is how you could use socat to expose your device on the machine port 5000:

`socat -v TCP-LISTEN:5000,reuseaddr,fork file:/dev/ttyS0,rawer,b9600,cs8,eol=10,icanon=1`

It might be worth considering starting socat, ser2net or ser2sock as a service using
[supervisor](http://supervisord.org/) or [circus](https://circus.rtfd.io/).

### Simulator

A PFCU simulator is provided.

Before using it, make sure everything is installed with:

`$ pip install xia-pfcu[simulator]`

The [sinstruments](https://pypi.org/project/sinstruments/) engine is used.

To start a simulator you need to write a YAML config file where you define
how many devices you want to simulate and which properties they hold.

The following example exports 1 hardware device with a minimal configuration
using default values:

```yaml
# config.yml

devices:
- class: PFCU
  package: xia_pfcu.simulator
  transports:
  - type: serial
    url: /tmp/pfcu-1
```

To start the simulator type:

```terminal
$ sinstruments-server -c ./config.yml --log-level=DEBUG
2020-09-14 10:42:27,592 INFO  simulator: Bootstraping server
2020-09-14 10:42:27,592 INFO  simulator: no backdoor declared
2020-09-14 10:42:27,592 INFO  simulator: Creating device PFCU ('PFCU')
2020-09-14 10:42:27,609 INFO  simulator: Created symbolic link "/tmp/pfcu-1" to simulator pseudo terminal '/dev/pts/3'
2020-09-14 10:42:27,609 INFO  simulator.PFCU[/tmp/pfcu-1]: listening on /tmp/pfcu-1 (baud=None)
```

(To see the full list of options type `sinstruments-server --help`)

You can access it as you would a real hardware. Here is an example using python
serial library on the same machine as the simulator:

```python
$ python
>>> from connio import connection_for_url
>>> from xia_pfcu import PFCU
>>> conn = connection_for_url("serial:///tmp/pfcu-cf31", concurrency="syncio")
>>> dev = PFCU(conn)
>>> conn.open()
>>> print(dev.status())
%PFCU15 OK PFCU v1.0 (c) XIA 1999 All Rights Reserved
CHANNEL IN/OUT (FPanel   TTL  RS232) Shorted? Open?
    1     OUT     OUT    OUT   OUT      NO      NO
    2     OUT     OUT    OUT   OUT      NO      NO
    3      IN     OUT    OUT    IN      NO      NO
    4     OUT     OUT    OUT   OUT      NO      NO
RS232 Control Enabled: YES
RS232 Control Only: NO
Shutter Mode Enabled: NO
Exposure Decimation:     1
```

### Tango server

A [tango](https://tango-controls.org/) device server is also provided.

Make sure everything is installed with:

`$ pip install xia-pfcu[tango]`

Register a PFCU tango server in the tango database:
```
$ tangoctl server add -s PFCU/test -d PFCU test/pfcu/1
$ tangoctl device property write -d test/pfcu/1 -p address -v "tcp://controls.lab.org:17890"
```

(the above example uses [tangoctl](https://pypi.org/project/tangoctl/). You would need
to install it with `pip install tangoctl` before using it. You are free to use any other
tango tool like [fandango](https://pypi.org/project/fandango/) or Jive)

Launch the server with:

```terminal
$ PFCU test
```
