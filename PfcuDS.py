#!/usr/bin/python
# -*- coding: utf-8 -*-

"""TANGO device server at ALBA
"""

META = """
    $URL$
    $LastChangedBy$
    $Date$
    $Rev: 
    Author: 
    License: GPL3+
"""

# Python standard library
import sys
from functools import partial, wraps, update_wrapper
from copy import copy
from types import StringType
import pprint
from time import time, sleep
import threading
import traceback
import socket
import errno
from threading import Event
# special 3rd party modules
import PyTango as Tg

TIMEOUT = 3
AQ_VALID = Tg.AttrQuality.ATTR_VALID
AQ_INVALID = Tg.AttrQuality.ATTR_INVALID

TERM = '\x0D'

POLL_PERIOD = 5.0


class UserException(Exception):
  pass

def ExceptionHandler(wrapped):
    '''Decorates commands so that the exception are logged and raised (to the client).
    '''

    @wraps(wrapped)
    def wrapper(self, *args, **kwargs):
        inst = self #< for pychecker

        try:
            return wrapped(self, *args, **kwargs)
        except Exception, x:
          inst.log.exception(x.__class__.__name__)
          inst.record_traceback()

    return wrapper

Attribute = ExceptionHandler

class TangoLogger(object):
    """Provides a logging.Logger interface to TANGO logger.
    """
    def __init__(self, log):
        self.name = log.get_name()
        self.debug = lambda *arg, **kw: log.debug(self.log_fmt(*arg, **kw))
        self.error = lambda *arg, **kw: log.error(self.log_fmt(*arg, **kw))
        self.warn = lambda *arg, **kw: log.warn(self.log_fmt(*arg, **kw))
        self.fatal = lambda *arg, **kw: log.fatal(self.log_fmt(*arg, **kw))
        self.info = lambda *arg, **kw: log.info(self.log_fmt(*arg, **kw))

    def exception(self, msg, *args):
        self.error(msg, *args, exc_info=1)

    def log_fmt(self, fmt, *args, **kwargs):
        try:
            exc_info = kwargs.get('exc_info')
            msg = str(fmt) % args
            if exc_info:
                msg += '\n'+traceback.format_exc()
            return msg
        except TypeError:
            return 'TypeError: %s / %s' % (str(fmt), str(args))


class PfcuDS(Tg.Device_4Impl):
    __exposure = 1
    __st_exposure = 1
    __lock = 1
    conn = None
    __state = None
    __status = None
    __DefaultDeviceID = None
    def __init__(self, cl, name):
        Tg.Device_4Impl.__init__(self, cl, name)
        self.log = TangoLogger(self.get_logger())
        self.get_device_properties(self.get_device_class())
        self.set_change_event('State', True)
        self.set_change_event('Status', True)
        self.exec_locals = { 'self' : self }
        self.exec_globals = globals()
        self.init_device()


    def delete_device(self):
        self.log.debug('deleting device')
        self.updater.stop()
        self.updater.fun_list.remove(self.update_stat)
        self.attr_list.remove_all()

    def init_device(self):
        self.cache = {}
        if not self.SerialLine:
            raise Exception('SerialLine not set')

        self.stat(Tg.DevState.UNKNOWN, 'not connected')
        self.log.info('started')
        self.Connect()
        if self.DefaultDeviceID in ['00','01','02','03','04','05','06','07','08','09','10','11','12','13','14','15','ALL']:
            self.__DefaultDeviceID = self.DefaultDeviceID
        else:
             raise Exception('Wrong DeviceID')
    def stat(self, state, status):
        '''Changes state and status and pushes events
        '''
        if state!=self.__state or status!=self.__status:
            self.log.debug('{0} {1} --> {2} {3}'.format(self.__state, self.__status, state, status))
        self.__state = state
        self.__status = status
        self.set_state(self.__state)
        self.set_status(self.__status)

        self.push_change_event('State')
        self.push_change_event('Status')

    ### Commands ###
    @ExceptionHandler
    def Connect(self):
        if self.conn: return
        try:
            conn = Tg.DeviceProxy(self.SerialLine)
        except Exception:
          pass
          raise
        self.conn = conn
        print "Connected" + str(self.conn.Status())
        self.conn.DevSerFlush(2)
        self.stat(Tg.DevState.ON, 'connected')

    @ExceptionHandler
    def Disconnect(self):
        self.conn = None
        self.log.debug('disconnecting...')
        self.stat(Tg.DevState.UNKNOWN, 'not connected')

    @ExceptionHandler
    def Exec(self, cmd):
        L = self.exec_locals
        G = self.exec_globals
        try:
            try:
                # interpretation as expression
                result = eval(cmd, G, L)
            except SyntaxError:
                # interpretation as statement
                exec cmd in G, L
                result = L.get("y")

        except Exception, exc:
            # handles errors on both eval and exec level
            result = exc

        if type(result)==StringType:
            return result
        elif isinstance(result, BaseException):
            return "%s!\n%s" % (result.__class__.__name__, str(result))
        else:
            return pprint.pformat(result)


    def Readline(self):
        return str(self.conn.DevSerReadRaw())

    def Flush(self):
        self.conn.DevSerFlush(2)

    def Write(self, what):
        re = self.request(what)
        return re

    def record_traceback(self, *extra):
        '''records a traceback of the current exception
           for easing later forensic.
            @param extra can be left empty and serves to append additional info
                         to the traceback
        '''
        self._trace = traceback.format_exc()
        for x in extra:
            self._trace = '\n'+str(extra)

    # attributes
    @Attribute
    def read_Identity(self, attr):
        try:
            tmp = '!PFCU%s S' % self.__DefaultDeviceID
            val = self.request(tmp,0.55)
        except Exception,e:
            raise Exception(e)
        attr.set_value(str(val))

    def read_PF2S2_Shutter_Status(self, attr):
        try:
            tmp = '!PFCU%s H' % self.__DefaultDeviceID
            val = self.request(tmp,0.2)
        except Exception,e:
            raise Exception(e)
        attr.set_value(str(val))

    def write_PF2S2_Shutter_Status(self, wattr):
        v = str(wattr.get_write_value())
        try:
            if v.lower() in ["true","1"]:
                tmp = '!PFCU%s 2' % self.__DefaultDeviceID
                val = self.request(tmp,0.2)
            elif v.lower() in ["false","0"]:
                tmp = '!PFCU%s 4' % self.__DefaultDeviceID
                val = self.request(tmp,0.2)
            else:
                raise Exception('Bad imput')
        except Exception,e:
            raise Exception(e)

    def read_Close_Shutter(self, attr):
        try:
            tmp = '!PFCU%s H' % self.__DefaultDeviceID
            val = self.request(tmp,0.2)
        except Exception,e:
            raise Exception(e)
        attr.set_value(str(val))

    def write_Close_Shutter(self, wattr):
        v = str(wattr.get_write_value())
        try:
            if v.lower() in ["true","1"]:
                tmp = '!PFCU%s C' % self.__DefaultDeviceID
                val = self.request(tmp,0.2)
            else:
                raise Exception('Bad imput')
        except Exception,e:
            raise Exception(e)

    def read_Open_Shutter(self, attr):
        try:
            tmp = '!PFCU%s H' % self.__DefaultDeviceID
            val = self.request(tmp,0.2)
        except Exception,e:
            raise Exception(e)
        attr.set_value(str(val))

    def write_Open_Shutter(self, wattr):
        v = str(wattr.get_write_value())
        try:
            if v.lower() in ["true","1"]:
                tmp = '!PFCU%s O' % self.__DefaultDeviceID
                val = self.request(tmp,0.2)

            else:
                raise Exception('Bad imput')
        except Exception,e:
            raise Exception(e)



    def read_Exposure_TimeUnit(self, attr):
        attr.set_value(self.__exposure)

    def write_Exposure_TimeUnit(self, wattr):
        v = wattr.get_write_value()
        try:
            if 0 < v < 65535:
                tmp = '!PFCU%s D %d' % (self.__DefaultDeviceID,v)
                val = self.request(tmp,0.2)
                self.__exposure=v
            else:
                raise Exception('Bad imput')
        except Exception,e:
            raise Exception(e)

    def read_Start_Exposure(self, attr):
        attr.set_value(self.__st_exposure)

    def write_Start_Exposure(self, wattr):
        v = wattr.get_write_value()
        try:
            if 0 < v < 65535:
                tmp = '!PFCU%s E %d' % (self.__DefaultDeviceID,v)
                val = self.request(tmp,0.2)
                self.__st_exposure = v
            else:
                raise Exception('Bad imput')
        except Exception,e:
            raise Exception(e)

    def read_DeviceID(self, attr):
        attr.set_value(self.__DefaultDeviceID)

    def read_Fault_Status(self, attr):
        try:
            tmp = '!PFCU%s F' % self.__DefaultDeviceID
            val = self.request(tmp,0.2)
        except Exception,e:
            raise Exception(e)
        attr.set_value(str(val))

    def write_DeviceID(self, wattr):
        v = str(wattr.get_write_value())
        try:
            if v in ['00','01','02','03','04','05','06','07','08','09','10','11','12','13','14','15','ALL']:
                self.__DefaultDeviceID = v
            else:
                raise Exception('Bad imput')
        except Exception,e:
            raise Exception(e)

    def write_Insert_Filter(self, wattr):
        v = str(wattr.get_write_value())
        try:
            tmp = '!PFCU%s I %s' % (self.__DefaultDeviceID,v)
            val = self.request(tmp,0.3)
        except Exception,e:
            raise Exception(e)

    def write_Remove_Filter(self, wattr):
        v = str(wattr.get_write_value())
        try:
            tmp = '!PFCU%s R %s' % (self.__DefaultDeviceID,v)
            val = self.request(tmp,0.3)
        except Exception,e:
            raise Exception(e)

    def read_Lock(self, attr):
        attr.set_value(str(self.__lock))

    def write_Lock(self, wattr):
        v = wattr.get_write_value()
        try:
            if v.lower() in ["true","1"]:
                tmp = '!PFCU%s L' % self.__DefaultDeviceID
                val = self.request(tmp,0.2)
                self.__lock = 1
            elif v.lower() in ["false","0"]:
                tmp = '!PFCU%s U' % self.__DefaultDeviceID
                val = self.request(tmp,0.2)
                self.__lock = 0			    
            else:
                raise Exception('Bad imput')
        except Exception,e:
            raise Exception(e)

    def read_Filter_Positions(self, attr):
        try:
            tmp = '!PFCU%s P ' % self.__DefaultDeviceID
            val = self.request(tmp,0.2)
        except Exception,e:
            raise Exception(e)
        attr.set_value(str(val))

    def write_Filter_Positions(self, wattr):
        v = str(wattr.get_write_value())
        try:
            tmp = '!PFCU%s W %s' % (self.__DefaultDeviceID,v)
            val = self.request(tmp, 0.2)
        except Exception,e:
            raise Exception(e)

    def write_Clear_ShortError(self, wattr):
        v = str(wattr.get_write_value())
        try:
            if v.lower() in ["true","1"]:
                tmp = '!PFCU%s Z' % self.__DefaultDeviceID
                val = self.request(tmp, 0.2)
            else:
                raise Exception('Bad imput')
        except Exception,e:
            raise Exception(e)


    def dev_state(self):
        return self.__state

    def dev_status(self):
        return self.__status

    def request(self, what, timepot=0):
        expr = what + TERM
        self.conn.DevSerWriteString(expr)
        sleeper = Event()
        sleeper.wait(timepot)   
        val = str(self.conn.DevSerReadRaw())
        print what + "  ---" + val
        return val

# Tango Class
class PfcuDS_Class(Tg.DeviceClass):

    # Class Properties
    class_property_list = {
    }


    # Device Properties
    device_property_list = {
        'SerialLine': [ Tg.DevString,
            "SerialLine", None
        ],
        'DefaultDeviceID': [ Tg.DevString,
            "From 00 to 15, or ALL", None
        ],
    }


    # Command definitions
    cmd_list = {
    'Connect' : 
            [[Tg.DevVoid, "Connect to SerialLine"], 
            [Tg.DevVoid, ""]], 
    'Disconnect' :             
            [[Tg.DevVoid, "Disconnect from SerialLine"], 
            [Tg.DevVoid, ""]], 
    'Exec': 
            [[Tg.DevVoid, ""], 
            [Tg.DevVoid, ""]], 
    'Write': 
            [[Tg.DevString, ""],
            [Tg.DevString, ""]], 
    'Readline': 
            [[Tg.DevVoid, ""], 
            [Tg.DevString, ""]], 
    'Flush': 
            [[Tg.DevVoid, ""], 
            [Tg.DevVoid, ""]], 
    }
    attr_list = {
        'Identity':  [ [ Tg.DevString, Tg.SCALAR, Tg.READ ],
            { 'display level' : Tg.DispLevel.OPERATOR,
              'memorized' : False
            } ],
        'DeviceID':  [ [ Tg.DevString, Tg.SCALAR, Tg.READ_WRITE ],
            { 'display level' : Tg.DispLevel.OPERATOR,
              'memorized' : True
            } ],
        'PF2S2_Shutter_Status':  [ [ Tg.DevString, Tg.SCALAR, Tg.READ_WRITE ],
            { 'display level' : Tg.DispLevel.OPERATOR,
              'memorized' : False
            } ],
        'Open_Shutter':  [ [ Tg.DevString, Tg.SCALAR, Tg.READ_WRITE ],
            { 'display level' : Tg.DispLevel.OPERATOR,
              'memorized' : False
            } ],
        'Close_Shutter':  [ [ Tg.DevString, Tg.SCALAR, Tg.READ_WRITE ],
            { 'display level' : Tg.DispLevel.OPERATOR,
              'memorized' : False
            } ],
        'Exposure_TimeUnit':  [ [ Tg.DevShort, Tg.SCALAR, Tg.READ_WRITE ],
            { 'display level' : Tg.DispLevel.OPERATOR,
              'memorized' : True
            } ],
        'Start_Exposure':  [ [ Tg.DevShort, Tg.SCALAR, Tg.READ_WRITE ],
            { 'display level' : Tg.DispLevel.OPERATOR,
              'memorized' : True
            } ],
        'Fault_Status':  [ [ Tg.DevString, Tg.SCALAR, Tg.READ ],
            { 'display level' : Tg.DispLevel.OPERATOR,
              'memorized' : False
            } ],
        'Insert_Filter':  [ [ Tg.DevString, Tg.SCALAR, Tg.WRITE ],
            { 'display level' : Tg.DispLevel.OPERATOR,
              'memorized' : False
            } ],
        'Lock':  [ [ Tg.DevString, Tg.SCALAR, Tg.READ_WRITE ],
            { 'display level' : Tg.DispLevel.OPERATOR,
              'memorized' : True
            } ],
        'Filter_Positions':  [ [ Tg.DevString, Tg.SCALAR, Tg.READ_WRITE ],
            { 'display level' : Tg.DispLevel.OPERATOR,
              'memorized' : False
            } ],
        'Remove_Filter':  [ [ Tg.DevString, Tg.SCALAR, Tg.WRITE ],
            { 'display level' : Tg.DispLevel.OPERATOR,
              'memorized' : False
            } ],
        'Clear_ShortError':  [ [ Tg.DevString, Tg.SCALAR, Tg.WRITE ],
            { 'display level' : Tg.DispLevel.OPERATOR,
              'memorized' : False
            } ],
    }



#------------------------------------------------------------------
#	Tango Class Constructor
#------------------------------------------------------------------
    def __init__(self, name):
        Tg.DeviceClass.__init__(self, name)
        self.set_type(name);

if __name__ == '__main__':
    try:
        argv = sys.argv
        # kill switch
        if '-k' in argv:
            argv.remove('-k')
            server = Tg.DeviceProxy('dserver/PfcuDS/'+argv[1])
            try:
                server.Kill()
            except AttributeError:
                print 'probably %s was not running anyway' % server.dev_name()
        U = Tg.Util(argv)
        U.add_TgClass( PfcuDS_Class, PfcuDS,'PfcuDS')

        tui = Tg.Util.instance()
        tui.server_init()
        tui.server_run()

    except Tg.DevFailed,e:
            Tg.Except.print_exception(e)
    except Exception,e:
            traceback.print_exc()

