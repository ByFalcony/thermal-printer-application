"""Masaüstüne ve Başlat menüsüne simgeli 'Fiş Yazıcı' kısayolu oluşturur.

Kısayol, uygulamayla aynı AppUserModelID'yi taşır; böylece görev çubuğuna
sabitlendiğinde de Python simgesi yerine uygulamanın simgesi görünür.
Gerekli: pip install pywin32
"""
import os
import sys

import pythoncom
from win32com.client import Dispatch
from win32com.propsys import propsys, pscon
from win32com.shell import shell, shellcon

HERE = os.path.dirname(os.path.abspath(__file__))
APP_ID = "Emir.FisYazici.1"   # app.py içindeki APP_ID ile aynı olmalı
NAME = "Fiş Yazıcı"


def pythonw_path():
    exe = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return exe if os.path.exists(exe) else sys.executable


def make_shortcut(folder):
    path = os.path.join(folder, NAME + ".lnk")
    sc = Dispatch("WScript.Shell").CreateShortcut(path)
    sc.TargetPath = pythonw_path()
    sc.Arguments = f'"{os.path.join(HERE, "app.py")}"'
    sc.WorkingDirectory = HERE
    sc.IconLocation = os.path.join(HERE, "icon.ico") + ",0"
    sc.Description = "X5h mini termal yazıcı için fiş tasarlama ve yazdırma"
    sc.Save()

    store = propsys.SHGetPropertyStoreFromParsingName(path, None, shellcon.GPS_READWRITE,
                                                      propsys.IID_IPropertyStore)
    store.SetValue(pscon.PKEY_AppUserModel_ID, propsys.PROPVARIANTType(APP_ID, pythoncom.VT_LPWSTR))
    store.Commit()
    return path


def main():
    desktop = shell.SHGetFolderPath(0, shellcon.CSIDL_DESKTOPDIRECTORY, None, 0)
    programs = shell.SHGetFolderPath(0, shellcon.CSIDL_PROGRAMS, None, 0)
    for folder in (desktop, programs):
        print("Oluşturuldu:", make_shortcut(folder))


if __name__ == "__main__":
    main()
