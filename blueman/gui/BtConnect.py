import logging
from enum import Enum, auto
from typing import Optional
from gettext import gettext as _

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.overrides import Gtk
from gi.repository import GLib
from gi.repository import Gtk

from blueman.bluez.Device import Device
from blueman.gui.manager.ManagerDeviceMenu import ManagerDeviceMenu
from blueman.gui.manager.ManagerProgressbar import ManagerProgressbar
from blueman.main.DBusProxies import AppletService, DBusProxyFailed
import pulsectl

class ConnectDevice:
    def __init__(self, blueman) -> None:
        self.logger = logging.getLogger('bm.BtConnect.ConnectDevice')
        self.Blueman = blueman

    GENERIC_CONNECT = "00000000-0000-0000-0000-000000000000"

    def connect_service(self, device: Device, uuid: str = GENERIC_CONNECT) -> None:
        self.logger.info(f"Connecting to service {uuid} on device {device}")
        try:
            self._appl: Optional[AppletService] = AppletService()
        except DBusProxyFailed:
            self.logger.error("** Failed to connect to applet", exc_info=True)
            self._appl = None

        selected = self.Blueman.List.selected()
        if not selected:
            return
        row = self.Blueman.List.get(selected, "alias", "paired", "connected", "trusted", "objpush", "device",
                                    "blocked")
        self.SelectedDevice = row["device"]
        self.logger.info(f"SelectedDevice: {self.SelectedDevice} > connected: {row['connected']}")
        if row['connected']:
            self.disconnect_service(device)

            return

        def success(_obj: AppletService, _result: None, _user_data: None) -> None:
            self.logger.info("success")
            prog.message(_("Success!"))
            b_connect = self.Blueman.builder.get_widget("b_connect", Gtk.ToolButton)
            b_connect.set_label(_("Disconnect"))
            b_set_sink = self.Blueman.builder.get_widget("b_set_sink", Gtk.ToolButton)
            b_set_sink.set_sensitive(True)
            self.unset_op(device)

        def fail(_obj: Optional[AppletService], result: GLib.Error, _user_data: None) -> None:
            prog.message(_("Failed"))

            self.unset_op(device)
            self.logger.warning(f"fail {result}")
            self._handle_error_message(result)

        self.set_op(device, _("Connecting…"))
        prog = ManagerProgressbar(self.Blueman, cancellable=uuid == self.GENERIC_CONNECT)
        if uuid == self.GENERIC_CONNECT:
            prog.connect("cancelled", lambda x: self.disconnect_service(device))

        if self._appl is None:
            fail(None, GLib.Error('Applet DBus Service not available'), None)
            return

        self._appl.ConnectService('(os)', device.get_object_path(), uuid,
                             result_handler=success, error_handler=fail,
                             timeout=GLib.MAXINT)

        prog.start()

    def unset_op(self, device: Device) -> None:
        del ManagerDeviceMenu.__ops__[device.get_object_path()]
        for inst in ManagerDeviceMenu.__instances__:
            self.logger.info(f"op: regenerating instance {inst}")
            if inst.SelectedDevice == self.SelectedDevice and not (inst.is_popup and not inst.props.visible):
                inst.generate()

    def set_op(self, device: Device, message: str) -> None:
        ManagerDeviceMenu.__ops__[device.get_object_path()] = message
        for inst in ManagerDeviceMenu.__instances__:
            self.logger.info(f"op: regenerating instance {inst}")
            if inst.SelectedDevice == self.SelectedDevice and not (inst.is_popup and not inst.props.visible):
                inst.generate()

    def disconnect_service(self, device: Device, uuid: str = GENERIC_CONNECT, port: int = 0) -> None:
        def ok(_obj: AppletService, _result: None, _user_date: None) -> None:
            self.logger.info("disconnect success")
            b_connect = self.Blueman.builder.get_widget("b_connect", Gtk.ToolButton)
            b_connect.set_label(_("Connect"))
            b_set_sink = self.Blueman.builder.get_widget("b_set_sink", Gtk.ToolButton)
            b_set_sink.set_sensitive(False)

        def err(_obj: Optional[AppletService], result: GLib.Error, _user_date: None) -> None:
            self.logger.warning(f"disconnect failed {result}")
            msg, tb = _(result.message)
            self.Blueman.infobar_update(_("Disconnection Failed: ") + msg, bt=tb)


        if self._appl is None:
            err(None, GLib.Error('Applet DBus Service not available'), None)
            return

        self._appl.DisconnectService('(osd)', device.get_object_path(), uuid, port,
                                     result_handler=ok, error_handler=err, timeout=GLib.MAXINT)


    def _handle_error_message(self, error: GLib.Error) -> None:
        err = self._BLUEZ_ERROR_MAP.get(error.message.split(":", 3)[-1].strip())

        if err == self._BluezError.PROFILE_UNAVAILABLE:
            self.logger.warning("No audio endpoints registered to bluetoothd. "
                            "Pulseaudio Bluetooth module, bluez-alsa, PipeWire or other audio support missing.")
            msg = _("No audio endpoints registered")
        elif err == self._BluezError.CREATE_SOCKET:
            self.logger.warning("bluetoothd reported input/output error. Check its logs for context.")
            msg = _("Input/output error")
        elif err == self._BluezError.PAGE_TIMEOUT:
            msg = _("Device did not respond")
        elif err == self._BluezError.UNKNOWN:
            self.logger.warning("bluetoothd reported an unknown error. "
                            "Retry or check its logs for context.")
            msg = _("Unknown error")
        else:
            msg = error.message.split(":", 3)[-1].strip()

        if err != self._BluezError.CANCELED:
            self.Blueman.infobar_update(_("Connection Failed: ") + msg)

    class _BluezError(Enum):
        PAGE_TIMEOUT = auto()
        PROFILE_UNAVAILABLE = auto()
        CREATE_SOCKET = auto()
        CANCELED = auto()
        UNKNOWN = auto()

    # BlueZ 5.62 introduced machine-readable error strings while earlier versions
    # used strerror() so that the messages depend on the libc implementation:
    # https://sourceware.org/git/?p=glibc.git;a=blob;f=sysdeps/gnu/errlist.h
    # https://git.musl-libc.org/cgit/musl/tree/src/errno/__strerror.h
    # https://git.uclibc.org/uClibc/tree/libc/string/_string_syserrmsgs.c
    _BLUEZ_ERROR_MAP = {
        "Protocol not available": _BluezError.PROFILE_UNAVAILABLE,
        "br-connection-profile-unavailable": _BluezError.PROFILE_UNAVAILABLE,
        "Input/output error": _BluezError.CREATE_SOCKET,
        "I/O error": _BluezError.CREATE_SOCKET,
        "br-connection-create-socket": _BluezError.CREATE_SOCKET,
        "le-connection-create-socket": _BluezError.CREATE_SOCKET,
        "Host is down": _BluezError.PAGE_TIMEOUT,
        "br-connection-page-timeout": _BluezError.PAGE_TIMEOUT,
        "br-connection-unknown": _BluezError.UNKNOWN,
        "Cancelled": _BluezError.CANCELED,
        "br-connection-canceled": _BluezError.CANCELED,
    }

class PulseInfo:
    """PulseAudio information"""
    def __init__(self):
        self.logger = logging.getLogger('bm.BtConnect.PulseInfo')
        # sink_hash is a dictionary with the following structure:
        # {description: {sink_name: string, volume: float, state: Boolean}}
        self.sink_hash = {}
        self.default_sink = None


    def get_sinks(self):
        self.logger.info("get_sinks")

        with pulsectl.Pulse('blueman') as pulse:
            try:
                for sink in pulse.sink_list():
                    self.sink_hash[sink.description] = {'sink_name': sink.name, 'volume': sink.volume.value_flat,
                                                        'state': sink.state._value == 'running'}
            except Exception as e:
                self.logger.error("Error getting PulseAudio sinks", exc_info=True)
                self.sink_hash = {'default': {'sink_name': 'No sinks found', 'volume': 0.85, 'state': False}}
            else:
                self.logger.info(f"get_sinks: {self.sink_hash}")
            return self.sink_hash

    def get_default_sink(self):
        self.logger.info("get_default_sink")
        with pulsectl.Pulse('blueman') as pulse:
            try:
                self.default_sink = pulse.sink_default_get().name
            except Exception as e:
                self.logger.error("Error getting PulseAudio default sink", exc_info=True)
            else:
                self.logger.info(f"get_default_sink: {self.default_sink}")
                return self.default_sink

    def set_default_sink(self, sink_name):
        self.logger.info(f"set_default_sink: {sink_name}")
        with pulsectl.Pulse('blueman') as pulse:
            try:
                for sink in pulse.sink_list():
                    if sink.name == sink_name:
                        pulse.sink_default_set(sink)
                        break
            except Exception as e:
                self.logger.error("Error setting PulseAudio default sink", exc_info=True)
            else:
                return True

    def set_sink_volume(self, sink_name='', volume=0.85):
        self.logger.info(f"set_sink_volume: {sink_name} {volume}")
        if not sink_name:
            sink_name = self.get_default_sink()
            self.logger.info(f"set_sink_volume: default sink {sink_name}")
        with pulsectl.Pulse('blueman') as pulse:
            try:
                for sink in pulse.sink_list():
                    if sink.name == sink_name:
                        pulse.volume_set_all_chans(sink, volume)
                        break
            except Exception as e:
                self.logger.error("Error setting PulseAudio sink volume", exc_info=True)
            else:
                return True

