package main

import (
	"unsafe"

	"golang.org/x/sys/windows"
)

var (
	shell32              = windows.NewLazySystemDLL("shell32.dll")
	ole32                = windows.NewLazySystemDLL("ole32.dll")
	pSHBrowseForFolder   = shell32.NewProc("SHBrowseForFolderW")
	pSHGetPathFromIDList = shell32.NewProc("SHGetPathFromIDListW")
	pCoTaskMemFree       = ole32.NewProc("CoTaskMemFree")
	pGetActiveWindow     = windows.NewLazySystemDLL("user32.dll").NewProc("GetActiveWindow")
)

type browseInfoW struct {
	hwndOwner      uintptr
	pidlRoot       uintptr
	pszDisplayName *uint16
	lpszTitle      *uint16
	ulFlags        uint32
	lpfn           uintptr
	lParam         uintptr
	iImage         int32
}

// pickFolder shows the Windows folder picker. Returns "" when cancelled or unavailable.
func pickFolder(title string) string {
	disp := make([]uint16, windows.MAX_PATH)
	t, err := windows.UTF16PtrFromString(title)
	if err != nil {
		return ""
	}
	bi := browseInfoW{pszDisplayName: &disp[0], lpszTitle: t, ulFlags: 0x00000001} // BIF_RETURNONLYFSDIRS
	if h, _, _ := pGetActiveWindow.Call(); h != 0 {
		bi.hwndOwner = h
	}
	r, _, _ := pSHBrowseForFolder.Call(uintptr(unsafe.Pointer(&bi)))
	if r == 0 {
		return ""
	}
	defer pCoTaskMemFree.Call(r)
	buf := make([]uint16, windows.MAX_PATH)
	ok, _, _ := pSHGetPathFromIDList.Call(r, uintptr(unsafe.Pointer(&buf[0])))
	if ok == 0 {
		return ""
	}
	return windows.UTF16ToString(buf)
}
