//go:build windows

package main

import (
	"syscall"
	"unsafe"

	"golang.org/x/sys/windows"
)

// Tray icon + global hotkey (Ctrl+Alt+R) by subclassing the WebView2 host window.
// Compiled for Windows but never run on a real Windows machine by the builder.

const (
	wmApp       = 0x8000 + 1
	wmHotkey    = 0x0312
	wmClose     = 0x0010
	wmLButtonUp = 0x0202
	wmRButtonUp = 0x0205
	nimAdd      = 0
	nimDelete   = 2
	nifMessage  = 1
	nifIcon     = 2
	nifTip      = 4
	hotkeyID    = 0x5242
	modCtrlAlt  = 0x0002 | 0x0001 | 0x4000 // MOD_CONTROL | MOD_ALT | MOD_NOREPEAT
	gwlpWndProc = -4
	swHide      = 0
	swShow      = 5
	swRestore   = 9
)

type notifyIconData struct {
	CbSize           uint32
	HWnd             windows.HWND
	UID              uint32
	UFlags           uint32
	UCallbackMessage uint32
	HIcon            windows.Handle
	SzTip            [128]uint16
}

var (
	u32            = windows.NewLazySystemDLL("user32.dll")
	s32            = windows.NewLazySystemDLL("shell32.dll")
	pRegisterHK    = u32.NewProc("RegisterHotKey")
	pUnregisterHK  = u32.NewProc("UnregisterHotKey")
	pSetWinLong    = u32.NewProc("SetWindowLongPtrW")
	pCallWinProc   = u32.NewProc("CallWindowProcW")
	pShowWindow    = u32.NewProc("ShowWindow")
	pSetForeground = u32.NewProc("SetForegroundWindow")
	pIsVisible     = u32.NewProc("IsWindowVisible")
	pLoadImage     = u32.NewProc("LoadImageW")
	pNotifyIcon    = s32.NewProc("Shell_NotifyIconW")

	oldProc      uintptr
	trayHwnd     uintptr
	trayWanted   bool
	hotkeyWanted bool
	trayShown    bool
)

func showMain() {
	pShowWindow.Call(trayHwnd, swShow)
	pShowWindow.Call(trayHwnd, swRestore)
	pSetForeground.Call(trayHwnd)
}

// hotAdd: the global shortcut brings the window forward and opens the add-link dialog (clipboard prefill happens in the page, on this deliberate action only).
func hotAdd() {
	showMain()
	if wv != nil {
		wv.Dispatch(func() { wv.Eval("window.rbHotAdd&&window.rbHotAdd()") })
	}
}

func toggleMain() {
	if v, _, _ := pIsVisible.Call(trayHwnd); v != 0 {
		pShowWindow.Call(trayHwnd, swHide)
	} else {
		showMain()
	}
}

func trayData() *notifyIconData {
	d := &notifyIconData{HWnd: windows.HWND(trayHwnd), UID: 1, UFlags: nifMessage | nifIcon | nifTip, UCallbackMessage: wmApp}
	d.CbSize = uint32(unsafe.Sizeof(*d))
	hi, _, _ := pLoadImage.Call(mustModule(), 3, 1, 16, 16, 0x8000) // resource id 3, LR_SHARED
	d.HIcon = windows.Handle(hi)
	tip, _ := windows.UTF16FromString("راابط")
	copy(d.SzTip[:], tip)
	return d
}

var pGetModule = windows.NewLazySystemDLL("kernel32.dll").NewProc("GetModuleHandleW")

func mustModule() uintptr { h, _, _ := pGetModule.Call(0); return h }

func setTray(on bool) {
	trayWanted = on
	if on && !trayShown {
		pNotifyIcon.Call(nimAdd, uintptr(unsafe.Pointer(trayData())))
		trayShown = true
	} else if !on && trayShown {
		pNotifyIcon.Call(nimDelete, uintptr(unsafe.Pointer(trayData())))
		trayShown = false
		showMain()
	}
}

// hotkeyMods/hotkeyVK hold the last combination that registered successfully, so a failed change can fall back.
var hotkeyMods uint32 = 0x0002 | 0x0001
var hotkeyVK uint32 = 'R'

// setHotkey registers mods+vk (MOD_ALT=1, MOD_CONTROL=2, MOD_SHIFT=4). If the new combination is taken
// by another app, the previous one is registered again and false is returned.
func setHotkey(on bool, mods, vk uint32) bool {
	hotkeyWanted = on
	if !on {
		pUnregisterHK.Call(trayHwnd, hotkeyID)
		return true
	}
	if mods&0x7 == 0 || vk == 0 {
		return false
	}
	pUnregisterHK.Call(trayHwnd, hotkeyID)
	r, _, _ := pRegisterHK.Call(trayHwnd, hotkeyID, uintptr(mods&0x7|0x4000), uintptr(vk))
	if r != 0 {
		hotkeyMods, hotkeyVK = mods&0x7, vk
		return true
	}
	pRegisterHK.Call(trayHwnd, hotkeyID, uintptr(hotkeyMods|0x4000), uintptr(hotkeyVK))
	return false
}

func wndProc(hwnd, msg, wp, lp uintptr) uintptr {
	switch msg {
	case wmHotkey:
		if wp == hotkeyID {
			hotAdd()
			return 0
		}
	case wmApp:
		if lp == wmLButtonUp {
			toggleMain()
			return 0
		}
		if lp == wmRButtonUp {
			trayMenu(hwnd)
			return 0
		}
	case wmClose:
		if trayWanted { // with tray on, X hides to tray instead of quitting
			pShowWindow.Call(hwnd, swHide)
			return 0
		}
		if trayShown {
			pNotifyIcon.Call(nimDelete, uintptr(unsafe.Pointer(trayData())))
		}
	}
	r, _, _ := pCallWinProc.Call(oldProc, hwnd, msg, wp, lp)
	return r
}

type point struct{ X, Y int32 }

var (
	pCreatePopup = u32.NewProc("CreatePopupMenu")
	pAppendMenu  = u32.NewProc("AppendMenuW")
	pTrackPopup  = u32.NewProc("TrackPopupMenu")
	pDestroyMenu = u32.NewProc("DestroyMenu")
	pGetCursor   = u32.NewProc("GetCursorPos")
)

const (
	idShow = 1
	idAdd  = 2
	idExit = 3
)

// trayMenu: right-click menu with Show, Add link, Exit.
func trayMenu(hwnd uintptr) {
	m, _, _ := pCreatePopup.Call()
	add := func(id uintptr, label string) {
		p, _ := windows.UTF16PtrFromString(label)
		pAppendMenu.Call(m, 0, id, uintptr(unsafe.Pointer(p)))
	}
	add(idShow, "فتح راابط")
	add(idAdd, "إضافة رابط")
	add(idExit, "خروج")
	var pt point
	pGetCursor.Call(uintptr(unsafe.Pointer(&pt)))
	pSetForeground.Call(hwnd)
	// TPM_RETURNCMD(0x100) | TPM_NONOTIFY(0x80)
	cmd, _, _ := pTrackPopup.Call(m, 0x100|0x80, uintptr(pt.X), uintptr(pt.Y), 0, hwnd, 0)
	pDestroyMenu.Call(m)
	switch cmd {
	case idShow:
		showMain()
	case idAdd:
		hotAdd()
	case idExit:
		trayWanted = false // let WM_CLOSE really close
		pPostMessage.Call(hwnd, wmClose, 0, 0)
	}
}

var pPostMessage = u32.NewProc("PostMessageW")

func initTray(hwnd uintptr) {
	trayHwnd = hwnd
	cb := syscall.NewCallback(wndProc)
	neg := gwlpWndProc
	oldProc, _, _ = pSetWinLong.Call(hwnd, uintptr(neg), cb)
}
