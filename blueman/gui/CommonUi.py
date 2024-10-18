import logging
from datetime import datetime
from gettext import gettext as _
from typing import Optional, overload, TYPE_CHECKING

from gi.repository import GLib

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
    about.set_comments(_('Blueman is a GTK+ Bluetooth manager' + '\n'+ "This version is adapted for use on BTP machines.\n"))
    about.set_website(WEBSITE)
    about.set_website_label(WEBSITE)
    about.set_icon_name('btp')
    about.set_logo_icon_name('btp')
    about.set_authors(['Valmantas Palikša <walmis@balticum-tv.lt>',
                       'Tadas Dailyda <tadas@dailyda.com>',
                       'For BTP+ fork <hj@btp.nl>'
                       ])
    if run:
        about.show()
        return None
    else:
        return about

def show_faq_dialog(parent: Optional[Gtk.Window] = None) -> None:
    dialog = Gtk.Dialog(title=_("Frequently Asked Questions"), transient_for=parent, modal=True)
    dialog.add_button(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
    dialog.set_default_size(700, 400)
    dialog.set_border_width(10)

    # we read a pango markup file from disk, and display it in a scrolled window
    # check the current locale as we need to load the correct file
    loc = GLib.get_language_names()[0]
    if loc == 'nl':
        path = 'data/docs/FAQ-nl.pango'
    elif loc == 'es':
        path = 'data/docs/FAQ-es.pango'
    else:
        path = 'data/docs/FAQ.pango'
    text = open(path, 'r').read()
    label = Gtk.Label()
    label.set_markup(text)

    mainbox = dialog.get_content_area()
    scrolled = Gtk.ScrolledWindow()
    scrolled.set_vexpand(True)

    scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    scrolled.add(label)
    mainbox.add(scrolled)
    dialog.show_all()
    dialog.run()
    dialog.destroy()


class PulseDialog(Gtk.Dialog):
    def __init__(self, parent: Optional[Gtk.Window] = None):
        super().__init__(title=_("PulseAudio"), transient_for=parent, modal=True)
        self.logger = logging.getLogger('bm.PulseDialog')
        self.add_button(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
        self.set_default_size(600, 400)
        self.set_border_width(10)
        self.PI = PulseInfo()

        self.box = self.fill_dialog()

        self.show_all()
        self.run()
        self.destroy()

    def on_radio_toggled(self, button, name):
        if button.get_active():
            self.PI.set_default_sink(name)


    def fill_dialog(self) -> Gtk.Box:
        sinks = self.PI.get_sinks()
        self.logger.info(f"fill_dialog: {sinks}")

        # Calculate the maximum length of all the labels
        max_length = max(len(k) for k in sinks.keys())

        mainbox = self.get_content_area()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        found_running = False
        first_radio = None
        radio = None
        for k in sinks.keys():
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            lbl = Gtk.Label(label=k, xalign=0.0)
            lbl.set_size_request(max_length * 10, -1)  # Set label width to the maximum length
            lbl.set_margin_top(36)
            hbox.add(lbl)
            volume = Gtk.VolumeButton()
            volume.set_value(0.85)
            volume.set_margin_start(12)
            volume.set_margin_end(12)
            hbox.add(volume)
            radio = Gtk.RadioButton.new_with_label_from_widget(first_radio, '')
            radio.set_margin_start(12)
            radio.set_margin_end(12)
            if first_radio is None:
                first_radio = radio
            if sinks[k]['state']:
                self.logger.info(f"fill_dialog: Found running sink: {sinks[k]['sink_name']}")
                radio.set_active(True)
                found_running = True
            radio.connect('toggled', self.on_radio_toggled, sinks[k]['sink_name'])
            hbox.add(radio)
            vbox.add(hbox)
        # if no sink is running, set the last radio button to active
        if not found_running and radio:
            self.logger.info("fill_dialog: No sink running, setting last radio button to active")
            radio.set_active(True)
        mainbox.add(vbox)
        return vbox
