#!/usr/bin/env python3
"""
Ứng dụng: Văn bản thành giọng đọc (Text-to-Speech)
Giao diện chuẩn GNOME / Linux sử dụng GTK 4 và Libadwaita.
Tích hợp mô hình V-TTS siêu nhẹ hỗ trợ đa giọng tiếng Việt & nhân bản giọng nói.
"""

import os
import sys
import re
import time
import threading
import tempfile
from pathlib import Path

# Add local app and engine directories
APP_DIR = Path(__file__).parent.resolve()
ROOT_DIR = APP_DIR.parent
ENGINE_DIR = ROOT_DIR / "engine"
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ENGINE_DIR))
sys.path.insert(0, str(APP_DIR))

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gio', '2.0')
from gi.repository import Gtk, Adw, Gio, GLib, Gdk

from tts_engine import TTSEngine
from audio_player import AudioPlayer

APP_ID = "io.github.adfoxtheme.VanBanThanhGiongDoc"


def format_time(seconds: float) -> str:
    """Format seconds into MM:SS string."""
    seconds = max(0, int(seconds))
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins:02d}:{secs:02d}"


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title("Văn bản thành giọng đọc")
        self.set_default_size(1020, 720)
        self.set_size_request(850, 600)

        # Core Engines
        self.engine = TTSEngine()
        self.player = AudioPlayer(
            on_eos_callback=self._on_player_eos,
            on_state_change=self._on_player_state_change
        )
        self.temp_audio_file = None
        self.last_audio_data = None
        self.last_sample_rate = 24000
        self.is_generating = False
        self.playback_timer_id = None
        self.reference_audio_path = None

        # Build UI
        self._setup_ui()
        self._apply_css()

        # Load engine in background
        threading.Thread(target=self._init_engine_background, daemon=True).start()

    def _setup_ui(self):
        # Toast Overlay (for notifications)
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        # Main Box (Vertical)
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.toast_overlay.set_child(main_box)

        # HeaderBar
        self.header_bar = Adw.HeaderBar()
        self.window_title = Adw.WindowTitle(
            title="Văn bản thành giọng đọc",
            subtitle="Đang khởi tạo mô hình AI..."
        )
        self.header_bar.set_title_widget(self.window_title)
        main_box.append(self.header_bar)

        # Left Header Buttons
        btn_box_left = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        self.btn_open = Gtk.Button(
            icon_name="document-open-symbolic",
            tooltip_text="Mở tệp văn bản (.txt, .srt)"
        )
        self.btn_open.connect("clicked", self._on_open_file_clicked)
        btn_box_left.append(self.btn_open)

        self.btn_paste = Gtk.Button(
            icon_name="edit-paste-symbolic",
            tooltip_text="Dán văn bản từ bộ nhớ tạm"
        )
        self.btn_paste.connect("clicked", self._on_paste_clicked)
        btn_box_left.append(self.btn_paste)

        self.btn_clear = Gtk.Button(
            icon_name="edit-clear-symbolic",
            tooltip_text="Xoá toàn bộ nội dung"
        )
        self.btn_clear.connect("clicked", self._on_clear_clicked)
        btn_box_left.append(self.btn_clear)

        self.header_bar.pack_start(btn_box_left)

        # Right Header Buttons
        btn_box_right = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        # Export Button
        self.btn_export_header = Gtk.Button(
            icon_name="document-save-symbolic",
            tooltip_text="Lưu file âm thanh (.wav)"
        )
        self.btn_export_header.set_sensitive(False)
        self.btn_export_header.connect("clicked", self._on_export_clicked)
        btn_box_right.append(self.btn_export_header)

        # Play / Generate Action Button in HeaderBar
        self.btn_main_action = Gtk.Button()
        self.btn_main_action.add_css_class("suggested-action")
        self.btn_main_action.set_tooltip_text("Tạo giọng đọc (TTS)")
        btn_header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.icon_header_action = Gtk.Image.new_from_icon_name("media-playback-start-symbolic")
        self.lbl_header_action = Gtk.Label(label="Tạo TTS")
        btn_header_box.append(self.icon_header_action)
        btn_header_box.append(self.lbl_header_action)
        self.btn_main_action.set_child(btn_header_box)
        self.btn_main_action.connect("clicked", self._on_main_action_clicked)
        btn_box_right.append(self.btn_main_action)

        # App Menu
        menu_button = Gtk.MenuButton(icon_name="open-menu-symbolic")
        menu = Gio.Menu()
        menu.append("Văn bản mẫu", "app.sample_text")
        menu.append("Thông tin ứng dụng", "app.about")
        menu_button.set_menu_model(menu)
        btn_box_right.append(menu_button)

        self.header_bar.pack_end(btn_box_right)

        # Content Paned (Split view: Editor on Left, Controls on Right)
        self.paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.paned.set_position(560)
        self.paned.set_wide_handle(True)
        self.paned.set_vexpand(True)
        self.paned.set_hexpand(True)
        main_box.append(self.paned)

        # LEFT PANE: Text Editor
        left_box = self._create_editor_pane()
        self.paned.set_start_child(left_box)

        # RIGHT PANE: Voice Controls & Player
        right_box = self._create_control_pane()
        self.paned.set_end_child(right_box)

        # Initialize button states
        self._update_action_button_state(is_running=False)

    def _create_editor_pane(self) -> Gtk.Box:
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        container.set_margin_start(16)
        container.set_margin_end(8)
        container.set_margin_top(16)
        container.set_margin_bottom(16)

        # Top Bar: Label & Quick actions
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        lbl_title = Gtk.Label(label="Nội dung văn bản")
        lbl_title.add_css_class("heading")
        top_bar.append(lbl_title)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        top_bar.append(spacer)

        btn_sample = Gtk.Button(label="Dán văn bản mẫu")
        btn_sample.add_css_class("flat")
        btn_sample.add_css_class("caption")
        btn_sample.connect("clicked", lambda b: self._load_sample_text())
        top_bar.append(btn_sample)

        container.append(top_bar)

        # Editor Card (Frame with ScrolledWindow + TextView)
        editor_frame = Gtk.Frame()
        editor_frame.add_css_class("card")
        editor_frame.set_vexpand(True)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        editor_frame.set_child(scrolled)

        self.text_view = Gtk.TextView()
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self.text_view.set_left_margin(16)
        self.text_view.set_right_margin(16)
        self.text_view.set_top_margin(16)
        self.text_view.set_bottom_margin(16)
        self.text_view.add_css_class("editor-text")
        
        self.text_buffer = self.text_view.get_buffer()
        self.text_buffer.connect("changed", self._on_text_changed)
        scrolled.set_child(self.text_view)

        container.append(editor_frame)

        # Main Generate TTS Action Button (Prominent, below editor)
        action_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        action_btn_box.set_margin_top(4)
        action_btn_box.set_margin_bottom(4)

        self.btn_generate_tts = Gtk.Button()
        self.btn_generate_tts.add_css_class("suggested-action")
        self.btn_generate_tts.add_css_class("pill")
        self.btn_generate_tts.set_hexpand(True)
        self.btn_generate_tts.set_size_request(-1, 46)
        self.btn_generate_tts.set_tooltip_text("Bắt đầu chuyển đổi văn bản thành giọng đọc (TTS)")
        self.btn_generate_tts.connect("clicked", self._on_main_action_clicked)

        btn_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_content.set_halign(Gtk.Align.CENTER)
        self.icon_generate = Gtk.Image.new_from_icon_name("media-playback-start-symbolic")
        self.icon_generate.set_pixel_size(18)
        self.lbl_generate = Gtk.Label(label="🚀  Tạo giọng đọc (TTS)")
        self.lbl_generate.add_css_class("title-4")
        btn_content.append(self.icon_generate)
        btn_content.append(self.lbl_generate)
        self.btn_generate_tts.set_child(btn_content)

        action_btn_box.append(self.btn_generate_tts)
        container.append(action_btn_box)

        # Bottom Stats Bar
        stats_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        
        self.lbl_stats = Gtk.Label(label="0 ký tự  •  0 từ  •  Ước tính: ~0 giây")
        self.lbl_stats.add_css_class("caption")
        self.lbl_stats.add_css_class("dim-label")
        stats_bar.append(self.lbl_stats)

        spacer2 = Gtk.Box()
        spacer2.set_hexpand(True)
        stats_bar.append(spacer2)

        # Natural Pause Switch
        lbl_pause = Gtk.Label(label="Ngắt nghỉ tự nhiên:")
        lbl_pause.add_css_class("caption")
        lbl_pause.add_css_class("dim-label")
        stats_bar.append(lbl_pause)

        self.switch_natural_pause = Gtk.Switch()
        self.switch_natural_pause.set_active(True)
        self.switch_natural_pause.set_valign(Gtk.Align.CENTER)
        self.switch_natural_pause.set_tooltip_text("Tự động phân tách và ngắt nghỉ tự nhiên giữa các câu")
        stats_bar.append(self.switch_natural_pause)

        container.append(stats_bar)
        return container

    def _create_control_pane(self) -> Gtk.ScrolledWindow:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_margin_start(8)
        scrolled.set_margin_end(16)
        scrolled.set_margin_top(16)
        scrolled.set_margin_bottom(16)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content_box.set_margin_end(5)
        scrolled.set_child(content_box)

        # Mode Selection: Presets vs Voice Clone
        mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        mode_box.add_css_class("linked")
        mode_box.set_halign(Gtk.Align.CENTER)

        self.btn_mode_preset = Gtk.ToggleButton(label="🎙️  Giọng đọc có sẵn")
        self.btn_mode_preset.set_active(True)
        self.btn_mode_clone = Gtk.ToggleButton(label="✨  Nhân bản giọng nói")
        self.btn_mode_clone.set_group(self.btn_mode_preset)

        self.btn_mode_preset.connect("toggled", self._on_mode_toggled)
        mode_box.append(self.btn_mode_preset)
        mode_box.append(self.btn_mode_clone)
        content_box.append(mode_box)

        # Stack for Presets vs Cloning
        self.stack_mode = Gtk.Stack()
        self.stack_mode.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        content_box.append(self.stack_mode)

        # --- TAB 1: PRESET VOICES ---
        preset_group = Adw.PreferencesGroup(title="Chọn giọng đọc")
        
        self.speaker_rows = []
        self.selected_speaker_id = "NF"

        speakers = self.engine.get_speakers()
        self.speaker_action_group = None

        for spk in speakers:
            row = Adw.ActionRow(
                title=spk["name"],
                subtitle=spk["desc"]
            )
            row.set_activatable(True)
            check = Gtk.CheckButton()
            if self.speaker_action_group is None:
                self.speaker_action_group = check
            else:
                check.set_group(self.speaker_action_group)

            if spk["id"] == "NF":
                check.set_active(True)

            check.connect("toggled", self._create_speaker_toggle_handler(spk["id"]))
            row.add_prefix(check)
            row.connect("activated", lambda r, c=check: c.set_active(True))
            preset_group.add(row)

        self.stack_mode.add_named(preset_group, "preset")

        # --- TAB 2: VOICE CLONING ---
        clone_group = Adw.PreferencesGroup(
            title="Nhân bản giọng bất kỳ (Zero-Shot)",
            description="Tải file âm thanh mẫu từ 3 đến 10 giây để AI mô phỏng giọng nói"
        )

        row_file = Adw.ActionRow(
            title="File âm thanh mẫu (.wav, .mp3)",
            subtitle="Chưa chọn file nào"
        )
        self.row_clone_file = row_file

        btn_choose_audio = Gtk.Button(label="Chọn tệp")
        btn_choose_audio.set_valign(Gtk.Align.CENTER)
        btn_choose_audio.connect("clicked", self._on_choose_reference_audio)
        row_file.add_suffix(btn_choose_audio)
        clone_group.add(row_file)

        # Reference preview row
        self.row_clone_preview = Adw.ActionRow(
            title="Nghe thử file mẫu",
            subtitle="Kiểm tra giọng nói trước khi nhân bản"
        )
        self.btn_play_ref = Gtk.Button(icon_name="media-playback-start-symbolic")
        self.btn_play_ref.set_valign(Gtk.Align.CENTER)
        self.btn_play_ref.set_sensitive(False)
        self.btn_play_ref.connect("clicked", self._on_play_reference_clicked)
        self.row_clone_preview.add_suffix(self.btn_play_ref)
        clone_group.add(self.row_clone_preview)

        self.stack_mode.add_named(clone_group, "clone")

        # --- SECTION: SETTINGS ---
        settings_group = Adw.PreferencesGroup(title="Tinh chỉnh phát âm")
        
        # Speed Row
        speed_row = Adw.ActionRow(
            title="Tốc độ đọc",
            subtitle="Điều chỉnh nhịp điệu đọc nhanh hoặc chậm"
        )
        self.lbl_speed_val = Gtk.Label(label="1.00x")
        self.lbl_speed_val.add_css_class("badge")
        self.lbl_speed_val.set_valign(Gtk.Align.CENTER)

        self.slider_speed = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.5, 2.0, 0.05)
        self.slider_speed.set_value(1.0)
        self.slider_speed.set_size_request(160, -1)
        self.slider_speed.set_valign(Gtk.Align.CENTER)
        self.slider_speed.connect("value-changed", self._on_speed_changed)

        speed_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        speed_box.append(self.slider_speed)
        speed_box.append(self.lbl_speed_val)
        speed_row.add_suffix(speed_box)
        settings_group.add(speed_row)

        content_box.append(settings_group)

        # --- SECTION: AUDIO PLAYER WIDGET ---
        player_group = Adw.PreferencesGroup(title="Trình phát âm thanh")

        player_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        player_card.add_css_class("card")
        player_card.add_css_class("player-card")
        player_card.set_margin_start(0)
        player_card.set_margin_end(0)
        player_card.set_margin_top(4)
        player_card.set_margin_bottom(4)

        # Progress bar (Visible when generating)
        self.gen_progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.gen_progress_bar = Gtk.ProgressBar()
        self.gen_progress_bar.set_fraction(0.0)
        self.gen_status_label = Gtk.Label(label="Đang chuẩn bị...")
        self.gen_status_label.add_css_class("caption")
        self.gen_status_label.set_halign(Gtk.Align.START)
        self.gen_progress_box.append(self.gen_status_label)
        self.gen_progress_box.append(self.gen_progress_bar)
        self.gen_progress_box.set_visible(False)
        player_card.append(self.gen_progress_box)

        # Timeline Slider & Time Labels
        timeline_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.lbl_time_current = Gtk.Label(label="00:00")
        self.lbl_time_current.add_css_class("numeric")
        self.lbl_time_current.add_css_class("caption")

        self.slider_playback = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.0, 100.0, 0.1)
        self.slider_playback.set_hexpand(True)
        self.slider_playback.set_sensitive(False)
        self.slider_playback.connect("change-value", self._on_seek_requested)

        self.lbl_time_total = Gtk.Label(label="00:00")
        self.lbl_time_total.add_css_class("numeric")
        self.lbl_time_total.add_css_class("caption")

        timeline_box.append(self.lbl_time_current)
        timeline_box.append(self.slider_playback)
        timeline_box.append(self.lbl_time_total)
        player_card.append(timeline_box)

        # Player Controls Row
        ctrl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        ctrl_box.set_halign(Gtk.Align.CENTER)

        self.btn_seek_back = Gtk.Button(icon_name="media-seek-backward-symbolic")
        self.btn_seek_back.set_tooltip_text("Lùi 5 giây")
        self.btn_seek_back.connect("clicked", lambda b: self._seek_relative(-5))
        self.btn_seek_back.set_sensitive(False)
        ctrl_box.append(self.btn_seek_back)

        self.btn_play_pause = Gtk.Button(icon_name="media-playback-start-symbolic")
        self.btn_play_pause.add_css_class("suggested-action")
        self.btn_play_pause.add_css_class("circular")
        self.btn_play_pause.set_size_request(46, 46)
        self.btn_play_pause.set_tooltip_text("Phát / Tạm dừng")
        self.btn_play_pause.connect("clicked", self._on_play_pause_clicked)
        self.btn_play_pause.set_sensitive(False)
        ctrl_box.append(self.btn_play_pause)

        self.btn_seek_forward = Gtk.Button(icon_name="media-seek-forward-symbolic")
        self.btn_seek_forward.set_tooltip_text("Tiến 5 giây")
        self.btn_seek_forward.connect("clicked", lambda b: self._seek_relative(5))
        self.btn_seek_forward.set_sensitive(False)
        ctrl_box.append(self.btn_seek_forward)

        self.btn_stop = Gtk.Button(icon_name="media-playback-stop-symbolic")
        self.btn_stop.set_tooltip_text("Dừng hẳn")
        self.btn_stop.connect("clicked", lambda b: self.player.stop())
        self.btn_stop.set_sensitive(False)
        ctrl_box.append(self.btn_stop)

        player_card.append(ctrl_box)

        # Quick Save Button
        self.btn_save_audio = Gtk.Button(label="Lưu file âm thanh (.wav)")
        self.btn_save_audio.add_css_class("pill")
        self.btn_save_audio.set_halign(Gtk.Align.CENTER)
        self.btn_save_audio.set_sensitive(False)
        self.btn_save_audio.connect("clicked", self._on_export_clicked)
        player_card.append(self.btn_save_audio)

        player_group.add(player_card)
        content_box.append(player_group)

        return scrolled

    def _apply_css(self):
        css_provider = Gtk.CssProvider()
        css = """
        .editor-text {
            font-size: 15px;
            line-height: 1.6;
        }
        .player-card {
            padding: 16px;
        }
        .badge {
            background-color: alpha(@accent_color, 0.15);
            color: @accent_color;
            border-radius: 6px;
            padding: 2px 8px;
            font-weight: bold;
            font-size: 12px;
        }
        .numeric {
            font-variant-numeric: tabular-nums;
        }
        """
        css_provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _create_speaker_toggle_handler(self, speaker_id):
        def handler(button):
            if button.get_active():
                self.selected_speaker_id = speaker_id
        return handler

    def _init_engine_background(self):
        def on_progress(msg):
            GLib.idle_add(self._update_init_status, msg)

        success = self.engine.load_models(on_progress=on_progress)
        GLib.idle_add(self._on_engine_initialized, success)

    def _update_init_status(self, msg):
        self.window_title.set_subtitle(msg)

    def _on_engine_initialized(self, success):
        if success:
            self.window_title.set_subtitle("Sẵn sàng")
            self.btn_main_action.set_sensitive(True)
            if hasattr(self, 'btn_generate_tts'):
                self.btn_generate_tts.set_sensitive(True)
            self._on_text_changed(self.text_buffer)
            self._show_toast("Mô hình AI đọc tiếng Việt đã sẵn sàng!")
        else:
            self.window_title.set_subtitle("Lỗi khởi tạo mô hình")
            self._show_toast("Không thể tải mô hình TTS. Vui lòng kiểm tra lại kết nối.")

    def _update_action_button_state(self, is_running: bool):
        if is_running:
            if hasattr(self, 'lbl_generate'):
                self.lbl_generate.set_label("🛑  Dừng tạo âm thanh")
                self.icon_generate.set_from_icon_name("media-playback-stop-symbolic")
                self.btn_generate_tts.remove_css_class("suggested-action")
                self.btn_generate_tts.add_css_class("destructive-action")
            if hasattr(self, 'lbl_header_action'):
                self.lbl_header_action.set_label("Dừng")
                self.icon_header_action.set_from_icon_name("media-playback-stop-symbolic")
            self.btn_main_action.remove_css_class("suggested-action")
            self.btn_main_action.add_css_class("destructive-action")
        else:
            if hasattr(self, 'lbl_generate'):
                self.lbl_generate.set_label("🚀  Tạo giọng đọc (TTS)")
                self.icon_generate.set_from_icon_name("media-playback-start-symbolic")
                self.btn_generate_tts.remove_css_class("destructive-action")
                self.btn_generate_tts.add_css_class("suggested-action")
            if hasattr(self, 'lbl_header_action'):
                self.lbl_header_action.set_label("Tạo TTS")
                self.icon_header_action.set_from_icon_name("media-playback-start-symbolic")
            self.btn_main_action.remove_css_class("destructive-action")
            self.btn_main_action.add_css_class("suggested-action")

    def _on_text_changed(self, buffer):
        start, end = buffer.get_bounds()
        text = buffer.get_text(start, end, True).strip()
        chars = len(text)
        words = len(text.split()) if text else 0
        # Estimate duration: average Vietnamese reading rate is ~3 words per second (180 wpm)
        est_seconds = int(words / 3.0)
        self.lbl_stats.set_label(f"{chars:,} ký tự  •  {words:,} từ  •  Ước tính: ~{est_seconds} giây")

    def _on_mode_toggled(self, button):
        if self.btn_mode_preset.get_active():
            self.stack_mode.set_visible_child_name("preset")
        else:
            self.stack_mode.set_visible_child_name("clone")

    def _on_speed_changed(self, scale):
        val = scale.get_value()
        self.lbl_speed_val.set_label(f"{val:.2f}x")

    def _load_sample_text(self):
        sample = (
            "Chào mừng bạn đến với ứng dụng Văn bản thành giọng đọc trên Ubuntu Linux!\n\n"
            "Ứng dụng được thiết kế hoàn toàn theo phong cách hiện đại Libadwaita của GNOME, "
            "tích hợp mô hình trí tuệ nhân tạo V-TTS siêu nhẹ giúp tổng hợp giọng đọc tiếng Việt "
            "tự nhiên, mượt mà và chạy trực tiếp trên vi xử lý CPU mà không làm chậm máy tính của bạn.\n\n"
            "Bạn có thể chọn giọng đọc miền Bắc hoặc miền Nam, tuỳ chỉnh tốc độ đọc, hoặc thậm chí "
            "nhân bản giọng nói của chính bạn từ một đoạn ghi âm ngắn."
        )
        self.text_buffer.set_text(sample)
        self._show_toast("Đã nạp văn bản mẫu")

    def _on_clear_clicked(self, button):
        self.text_buffer.set_text("")
        self._show_toast("Đã xoá nội dung")

    def _on_paste_clicked(self, button):
        clipboard = Gdk.Display.get_default().get_clipboard()
        clipboard.read_text_async(None, self._on_clipboard_text_read)

    def _on_clipboard_text_read(self, clipboard, result):
        try:
            text = clipboard.read_text_finish(result)
            if text:
                self.text_buffer.set_text(text)
                self._show_toast("Đã dán văn bản từ bộ nhớ tạm")
        except Exception as e:
            print(f"[Main] Clipboard paste error: {e}")

    def _on_open_file_clicked(self, button):
        dialog = Gtk.FileDialog()
        dialog.set_title("Chọn tệp văn bản hoặc phụ đề")

        filter_text = Gtk.FileFilter()
        filter_text.set_name("Tệp văn bản & phụ đề (*.txt, *.srt)")
        filter_text.add_pattern("*.txt")
        filter_text.add_pattern("*.srt")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_text)
        dialog.set_filters(filters)

        dialog.open(self, None, self._on_file_open_finish)

    def _on_file_open_finish(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                path = file.get_path()
                content = Path(path).read_text(encoding="utf-8", errors="replace")
                if path.lower().endswith(".srt"):
                    content = self._parse_srt(content)
                self.text_buffer.set_text(content)
                self._show_toast(f"Đã mở tệp: {Path(path).name}")
        except Exception as e:
            print(f"[Main] File open error: {e}")

    def _parse_srt(self, srt_content: str) -> str:
        lines = []
        for line in srt_content.splitlines():
            line = line.strip()
            if not line:
                continue
            if re.match(r'^\d+$', line):
                continue
            if re.match(r'^\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,\.]\d{3}', line):
                continue
            lines.append(line)
        return ' '.join(lines)

    def _on_choose_reference_audio(self, button):
        dialog = Gtk.FileDialog()
        dialog.set_title("Chọn file âm thanh mẫu (3–10 giây)")

        filter_audio = Gtk.FileFilter()
        filter_audio.set_name("Tệp âm thanh (*.wav, *.mp3, *.ogg, *.flac)")
        filter_audio.add_pattern("*.wav")
        filter_audio.add_pattern("*.mp3")
        filter_audio.add_pattern("*.ogg")
        filter_audio.add_pattern("*.flac")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_audio)
        dialog.set_filters(filters)

        dialog.open(self, None, self._on_reference_audio_chosen)

    def _on_reference_audio_chosen(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                path = file.get_path()
                self.reference_audio_path = path
                self.row_clone_file.set_subtitle(Path(path).name)
                self.btn_play_ref.set_sensitive(True)
                self._show_toast(f"Đã chọn mẫu giọng: {Path(path).name}")
        except Exception as e:
            print(f"[Main] Choose reference audio error: {e}")

    def _on_play_reference_clicked(self, button):
        if self.reference_audio_path and os.path.exists(self.reference_audio_path):
            self.player.load(self.reference_audio_path)
            self.player.play()

    def _on_main_action_clicked(self, button):
        if self.is_generating:
            # Cancel request
            self.engine.cancel()
            self._update_action_button_state(is_running=False)
            self.gen_status_label.set_label("Đã huỷ tác vụ.")
            self.window_title.set_subtitle("Đã huỷ")
            self.is_generating = False
            return

        if not self.engine._is_ready:
            self._show_toast("Mô hình AI đang được khởi tạo, vui lòng chờ trong giây lát...")
            return

        start, end = self.text_buffer.get_bounds()
        text = self.text_buffer.get_text(start, end, True).strip()
        if not text:
            self._show_toast("Vui lòng nhập hoặc dán văn bản tiếng Việt để tạo giọng đọc!")
            self.text_view.grab_focus()
            return

        is_clone = self.btn_mode_clone.get_active()
        if is_clone and (not self.reference_audio_path or not os.path.exists(self.reference_audio_path)):
            self._show_toast("Vui lòng chọn file âm thanh mẫu để nhân bản giọng!")
            return

        # Start background generation
        self.is_generating = True
        self._update_action_button_state(is_running=True)
        self.player.stop()

        self.gen_progress_box.set_visible(True)
        self.gen_progress_bar.set_fraction(0.0)
        self.gen_status_label.set_label("Bắt đầu xử lý âm thanh...")
        self.window_title.set_subtitle("Đang tạo giọng đọc...")

        speed = self.slider_speed.get_value()
        speaker = self.selected_speaker_id
        ref_path = self.reference_audio_path

        threading.Thread(
            target=self._run_synthesis_thread,
            args=(text, is_clone, speaker, ref_path, speed),
            daemon=True
        ).start()

    def _run_synthesis_thread(self, text, is_clone, speaker, ref_path, speed):
        start_time = time.time()

        def on_progress(current, total, msg):
            frac = (current / total) if total > 0 else 0.0
            GLib.idle_add(self._update_generation_progress, frac, msg)

        try:
            if is_clone:
                result = self.engine.clone_voice(
                    text=text,
                    reference_audio_path=ref_path,
                    speed=speed,
                    on_progress=on_progress
                )
            else:
                result = self.engine.synthesize(
                    text=text,
                    speaker=speaker,
                    speed=speed,
                    on_progress=on_progress
                )

            duration_cost = time.time() - start_time
            GLib.idle_add(self._on_synthesis_finished, result, duration_cost)

        except Exception as e:
            GLib.idle_add(self._on_synthesis_error, str(e))

    def _update_generation_progress(self, fraction, message):
        self.gen_progress_bar.set_fraction(fraction)
        self.gen_status_label.set_label(message)
        self.window_title.set_subtitle(message)

    def _on_synthesis_finished(self, result, duration_cost):
        self.is_generating = False
        self._update_action_button_state(is_running=False)
        self.gen_progress_box.set_visible(False)

        if result is None:
            self.window_title.set_subtitle("Sẵn sàng")
            return

        audio_data, sample_rate = result
        self.last_audio_data = audio_data
        self.last_sample_rate = sample_rate

        # Save to temporary file for player
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, "v_tts_current_audio.wav")
        self.engine.save_audio(audio_data, sample_rate, temp_path)
        self.temp_audio_file = temp_path

        # Update player
        self.player.load(temp_path)
        audio_len_secs = len(audio_data) / sample_rate

        self.slider_playback.set_range(0.0, max(0.1, audio_len_secs))
        self.slider_playback.set_value(0.0)
        self.slider_playback.set_sensitive(True)

        self.lbl_time_current.set_label("00:00")
        self.lbl_time_total.set_label(format_time(audio_len_secs))

        self.btn_play_pause.set_sensitive(True)
        self.btn_stop.set_sensitive(True)
        self.btn_seek_back.set_sensitive(True)
        self.btn_seek_forward.set_sensitive(True)
        self.btn_save_audio.set_sensitive(True)
        self.btn_export_header.set_sensitive(True)

        # Auto-play generated audio
        self.player.play()
        self._start_playback_timer()

        self.window_title.set_subtitle(f"Đã tạo xong ({duration_cost:.1f}s • {format_time(audio_len_secs)})")
        self._show_toast(f"Tạo giọng đọc thành công trong {duration_cost:.1f} giây!")

    def _on_synthesis_error(self, err_msg):
        self.is_generating = False
        self._update_action_button_state(is_running=False)
        self.gen_progress_box.set_visible(False)
        self.window_title.set_subtitle("Lỗi tạo âm thanh")
        self._show_toast(f"Lỗi: {err_msg}")

    # Player controls
    def _on_play_pause_clicked(self, button):
        self.player.toggle()

    def _on_player_state_change(self, is_playing):
        GLib.idle_add(self._update_play_icon, is_playing)

    def _update_play_icon(self, is_playing):
        if is_playing:
            self.btn_play_pause.set_icon_name("media-playback-pause-symbolic")
            self._start_playback_timer()
        else:
            self.btn_play_pause.set_icon_name("media-playback-start-symbolic")

    def _on_player_eos(self):
        GLib.idle_add(self._reset_playback_ui)

    def _reset_playback_ui(self):
        self.btn_play_pause.set_icon_name("media-playback-start-symbolic")
        self.slider_playback.set_value(0.0)
        self.lbl_time_current.set_label("00:00")
        self._stop_playback_timer()

    def _start_playback_timer(self):
        if self.playback_timer_id is None:
            self.playback_timer_id = GLib.timeout_add(200, self._on_playback_tick)

    def _stop_playback_timer(self):
        if self.playback_timer_id is not None:
            GLib.source_remove(self.playback_timer_id)
            self.playback_timer_id = None

    def _on_playback_tick(self):
        if not self.player.is_playing():
            return True
        pos = self.player.get_position()
        dur = self.player.get_duration()

        self.slider_playback.set_value(pos)
        self.lbl_time_current.set_label(format_time(pos))
        if dur > 0:
            self.lbl_time_total.set_label(format_time(dur))
        return True

    def _on_seek_requested(self, scale, scroll_type, value):
        self.player.seek(value)
        self.lbl_time_current.set_label(format_time(value))
        return False

    def _seek_relative(self, delta):
        cur = self.player.get_position()
        dur = self.player.get_duration()
        if dur <= 0:
            return
        target = max(0.0, min(dur, cur + delta))
        self.player.seek(target)
        self.slider_playback.set_value(target)
        self.lbl_time_current.set_label(format_time(target))

    def _on_export_clicked(self, button):
        if self.last_audio_data is None:
            self._show_toast("Chưa có đoạn âm thanh nào được tạo!")
            return

        dialog = Gtk.FileDialog()
        dialog.set_title("Lưu file âm thanh")
        dialog.set_initial_name("giong_doc.wav")

        filter_wav = Gtk.FileFilter()
        filter_wav.set_name("Tệp âm thanh WAV (*.wav)")
        filter_wav.add_pattern("*.wav")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_wav)
        dialog.set_filters(filters)

        dialog.save(self, None, self._on_export_file_finish)

    def _on_export_file_finish(self, dialog, result):
        try:
            file = dialog.save_finish(result)
            if file:
                path = file.get_path()
                if not path.lower().endswith(".wav"):
                    path += ".wav"
                self.engine.save_audio(self.last_audio_data, self.last_sample_rate, path)
                self._show_toast(f"Đã lưu thành công: {Path(path).name}")
        except Exception as e:
            print(f"[Main] Export error: {e}")

    def _show_toast(self, message: str):
        toast = Adw.Toast.new(message)
        toast.set_timeout(3)
        self.toast_overlay.add_toast(toast)


class VanBanThanhGiongDocApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS
        )

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = MainWindow(application=self)
        win.present()

    def do_startup(self):
        Adw.Application.do_startup(self)
        
        # Setup application actions
        sample_action = Gio.SimpleAction.new("sample_text", None)
        sample_action.connect("activate", self._on_sample_action)
        self.add_action(sample_action)

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about_action)
        self.add_action(about_action)

    def _on_sample_action(self, action, param):
        win = self.props.active_window
        if win:
            win._load_sample_text()

    def _on_about_action(self, action, param):
        win = self.props.active_window
        dialog = Adw.AboutDialog()
        dialog.set_application_name("Văn bản thành giọng đọc")
        dialog.set_version("1.0.0")
        dialog.set_developer_name("Nguyễn Ngọc Hoan\nadfoxtheme")
        dialog.set_developers(["Nguyễn Ngọc Hoan", "adfoxtheme"])
        dialog.add_credit_section("Bộ máy AI V-TTS", ["Lê Trọng Hiếu (github.com/tronghieuit/v-tts)"])
        dialog.set_comments(
            "Ứng dụng chuyển đổi văn bản thành giọng đọc tiếng Việt siêu nhẹ, "
            "hỗ trợ 5 giọng chuẩn Bắc/Nam và tính năng nhân bản giọng nói AI."
        )
        dialog.set_website("https://github.com/tronghieuit/v-tts")
        dialog.set_issue_url("https://github.com/tronghieuit/v-tts/issues")
        dialog.set_license_type(Gtk.License.MIT_X11)
        dialog.set_application_icon(APP_ID)
        dialog.present(win)


def main():
    app = VanBanThanhGiongDocApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
