import logging
from datetime import datetime
from gettext import gettext as _
from typing import Optional, overload, TYPE_CHECKING

from gi.overrides.GLib import GLib

from blueman.Constants import WEBSITE, VERSION

import gi

from blueman.bluez.Device import Device
from blueman.gui.BtConnect import PulseInfo
from blueman.gui.manager.ManagerDeviceMenu import ManagerDeviceMenu
from blueman.gui.manager.ManagerProgressbar import ManagerProgressbar
from blueman.main.DBusProxies import DBusProxyFailed, AppletService

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

if TYPE_CHECKING:
    from typing_extensions import Literal


class ErrorDialog(Gtk.MessageDialog):
    def __init__(self, markup: str, secondary_markup: Optional[str] = None, excp: Optional[object] = None,
                 icon_name: str = "dialog-error", buttons: Gtk.ButtonsType = Gtk.ButtonsType.CLOSE,
                 title: Optional[str] = None, parent: Optional[Gtk.Container] = None, modal: bool = False,
                 margin_left: int = 0,
                 ) -> None:
        super().__init__(name="ErrorDialog", icon_name=icon_name, buttons=buttons,
                         type=Gtk.MessageType.ERROR, title=title, parent=parent, modal=modal, margin_left=margin_left)

        self.set_markup(markup)

        if secondary_markup:
            self.format_secondary_markup(secondary_markup)

        if excp:
            message_box = self.get_message_area()

            label_expander = Gtk.Label(label="<b>Exception</b>", use_markup=True, visible=True)

            excp_label = Gtk.Label(label=str(excp), selectable=True, visible=True)

            expander = Gtk.Expander(label_widget=label_expander, visible=True)
            expander.add(excp_label)

            message_box.pack_start(expander, False, False, 10)


@overload
def show_about_dialog(app_name: str, run: "Literal[True]" = True, parent: Optional[Gtk.Window] = None) -> None:
    ...


@overload
def show_about_dialog(app_name: str, run: "Literal[False]", parent: Optional[Gtk.Window] = None) -> Gtk.AboutDialog:
    ...


def show_about_dialog(app_name: str, run: bool = True, parent: Optional[Gtk.Window] = None
                      ) -> Optional[Gtk.AboutDialog]:
    about = Gtk.AboutDialog()
    about.set_transient_for(parent)
    about.set_modal(True)
    # on KDE it shows a close button which is unconnected.
    about.connect("response", lambda x, y: about.destroy())
    about.set_name(app_name)
    about.set_version(VERSION)
    about.set_copyright('Copyright © 2008 Valmantas Palikša\n'
                        'Copyright © 2008 Tadas Dailyda\n'
                        f'Copyright © 2008 - {datetime.now().year} blueman project'
                        )
    test_lines = ["line 1\n", "line 2\n", "line 3\n", "line 4\n", "line 5\n", "line 6\n", "line 7\n", "line 8\n"]
    about.set_comments(_('Blueman is a GTK+ Bluetooth manager' + '\n'+ "Now edited for use on BTP machines.\n" + ",".join(test_lines)))
    about.set_website(WEBSITE)
    about.set_website_label(WEBSITE)
    about.set_icon_name('blueman')
    about.set_logo_icon_name('blueman')
    about.set_authors(['Valmantas Palikša <walmis@balticum-tv.lt>',
                       'Tadas Dailyda <tadas@dailyda.com>',
                       f'{WEBSITE}/graphs/contributors',
                       'For BTP+ <hj@btp.nl>'
                       ])
    if run:
        about.show()
        return None
    else:
        return about

class PulseDialog(Gtk.Dialog):
    def __init__(self, devicelist, parent: Optional[Gtk.Window] = None):
        super().__init__(title=_("PulseAudio"), transient_for=parent, modal=True)
        self.add_button(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
        self.set_default_size(600, 400)
        self.set_border_width(10)
        self.PI = PulseInfo()
        self.box = self.fill_dialog(devicelist)

        self.show_all()
        self.run()
        # TODO: Implement PulseAudio sink setting
        print("PulseAudio sink setting not yet implemented")
        # get children of gbox
        # get the radio button that is active
        # get the label of the radio button
        # set the default sink to the label of the radio button
        # self.set_default_sink(label)
        children = self.box.get_children()
        print(f"Got children: {children}")
        for child in children:
            print(f"Child: {child}")
            if isinstance(child, Gtk.Box):
                for c in child.get_children():
                    print(f"Child: {c}")
                    if isinstance(c, Gtk.RadioButton):
                        if c.get_active():
                            print(f"Found active radio button: {c}")
                            # for cc in child.get_children():
                            #     if isinstance(cc, Gtk.Label):
                            #         print(f"Found label: {cc}")
                            #         self.set_default_sink(cc.get_text())
        self.destroy()

    def set_default_sink(self, sink):
        print(f"Setting_default_sink to {sink}")
        self.PI.set_default_sink(sink)

    def fill_dialog(self, devicelist) -> Gtk.Box:
        sinks = self.PI.get_sinks()
        print(f"Got sinks info: {sinks}")

        print("Filling dialog")
        mainbox = self.get_content_area()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.devicelist = devicelist
        radio = None
        first_radio = None
        for k in sinks.keys():
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            lbl = Gtk.Label(label=k, xalign=Gtk.Align.START)
            lbl.set_width_chars(32)
            hbox.add(lbl)
            volume = Gtk.VolumeButton()
            volume.set_value(50)
            hbox.add(volume)
            radio = Gtk.RadioButton.new_with_label_from_widget(first_radio, '')
            if first_radio is None:
                first_radio = radio
            if sinks[k]['state']:
                print(f"Setting radio to active: {radio}")
                radio.set_active(True)
            hbox.add(radio)
            vbox.add(hbox)
        # if no sink is running, set the last radio button to active
        if not first_radio and radio:
            radio.set_active(True)
        mainbox.add(vbox)
        return vbox
