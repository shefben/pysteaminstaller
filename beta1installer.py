import os
import sys
import time
import threading

try:
    import win32con
    import win32gui
    import win32com.shell.shell as shell
except ImportError:
    raise SystemExit("pywin32 is required for this installer")

# Geometry constants matching the Tkinter version
OUTER_W, OUTER_H = 480, 361
CLIENT_W, CLIENT_H = 480, 335

class WizardPage:
    def __init__(self, hwnd_parent):
        self.hwnd_parent = hwnd_parent
        self.controls = []
        self.hwnd = None

    def show(self):
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)

    def hide(self):
        win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)

class SetupWizard:
    def __init__(self):
        self.hInstance = win32gui.GetModuleHandle(None)
        className = 'SteamSetupWizard'
        wndClass = win32gui.WNDCLASS()
        wndClass.style = win32con.CS_HREDRAW | win32con.CS_VREDRAW
        wndClass.lpfnWndProc = self._wndProc
        wndClass.hInstance = self.hInstance
        wndClass.hCursor = win32gui.LoadCursor(0, win32con.IDC_ARROW)
        wndClass.hbrBackground = win32con.COLOR_WINDOW + 1
        wndClass.lpszClassName = className
        self.classAtom = win32gui.RegisterClass(wndClass)
        self.hwnd = win32gui.CreateWindowEx(
            0,
            self.classAtom,
            'Steam Setup',
            win32con.WS_OVERLAPPED | win32con.WS_CAPTION | win32con.WS_SYSMENU,
            100,
            100,
            OUTER_W,
            OUTER_H,
            0,
            0,
            self.hInstance,
            None
        )

        self.pages = {}
        self.cur_page = None
        self._build_pages()
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)

    def _build_pages(self):
        self.pages['welcome'] = self._build_welcome()
        self.pages['install'] = self._build_install()
        self.show_page('welcome')

    def _build_welcome(self):
        page = WizardPage(self.hwnd)
        hwnd_static = win32gui.CreateWindowEx(
            0,
            'Static',
            'Welcome to the Steam Setup program.',
            win32con.WS_CHILD | win32con.WS_VISIBLE,
            20,
            20,
            440,
            40,
            self.hwnd,
            0,
            self.hInstance,
            None
        )
        page.hwnd = hwnd_static  # store handle for show/hide
        btn_next = win32gui.CreateWindowEx(
            0,
            'Button',
            'Next >',
            win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.BS_PUSHBUTTON,
            370,
            300,
            80,
            24,
            self.hwnd,
            1,
            self.hInstance,
            None
        )
        self.btn_next = btn_next
        btn_cancel = win32gui.CreateWindowEx(
            0,
            'Button',
            'Cancel',
            win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.BS_PUSHBUTTON,
            260,
            300,
            80,
            24,
            self.hwnd,
            2,
            self.hInstance,
            None
        )
        page.controls = [hwnd_static, btn_next, btn_cancel]
        return page

    def _build_install(self):
        page = WizardPage(self.hwnd)
        hwnd_static = win32gui.CreateWindowEx(
            0,
            'Static',
            'Installing...',
            win32con.WS_CHILD | win32con.WS_VISIBLE,
            20,
            20,
            440,
            40,
            self.hwnd,
            0,
            self.hInstance,
            None
        )
        page.hwnd = hwnd_static
        page.controls = [hwnd_static]
        return page

    def show_page(self, key):
        if self.cur_page:
            for ctl in self.pages[self.cur_page].controls:
                win32gui.ShowWindow(ctl, win32con.SW_HIDE)
        self.cur_page = key
        for ctl in self.pages[key].controls:
            win32gui.ShowWindow(ctl, win32con.SW_SHOW)

    def _wndProc(self, hwnd, msg, wparam, lparam):
        if msg == win32con.WM_COMMAND:
            ctl_id = win32gui.LOWORD(wparam)
            if ctl_id == 1:  # Next
                if self.cur_page == 'welcome':
                    self.show_page('install')
            elif ctl_id == 2:  # Cancel
                win32gui.DestroyWindow(self.hwnd)
        elif msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
        else:
            return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)
        return 0

    def run(self):
        win32gui.PumpMessages()

if __name__ == '__main__':
    SetupWizard().run()
