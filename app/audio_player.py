#!/usr/bin/env python3
"""
Audio Player using GStreamer 1.0 for GNOME / Linux
Supports playback, pause, stop, seeking, and position tracking.
"""

import os
from pathlib import Path
import gi

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

# Initialize GStreamer once
Gst.init(None)


class AudioPlayer:
    def __init__(self, on_eos_callback=None, on_state_change=None):
        self.player = Gst.ElementFactory.make("playbin", "audio_player")
        self.bus = self.player.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect("message", self._on_bus_message)
        
        self.on_eos_callback = on_eos_callback
        self.on_state_change = on_state_change
        self.current_file = None
        self._is_playing = False
        self._duration = 0.0

    def _on_bus_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            self._is_playing = False
            self.player.set_state(Gst.State.NULL)
            if self.on_eos_callback:
                self.on_eos_callback()
            if self.on_state_change:
                self.on_state_change(False)
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"[AudioPlayer] Error: {err}, debug: {debug}")
            self.stop()
        elif t == Gst.MessageType.STATE_CHANGED:
            if message.src == self.player:
                old_state, new_state, pending = message.parse_state_changed()
                is_play = (new_state == Gst.State.PLAYING)
                if is_play != self._is_playing:
                    self._is_playing = is_play
                    if self.on_state_change:
                        self.on_state_change(self._is_playing)

    def load(self, filepath: str):
        self.stop()
        abs_path = os.path.abspath(filepath)
        self.current_file = abs_path
        uri = Path(abs_path).as_uri()
        self.player.set_property("uri", uri)
        
        # Query duration after a brief preroll
        self.player.set_state(Gst.State.PAUSED)
        GLib.timeout_add(100, self._update_duration)

    def _update_duration(self):
        success, duration = self.player.query_duration(Gst.Format.TIME)
        if success and duration > 0:
            self._duration = duration / Gst.SECOND
        return False

    def play(self):
        if not self.current_file:
            return False
        self.player.set_state(Gst.State.PLAYING)
        self._is_playing = True
        return True

    def pause(self):
        self.player.set_state(Gst.State.PAUSED)
        self._is_playing = False

    def toggle(self):
        if self._is_playing:
            self.pause()
        else:
            self.play()

    def stop(self):
        self.player.set_state(Gst.State.NULL)
        self._is_playing = False
        if self.on_state_change:
            self.on_state_change(False)

    def seek(self, seconds: float):
        if not self.current_file:
            return
        seconds = max(0.0, float(seconds))
        time_nanos = int(seconds * Gst.SECOND)
        self.player.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            time_nanos
        )

    def get_position(self) -> float:
        if not self.current_file:
            return 0.0
        success, pos = self.player.query_position(Gst.Format.TIME)
        if success and pos >= 0:
            return pos / Gst.SECOND
        return 0.0

    def get_duration(self) -> float:
        if self._duration > 0:
            return self._duration
        if not self.current_file:
            return 0.0
        success, duration = self.player.query_duration(Gst.Format.TIME)
        if success and duration > 0:
            self._duration = duration / Gst.SECOND
            return self._duration
        return 0.0

    def is_playing(self) -> bool:
        return self._is_playing
