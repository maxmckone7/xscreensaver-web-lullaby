import signal

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GdkX11', '3.0')
gi.require_version('WebKit', '3.0')
from gi.repository import Gtk, GdkX11, WebKit

import logging
import os
from ctypes import c_int

from . import config

_logger = logging.getLogger(config.APP_NAME)


class _Browser:
    def __init__(self, enable_user_interaction=False):
        """
        :type enable_user_interaction: bool
        """
        self.__window = Gtk.Window(title=config.APP_NAME)
        self.__window.connect('delete-event', Gtk.main_quit)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)

        self.__web_view = WebKit.WebView()
        self.__web_view.set_sensitive(enable_user_interaction)
        self.__web_view.get_settings().set_property("enable-webgl", True)
        # self.__web_view.setStyleSheet('* { background-color: rgb(0, 0, 0); }')

        # self.__web_view.closeEvent = self.__web_view_on_close
        self.__web_view.connect('notify::title', self.__web_view_on_title_change)
        self.__web_view.connect('console-message', self.__web_view_on_console_message)
        scrolled_window.add(self.__web_view)

        self.__window.add(scrolled_window)

    def show_window(self, width=800, height=600):
        """
        :type width: int
        :type height: int
        """
        self.__window.set_size_request(width, height)
        self.__window.show_all()

    def embed_window(self, foreign_window_id):
        """
        :type foreign_window_id: int
        """
        display = GdkX11.X11Display.get_default()
        web_view_window = GdkX11.X11Window.foreign_new_for_display(display, c_int(self.__web_view.winId()).value)
        foreign_window = GdkX11.X11Window.foreign_new_for_display(display, foreign_window_id)

        # foreign_window.set_events(
        #     gtk.gdk.EXPOSURE_MASK
        #     | gtk.gdk.STRUCTURE_MASK
        # )

        # INFO: https://github.com/jsdf/previous/blob/master/python-ui/tests/pygtk-hatari-embed-test.py
        web_view_window.reparent(foreign_window, 0, 0)
        while Gtk.events_pending():
            Gtk.main_iteration()

        self.__web_view.setWindowFlags(
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.NoDropShadowWindowHint
        )

        width, height = foreign_window.get_size()
        self.__web_view.setFixedSize(QSize(width, height))

        self.__web_view.setVisible(False)
        self.__web_view.loadFinished.connect(self.__web_view_on_load_finished)

        self.__web_view.show()

    def open(self, url):
        """
        :type url: str
        """
        self.__web_view.open(url)

    @classmethod
    def __web_view_on_close(self, event):
        """
        :type event: PyQt5.QtGui.QCloseEvent.QCloseEvent
        """
        mbox = QMessageBox()
        mbox.setModal(True)
        mbox.setText('Click on \'Cancel\' to leave the application open.')
        mbox.setIcon(QMessageBox.Question)
        mbox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

        event.setAccepted(mbox.exec_() == QMessageBox.Ok)

    def __web_view_on_load_finished(self):
        self.__web_view.setVisible(True)

    def __web_view_on_title_change(self, web_view, property_spec):
        """
        :type web_view: WebKit.WebView
        :type property_spec: GParamSpec
        """
        browser_title = web_view.get_title()

        title = config.APP_NAME
        if browser_title is not None:
            title = '{}: {}'.format(title, browser_title)

        self.__window.set_title(title)

    def __web_view_on_console_message(self, web_view, message, line, source):
        """
        :type web_view: WebKit.WebView
        :type message: str
        :type line: int
        :type source: str
        """
        _logger.debug('JsConsole: {message} - {source}:{line}'.format(
            message=message,
            source=source,
            line=line
        ))


def run(url):
    """
    :type url: str
    :rtype: int
    """
    parent_wid = os.environ.get('XSCREENSAVER_WINDOW')

    browser = _Browser()
    if parent_wid is None:
        browser.show_window()
    else:
        browser.embed_window(int(parent_wid, 16))
    browser.open(url)

    # Handle properly Ctrl+C while GTK App is running
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    return Gtk.main()
