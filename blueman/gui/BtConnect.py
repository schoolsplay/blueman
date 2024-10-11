import logging
from enum import Enum, auto
from typing import Optional
from gettext import gettext as _
from gi.repository import GLib

from blueman.bluez.Device import Device
from blueman.gui.manager.ManagerDeviceMenu import ManagerDeviceMenu
from blueman.gui.manager.ManagerProgressbar import ManagerProgressbar
from blueman.main.DBusProxies import AppletService, DBusProxyFailed


class ConnectDevice:
    def __init__(self, blueman) -> None:
        self.logger = logging.getLogger('bm.BtConnect.ConnectDevice')
        self.Blueman = blueman

    GENERIC_CONNECT = "00000000-0000-0000-0000-000000000000"

    def connect_service(self, device: Device, uuid: str = GENERIC_CONNECT) -> None:
        self.logger.info(f"Connecting to service {uuid} on device {device}")

        try:
            _appl: Optional[AppletService] = AppletService()
        except DBusProxyFailed:
            self.logger.error("** Failed to connect to applet", exc_info=True)
            _appl = None

        selected = self.Blueman.List.selected()
        if not selected:
            return
        row = self.Blueman.List.get(selected, "alias", "paired", "connected", "trusted", "objpush", "device",
                                    "blocked")
        self.SelectedDevice = row["device"]
        self.logger.info(f"SelectedDevice: {self.SelectedDevice}")
        def success(_obj: AppletService, _result: None, _user_data: None) -> None:
            self.logger.info("success")
            prog.message(_("Success!"))

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

        if _appl is None:
            fail(None, GLib.Error('Applet DBus Service not available'), None)
            return

        _appl.ConnectService('(os)', device.get_object_path(), uuid,
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
