import wx
from gui import MainFrame
import asyncio
import multiprocessing


def main():
    app = wx.App()
    frame = MainFrame()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")
    main()
