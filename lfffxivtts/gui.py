import threading

import wx
import sys
from config import read_config, write_config
from client import start_client
import sounddevice as sd

LANGUAGE_CHOICES = ["auto", "en", "de", "fr", "jp"]
LANGUAGE_CHOICES_LABELS = ["Auto-select language", "English", "German", "French", "Japanese"]


class RedirectText:
    def __init__(self, text_ctrl):
        self.output = text_ctrl

    def write(self, string):
        wx.CallAfter(self.output.WriteText, string)


class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Local Fast FFXIV TTS", size=(800, 600))
        icon = wx.Icon("lfffxivtts/resources/icon.ico", wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)

        panel = wx.Panel(self)

        self.config = read_config()
        self.config["tts"]["enableVoiceFixer"] = False  # Currently broken due to multiprocessing
        self.voice_server = None

        self.log_text = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.log_text.SetFont(wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))

        websocket_panel = wx.Panel(panel)
        checkbox_panel = wx.Panel(panel)
        volume_panel = wx.Panel(panel)

        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        panel_sizer.Add(websocket_panel, flag=wx.EXPAND | wx.ALL, border=5)
        panel_sizer.Add(self.log_text, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)
        panel_sizer.Add(checkbox_panel, flag=wx.ALL, border=5)
        panel_sizer.Add(volume_panel, flag=wx.EXPAND | wx.ALL, border=5)

        # Websocket settings panel
        websocket_panel_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.websocket_uri = wx.TextCtrl(websocket_panel)
        self.websocket_uri.SetValue(self.config["websocketURI"])
        self.confirm_websocket_uri = wx.Button(websocket_panel, label="Connect")

        websocket_panel_sizer.Add(wx.StaticText(websocket_panel, label="Websocket URI (ws://)"),
                                  flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)
        websocket_panel_sizer.Add(self.websocket_uri, flag=wx.EXPAND | wx.ALL, border=5, proportion=1)
        websocket_panel_sizer.Add(self.confirm_websocket_uri, flag=wx.ALL, border=5)
        websocket_panel.SetSizer(websocket_panel_sizer)

        # Checkbox settings panel
        checkbox_panel_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.select_language = wx.Choice(checkbox_panel, choices=LANGUAGE_CHOICES)
        for i, text in enumerate(LANGUAGE_CHOICES_LABELS):
            self.select_language.SetString(i, text)

        # self.checkbox_enable_voicefixer = wx.CheckBox(checkbox_panel, label="voicefixer (CPU intensive)")
        self.checkbox_enable_noisereduce = wx.CheckBox(checkbox_panel, label="noisereduce")
        self.checkbox_enable_tts = wx.CheckBox(checkbox_panel, label="Enable TTS")

        self.select_language.SetSelection(LANGUAGE_CHOICES.index(self.config["language"]))
        # self.checkbox_enable_voicefixer.SetValue(self.config["tts"]["enableVoiceFixer"])
        self.checkbox_enable_noisereduce.SetValue(self.config["tts"]["enableNoiseReduce"])
        self.checkbox_enable_tts.SetValue(self.config["enable"])

        checkbox_panel_sizer.Add(self.select_language, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)
        checkbox_panel_sizer.Add(self.checkbox_enable_tts, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)
        # checkbox_panel_sizer.Add(self.checkbox_enable_voicefixer, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)
        checkbox_panel_sizer.Add(self.checkbox_enable_noisereduce, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)

        checkbox_panel.SetSizer(checkbox_panel_sizer)

        # Volume/TTS stop panel
        volume_panel_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.volume_slider = wx.Slider(volume_panel, value=int(self.config["volume"] * 100))

        self.audio_output_devices = [{"index": -1, "name": "Default"}] + [device for device in sd.query_devices() if
                                                                          device["max_output_channels"] > 0]
        self.device_choice = wx.Choice(volume_panel,
                                       choices=[str(device["index"]) for device in self.audio_output_devices])

        for i, device in enumerate(self.audio_output_devices):
            self.device_choice.SetString(i, device["name"])
            if str(device["index"]) == str(self.config["outputDeviceIndex"]):
                self.device_choice.SetSelection(i)

        volume_panel_sizer.Add(wx.StaticText(volume_panel, label="Volume"),
                               flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)
        volume_panel_sizer.Add(self.volume_slider, flag=wx.ALL | wx.EXPAND, border=5, proportion=1)
        volume_panel_sizer.Add(self.device_choice, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL, border=5)

        volume_panel.SetSizer(volume_panel_sizer)

        panel.SetSizer(panel_sizer)

        # Event binding
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_SHOW, self.on_show)
        sys.stdout = RedirectText(self.log_text)

        self.volume_slider.Bind(wx.EVT_SLIDER, self.on_change_volume)
        self.select_language.Bind(wx.EVT_CHOICE, self.on_select_language)
        self.device_choice.Bind(wx.EVT_CHOICE, self.on_select_device)
        # self.checkbox_enable_voicefixer.Bind(wx.EVT_CHECKBOX, self.on_toggle_voicefixer)
        self.checkbox_enable_noisereduce.Bind(wx.EVT_CHECKBOX, self.on_toggle_noisereduce)
        self.checkbox_enable_tts.Bind(wx.EVT_CHECKBOX, self.on_toggle_tts)

        self.confirm_websocket_uri.Bind(wx.EVT_BUTTON, self.on_confirm_websocket_uri)

    def on_select_device(self, event):
        new_device = self.audio_output_devices[self.device_choice.GetSelection()]
        print("[>] output device =", new_device["name"])
        self.config["outputDeviceIndex"] = new_device["index"]
        write_config(self.config)

    def on_select_language(self, event):
        new_lang = LANGUAGE_CHOICES[self.select_language.GetSelection()]
        print("[>] language =", new_lang)
        self.config["language"] = new_lang
        write_config(self.config)

    def on_change_volume(self, event):
        new_volume = self.volume_slider.GetValue() / 100
        print("[>] volume =", new_volume, "(WILL BE APPLIED ON THE NEXT TTS)")
        self.config["volume"] = new_volume
        write_config(self.config)

    def on_confirm_websocket_uri(self, event):
        new_uri = self.websocket_uri.GetValue()
        if not new_uri.startswith("ws://"):
            print("[!] INVALID websocket URI. Should have the format ws://<host>:port/")
            return
        print("[>] websocket URI =", new_uri)
        print("[!] YOU MIGHT NEED A RESTART IF IT DOESN'T CONNECT AUTOMATICALLY")
        self.config["websocketURI"] = new_uri
        write_config(self.config)

    # def on_toggle_voicefixer(self, event):
    #     print("[>] voicefixer =", self.checkbox_enable_voicefixer.GetValue())
    #     if self.checkbox_enable_voicefixer.GetValue() and "voicefixer" not in self.config:
    #         print("[!] PLEASE RESTART THE APP TO ENABLE VOICEFIXER")
    #     self.config["tts"]["enableVoiceFixer"] = self.checkbox_enable_voicefixer.GetValue()
    #     write_config(self.config)

    def on_toggle_noisereduce(self, event):
        print("[>] noisereduce =", self.checkbox_enable_noisereduce.GetValue())
        self.config["tts"]["enableNoiseReduce"] = self.checkbox_enable_noisereduce.GetValue()
        write_config(self.config)

    def on_toggle_tts(self, event):
        print("[>] tts enabled =", self.checkbox_enable_tts.GetValue())
        self.config["enable"] = self.checkbox_enable_tts.GetValue()
        write_config(self.config)

    def on_show(self, event):
        print("[i] Starting lfFFXIVTTS ...")
        self.voice_server = threading.Thread(target=start_client, args=(self.config,), daemon=True)
        self.voice_server.start()

    def on_close(self, event):
        self.Destroy()
