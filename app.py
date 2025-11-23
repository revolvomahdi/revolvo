# Automation/app.py
# Main application controller with advanced features and a custom fullscreen UI
# --- VERSION WITH 2K 60FPS OUTPUT & UI CLEANUP ---

import sys
import threading
import os
import time
import subprocess
import json
from datetime import datetime
from pathlib import Path
import traceback

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QProgressBar, QFrame,
    QMessageBox, QGroupBox, QScrollArea, QCheckBox, QStatusBar,
    QDialog, QLineEdit, QFormLayout, QGraphicsOpacityEffect, QMenuBar,
    QFileDialog, QTabWidget, QComboBox, QSpinBox, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QFont, QIcon, QAction, QCursor, QPainter, QColor
from PyQt6.QtCore import pyqtSignal, QThread, Qt, QPropertyAnimation, QEasingCurve, QPoint, QSize

import qtawesome as qta

from creator import core as creator_core
from uploader import youtube_uploader
from uploader import config as uploader_config
from settings.check import AuthCheckDialog

# --- Constants & Default Paths ---
SETTINGS_DIR = Path("settings")
SETTINGS_FILE = SETTINGS_DIR / "app_settings.json"
DEFAULT_CREATOR_DIR = Path("creator")
DEFAULT_LINKS_FILE = DEFAULT_CREATOR_DIR / "link.txt"
DEFAULT_USED_LINKS_FILE = DEFAULT_CREATOR_DIR / "used_link.txt"
DEFAULT_OUTPUT_BASE_DIR = DEFAULT_CREATOR_DIR / "output"

# --- THEME STYLESHEETS ---
THEMES = {
    "Nord Dark": """...""", # Önceki yanıttaki uzun stil kodları buraya gelecek
    "Dracula": """...""",
    "Classic Light": """...""",
    "Solarized Light": """..."""
}
# (Not: Okunabilirlik için tema kodlarını kısalttım, önceki yanıttaki tam kodları kullanın)
THEMES["Nord Dark"] = """
    QWidget, QDialog { background-color: #2E3440; color: #D8DEE9; font-family: 'Segoe UI', sans-serif; } CustomTitleBar { background-color: #3B4252; } #TitleLabel { color: #ECEFF4; padding-left: 10px; font-weight: bold; } QGroupBox { font-size: 14px; font-weight: bold; color: #88C0D0; border: 1px solid #4C566A; border-radius: 8px; margin-top: 10px; padding: 20px 15px 15px 15px; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 10px; background-color: #3B4252; border-radius: 4px; } QPushButton { background-color: #434C5E; color: #ECEFF4; border: 1px solid #4C566A; padding: 10px; border-radius: 5px; font-size: 13px; min-height: 20px; } QPushButton:hover { background-color: #4C566A; border: 1px solid #5E81AC; } QPushButton#StartButton { background-color: #5E81AC; } QPushButton#UploadButton { background-color: #A3BE8C; } QPushButton#StopButton { background-color: #BF616A; } QTextEdit, QLineEdit, QSpinBox, QComboBox { background-color: #3B4252; color: #D8DEE9; border: 1px solid #4C566A; border-radius: 5px; padding: 8px; } QProgressBar::chunk { background-color: #88C0D0; } QMenuBar, QMenu { background-color: #3B4252; color: #D8DEE9; } QMenu { border: 1px solid #4C566A; } QMenuBar::item:selected, QMenu::item:selected { background-color: #4C566A; } QTabWidget::pane { border: 1px solid #4C566A; } QTabBar::tab { background: #2E3440; padding: 8px; } QTabBar::tab:selected { background: #434C5E; } #Container { border: 1px solid #4C566A; border-radius: 8px; }
"""
THEMES["Dracula"] = """
    QWidget, QDialog { background-color: #282a36; color: #f8f8f2; font-family: 'Segoe UI', sans-serif; } CustomTitleBar { background-color: #21222c; } #TitleLabel { color: #bd93f9; padding-left: 10px; font-weight: bold; } QGroupBox { font-size: 14px; font-weight: bold; color: #bd93f9; border: 1px solid #44475a; border-radius: 8px; margin-top: 10px; padding: 20px 15px 15px 15px; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 10px; background-color: #44475a; border-radius: 4px; } QPushButton { background-color: #44475a; color: #f8f8f2; border: 1px solid #6272a4; padding: 10px; border-radius: 5px; font-size: 13px; min-height: 20px; } QPushButton:hover { background-color: #6272a4; } QPushButton#StartButton { background-color: #8be9fd; color: #282a36; } QPushButton#UploadButton { background-color: #50fa7b; color: #282a36; } QPushButton#StopButton { background-color: #ff5555; } QTextEdit, QLineEdit, QSpinBox, QComboBox { background-color: #21222c; color: #f8f8f2; border: 1px solid #44475a; border-radius: 5px; padding: 8px; } QProgressBar::chunk { background-color: #ff79c6; } QMenuBar, QMenu { background-color: #21222c; color: #f8f8f2; } QMenu { border: 1px solid #44475a; } QMenuBar::item:selected, QMenu::item:selected { background-color: #44475a; } QTabWidget::pane { border: 1px solid #44475a; } QTabBar::tab { background: #282a36; padding: 8px; } QTabBar::tab:selected { background: #44475a; } #Container { border: 1px solid #44475a; border-radius: 8px; }
"""
THEMES["Classic Light"] = """
    QWidget, QDialog { background-color: #f0f0f0; color: #000; font-family: 'Segoe UI', sans-serif; } CustomTitleBar { background-color: #dcdcdc; } #TitleLabel { color: #000; padding-left: 10px; font-weight: bold; } QGroupBox { font-size: 14px; font-weight: bold; color: #00539C; border: 1px solid #b0b0b0; border-radius: 8px; margin-top: 10px; padding: 20px 15px 15px 15px; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 10px; background-color: #e8e8e8; border-radius: 4px; } QPushButton { background-color: #e1e1e1; color: #000; border: 1px solid #adadad; padding: 10px; border-radius: 5px; font-size: 13px; min-height: 20px; } QPushButton:hover { background-color: #e9e9e9; border: 1px solid #0078d7; } QPushButton#StartButton { background-color: #0078d7; color: white; } QPushButton#UploadButton { background-color: #107c10; color: white; } QPushButton#StopButton { background-color: #d13438; color: white; } QTextEdit, QLineEdit, QSpinBox, QComboBox { background-color: #fff; color: #000; border: 1px solid #adadad; border-radius: 5px; padding: 8px; } QProgressBar::chunk { background-color: #0078d7; } QMenuBar, QMenu { background-color: #f0f0f0; color: #000; } QMenu { border: 1px solid #adadad; } QMenuBar::item:selected, QMenu::item:selected { background-color: #d0e4f8; } QTabWidget::pane { border: 1px solid #adadad; } QTabBar::tab { background: #f0f0f0; padding: 8px; } QTabBar::tab:selected { background: #e0e0e0; } #Container { border: 1px solid #adadad; border-radius: 8px; }
"""
THEMES["Solarized Light"] = """
    QWidget, QDialog { background-color: #fdf6e3; color: #657b83; font-family: 'Segoe UI', sans-serif; } CustomTitleBar { background-color: #eee8d5; } #TitleLabel { color: #073642; padding-left: 10px; font-weight: bold; } QGroupBox { font-size: 14px; font-weight: bold; color: #268bd2; border: 1px solid #93a1a1; border-radius: 8px; margin-top: 10px; padding: 20px 15px 15px 15px; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 10px; background-color: #eee8d5; border-radius: 4px; } QPushButton { background-color: #eee8d5; color: #586e75; border: 1px solid #93a1a1; padding: 10px; border-radius: 5px; font-size: 13px; min-height: 20px; } QPushButton:hover { background-color: #fdf6e3; border: 1px solid #268bd2; } QPushButton#StartButton { background-color: #268bd2; color: #fdf6e3; } QPushButton#UploadButton { background-color: #859900; color: #fdf6e3; } QPushButton#StopButton { background-color: #dc322f; color: #fdf6e3; } QTextEdit, QLineEdit, QSpinBox, QComboBox { background-color: #eee8d5; color: #586e75; border: 1px solid #93a1a1; border-radius: 5px; padding: 8px; } QProgressBar::chunk { background-color: #2aa198; } QMenuBar, QMenu { background-color: #eee8d5; color: #586e75; } QMenu { border: 1px solid #93a1a1; } QMenuBar::item:selected, QMenu::item:selected { background-color: #93a1a1; } QTabWidget::pane { border: 1px solid #93a1a1; } QTabBar::tab { background: #fdf6e3; padding: 8px; } QTabBar::tab:selected { background: #eee8d5; } #Container { border: 1px solid #93a1a1; border-radius: 8px; }
"""
THEMES["Red & Black"] = """
    QWidget, QDialog { background-color: #000000; color: #FF0000; font-family: 'Segoe UI', sans-serif; font-weight: bold; }
    CustomTitleBar { background-color: #1a0000; border-bottom: 2px solid #FF0000; }
    #TitleLabel { color: #FF0000; }
    QGroupBox { font-size: 14px; font-weight: bold; color: #FF0000; border: 2px solid #FF0000; border-radius: 8px; margin-top: 15px; padding: 20px 10px 10px 10px; }
    QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 0 10px; background-color: #000000; color: #FF0000; }
    QPushButton { background-color: #000000; color: #FF0000; border: 2px solid #FF0000; padding: 10px; border-radius: 5px; }
    QPushButton:hover { background-color: #FF0000; color: #000000; }
    QPushButton:disabled { border-color: #550000; color: #550000; }
    QTextEdit, QLineEdit, QSpinBox, QComboBox { background-color: #0a0000; color: #FF0000; border: 1px solid #FF0000; border-radius: 5px; padding: 5px; }
    QProgressBar { border: 2px solid #FF0000; text-align: center; color: #FF0000; }
    QProgressBar::chunk { background-color: #FF0000; }
    QMenuBar, QMenu { background-color: #000000; color: #FF0000; border: 1px solid #FF0000; }
    QMenuBar::item:selected, QMenu::item:selected { background-color: #FF0000; color: #000000; }
    QTabWidget::pane { border: 2px solid #FF0000; }
    QTabBar::tab { background: #000000; color: #FF0000; border: 1px solid #FF0000; padding: 8px; margin-right: 2px; }
    QTabBar::tab:selected { background: #FF0000; color: #000000; }
    #Container { border: 3px solid #FF0000; border-radius: 8px; }
    QScrollBar:vertical { background: #000000; width: 12px; }
    QScrollBar::handle:vertical { background: #FF0000; border-radius: 6px; }
"""

THEMES["Cyber Red"] = """
    /* Genel Zemin - Simsiyah */
    QWidget, QDialog { background-color: #050505; color: #D6D6D6; font-family: 'Segoe UI', sans-serif; }
    
    /* Başlık Çubuğu */
    CustomTitleBar { background-color: #000000; border-bottom: 2px solid #B71C1C; }
    #TitleLabel { color: #E0E0E0; font-weight: bold; padding-left: 10px; }
    
    /* Gruplama Kutuları */
    QGroupBox { font-size: 14px; font-weight: bold; color: #FF5252; border: 1px solid #8B0000; border-radius: 4px; margin-top: 15px; padding: 20px 15px 15px 15px; }
    QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; background-color: #050505; color: #FF5252; }
    
    /* Genel Butonlar */
    QPushButton { background-color: #0F0F0F; color: #D6D6D6; border: 1px solid #B71C1C; padding: 10px; border-radius: 4px; font-size: 13px; }
    QPushButton:hover { background-color: #B71C1C; color: #FFFFFF; border: 1px solid #FF5252; }
    QPushButton:pressed { background-color: #FF5252; color: #000000; }
    QPushButton:disabled { background-color: #0A0A0A; border-color: #333333; color: #444444; }
    
    /* --- ÖZEL START BUTONU (NEON EFEKTİ) --- */
    QPushButton#StartButton { 
        background-color: #1a0000; 
        border: 2px solid #D32F2F; 
        color: #FF5252; 
        font-weight: bold;
    }
    /* Mouse üzerine gelince (HOVER) parlasın */
    QPushButton#StartButton:hover { 
        background-color: #D32F2F; /* İçi Kırmızı Olsun */
        color: #FFFFFF;            /* Yazı Beyaz Olsun */
        border: 2px solid #FF8A80; /* Çerçeve Açık Kırmızı (Parlıyor gibi) */
    }
    
    /* Diğer Özel Butonlar */
    QPushButton#StopButton { border: 1px solid #5c0000; color: #ff6666; }
    QPushButton#StopButton:hover { background-color: #800000; color: white; }
    
    QPushButton#UploadButton { border: 1px solid #1B5E20; color: #81C784; }
    QPushButton#UploadButton:hover { background-color: #1B5E20; color: white; }

    /* Giriş Alanları */
    QTextEdit, QLineEdit, QSpinBox, QComboBox { background-color: #000000; color: #D6D6D6; border: 1px solid #333333; border-radius: 3px; padding: 8px; }
    QTextEdit:focus, QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #FF5252; }
    
    /* İlerleme Çubuğu */
    QProgressBar { border: 1px solid #333333; text-align: center; color: #FFFFFF; background-color: #000000; border-radius: 3px; }
    QProgressBar::chunk { background-color: #D32F2F; }
    
    /* Menü ve Tablar */
    QMenuBar, QMenu { background-color: #000000; color: #D6D6D6; border: none; }
    QMenuBar::item:selected, QMenu::item:selected { background-color: #B71C1C; color: #FFFFFF; }
    QMenu { border: 1px solid #8B0000; }
    
    QTabWidget::pane { border: 1px solid #8B0000; }
    QTabBar::tab { background: #0F0F0F; color: #888888; padding: 8px 20px; border: 1px solid #333333; margin-right: 2px; }
    QTabBar::tab:selected { background: #000000; color: #FF5252; border-top: 2px solid #FF5252; border-bottom: none; }
    
    #Container { border: 2px solid #8B0000; border-radius: 5px; }
    
    /* Checkbox */
    QCheckBox { color: #D6D6D6; spacing: 8px; }
    QCheckBox::indicator { width: 16px; height: 16px; background-color: #000000; border: 1px solid #8B0000; border-radius: 2px; }
    QCheckBox::indicator:checked { background-color: #FF5252; border: 1px solid #FF5252; }
    
    /* Scrollbar */
    QScrollBar:vertical { background: #050505; width: 8px; margin: 0px; }
    QScrollBar::handle:vertical { background: #550000; min-height: 20px; border-radius: 4px; }
    QScrollBar::handle:vertical:hover { background: #B71C1C; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
"""

THEMES["Midnight Rain"] = """
    /* Genel Zemin - Derin Gece Mavisi */
    QWidget, QDialog { background-color: #050A14; color: #CFD8DC; font-family: 'Segoe UI', sans-serif; }

    /* Başlık Çubuğu */
    CustomTitleBar { background-color: #020508; border-bottom: 1px solid #006064; }
    #TitleLabel { color: #B2EBF2; font-weight: bold; padding-left: 10px; text-transform: uppercase; letter-spacing: 1px; }

    /* Gruplama Kutuları - Yarı Şeffaf Mavi Dolgu */
    QGroupBox { 
        font-size: 14px; 
        font-weight: bold; 
        color: #00BCD4; /* Neon Camgöbeği */
        border: 1px solid #006064; 
        border-radius: 6px; 
        margin-top: 15px; 
        padding: 20px 15px 15px 15px; 
        background-color: #081020; /* Hafif açık lacivert */
    }
    QGroupBox::title { 
        subcontrol-origin: margin; 
        subcontrol-position: top left; 
        padding: 0 5px; 
        background-color: #050A14; 
        color: #80DEEA; 
    }

    /* Genel Butonlar - Mistik Hava */
    QPushButton { 
        background-color: #0B162A; 
        color: #CFD8DC; 
        border: 1px solid #1C3A50; 
        padding: 10px; 
        border-radius: 4px; 
        font-size: 13px; 
    }
    QPushButton:hover { 
        background-color: #006064; 
        color: #FFFFFF; 
        border: 1px solid #00BCD4; /* Parlayan Çiçek Rengi */
    }
    QPushButton:pressed { background-color: #00BCD4; color: #000000; }
    QPushButton:disabled { background-color: #05080C; border-color: #0F202D; color: #263238; }

    /* --- ÖZEL START BUTONU (Çiçek Gibi Parlasın) --- */
    QPushButton#StartButton { 
        background-color: #002529; /* Çok koyu turkuaz */
        border: 1px solid #00838F; 
        color: #00BCD4; 
        font-weight: bold;
    }
    /* Mouse üzerine gelince o çiçeklerin parlaklığı gibi olsun */
    QPushButton#StartButton:hover { 
        background-color: #006064; 
        color: #E0F7FA;            
        border: 1px solid #80DEEA; /* Parlak buz mavisi çerçeve */
    }

    /* Diğer Özel Butonlar */
    QPushButton#StopButton { border: 1px solid #37474F; color: #B0BEC5; }
    QPushButton#StopButton:hover { background-color: #263238; color: #EF5350; border-color: #EF5350; }

    QPushButton#UploadButton { border: 1px solid #1B5E20; color: #81C784; }
    QPushButton#UploadButton:hover { background-color: #1B5E20; color: white; }

    /* Giriş Alanları */
    QTextEdit, QLineEdit, QSpinBox, QComboBox { 
        background-color: #020406; 
        color: #E0F7FA; 
        border: 1px solid #1C3A50; 
        border-radius: 3px; 
        padding: 8px; 
    }
    QTextEdit:focus, QLineEdit:focus, QSpinBox:focus, QComboBox:focus { 
        border: 1px solid #00BCD4; /* Odaklanınca neon mavi */
    }

    /* İlerleme Çubuğu */
    QProgressBar { 
        border: 1px solid #1C3A50; 
        text-align: center; 
        color: #FFFFFF; 
        background-color: #020406; 
        border-radius: 3px; 
    }
    QProgressBar::chunk { 
        background-color: #0097A7; /* Koyu Camgöbeği */
        width: 10px;
        margin: 0.5px;
    }

    /* Menü ve Tablar */
    QMenuBar, QMenu { background-color: #050A14; color: #CFD8DC; border: none; }
    QMenuBar::item:selected, QMenu::item:selected { background-color: #006064; color: #FFFFFF; }
    QMenu { border: 1px solid #1C3A50; }

    QTabWidget::pane { border: 1px solid #1C3A50; }
    QTabBar::tab { background: #081020; color: #546E7A; padding: 8px 20px; border: 1px solid #1C3A50; margin-right: 2px; }
    QTabBar::tab:selected { 
        background: #050A14; 
        color: #00BCD4; 
        border-top: 2px solid #00BCD4; 
        border-bottom: none; 
    }

    #Container { border: 1px solid #1C3A50; border-radius: 5px; }

    /* Checkbox */
    QCheckBox { color: #B2EBF2; spacing: 8px; }
    QCheckBox::indicator { width: 16px; height: 16px; background-color: #020406; border: 1px solid #006064; border-radius: 2px; }
    QCheckBox::indicator:checked { background-color: #00BCD4; border: 1px solid #00BCD4; }

    /* Scrollbar - İnce ve Zarif */
    QScrollBar:vertical { background: #050A14; width: 8px; margin: 0px; }
    QScrollBar::handle:vertical { background: #263238; min-height: 20px; border-radius: 4px; }
    QScrollBar::handle:vertical:hover { background: #00838F; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
"""

# --- Worker Threads ---
class CreatorWorker(QThread):
    finished = pyqtSignal(bool, str, str, list)
    log_message = pyqtSignal(str)
    progress = pyqtSignal(int)
    remaining_links_count = pyqtSignal(int)
    processed_stats = pyqtSignal(int, int)
    video_finished = pyqtSignal(list)  # <-- YENİ EKLENEN SİNYAL (Köprü)

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.stop_event = threading.Event()
        self.settings = settings

    def run(self):
        try:
            worker_signals = creator_core.WorkerSignals()
            # Sinyalleri Bağla
            worker_signals.log_message.connect(self.log_message)
            worker_signals.progress.connect(self.progress)
            worker_signals.remaining_links_count.connect(self.remaining_links_count)
            worker_signals.processed_stats.connect(self.processed_stats)
            
            # --- YENİ SİNYAL BAĞLANTISI ---
            # Core'dan gelen video bitti sinyalini, Arayüze ilet
            worker_signals.video_finished.connect(self.video_finished) 
            # ------------------------------

            # Ayarları Al
            enable_overlay = self.settings.get('enable_overlay', True)
            hardware_accel = self.settings.get('hardware_accel', "CPU")
            
            # Limiti Ayarla
            max_limit = 0
            if self.settings.get('limit_enabled', False):
                max_limit = self.settings.get('limit_count', 10)

            # İşlemi Başlat
            success, msg, v_id, meta = creator_core.process_link(
                Path(self.settings.get('links_file')), 
                Path(self.settings.get('used_links_file')), 
                Path(self.settings.get('output_dir')),
                self.settings.get('openai_api_key'), 
                self.settings.get('openai_model'), 
                self.settings.get('yt_dlp_quality'),
                self.settings.get('ffmpeg_preset'),
                worker_signals, 
                self.stop_event,
                enable_overlay=enable_overlay,
                hardware_accel=hardware_accel,
                max_limit=max_limit
            )
            self.finished.emit(success, msg, v_id, meta)
            
        except Exception as e:
            error_msg = f"Creator worker error: {e}\n{traceback.format_exc()}"
            self.log_message.emit(error_msg)
            self.finished.emit(False, error_msg, None, [])

    def stop(self): 
        self.stop_event.set()

        
class UploaderWorker(QThread):
    finished = pyqtSignal(bool, str)
    log_message = pyqtSignal(str)
    
    # privacy_status parametresi eklendi
    def __init__(self, metadata_list, privacy_status="private", parent=None):
        super().__init__(parent)
        self.metadata_list = metadata_list
        self.privacy_status = privacy_status 

    def run(self):
        try:
            self.log_message.emit(f"🚀 Starting YouTube upload process ({self.privacy_status})...")
            # privacy_status iletiliyor
            youtube_uploader.upload_videos(self.metadata_list, uploader_config.CHANNEL_CONFIGS, self.log_message.emit, self.privacy_status)
            self.finished.emit(True, "✅ YouTube upload process completed successfully.")
        except Exception as e:
            error_msg = f"Uploader worker error: {e}\n{traceback.format_exc()}"
            self.log_message.emit(error_msg)
            self.finished.emit(False, error_msg)

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Login"); self.setModal(True); self.setFixedSize(350, 180)
        layout = QVBoxLayout(self); form_layout = QFormLayout()
        self.username_input = QLineEdit(self)
        self.password_input = QLineEdit(self); self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("Username:", self.username_input)
        form_layout.addRow("Password:", self.password_input)
        self.login_button = QPushButton("Login", self)
        self.login_button.clicked.connect(self.check_credentials)
        self.password_input.returnPressed.connect(self.check_credentials)
        layout.addLayout(form_layout); layout.addStretch(); layout.addWidget(self.login_button)
    def check_credentials(self):
        if self.username_input.text() == "1" and self.password_input.text() == "1": self.accept()
        else: QMessageBox.warning(self, "Login Failed", "Invalid username or password.")


class SettingsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings.copy()
        self.setWindowTitle("Settings"); self.setMinimumSize(600, 400)
        main_layout = QVBoxLayout(self); tab_widget = QTabWidget(self)
        tab_widget.addTab(self.create_general_tab(), "General")
        tab_widget.addTab(self.create_paths_tab(), "Paths")
        tab_widget.addTab(self.create_processing_tab(), "Processing")
        button_layout = QHBoxLayout(); save_button = QPushButton("Save"); save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel"); cancel_button.clicked.connect(self.reject)
        button_layout.addStretch(); button_layout.addWidget(save_button); button_layout.addWidget(cancel_button)
        main_layout.addWidget(tab_widget); main_layout.addLayout(button_layout)

    def create_general_tab(self):
        widget = QWidget(); layout = QFormLayout(widget)
        self.api_key_input = QLineEdit(self.settings.get("openai_api_key", "")); self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.model_combo = QComboBox(); self.model_combo.addItems(["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"])
        self.model_combo.setCurrentText(self.settings.get("openai_model", "gpt-3.5-turbo"))
        layout.addRow("OpenAI API Key:", self.api_key_input)
        layout.addRow("OpenAI Model:", self.model_combo)
        return widget
        
    def create_paths_tab(self):
        widget = QWidget(); layout = QFormLayout(widget)
        self.links_file_input = self.create_path_selector("links_file", "Links File (link.txt):", True)
        self.used_links_file_input = self.create_path_selector("used_links_file", "Used Links File (used_link.txt):", True)
        self.output_dir_input = self.create_path_selector("output_dir", "Output Directory:", False)
        layout.addRow(self.links_file_input[0], self.links_file_input[1])
        layout.addRow(self.used_links_file_input[0], self.used_links_file_input[1])
        layout.addRow(self.output_dir_input[0], self.output_dir_input[1])
        return widget

    def create_path_selector(self, key, label, is_file):
        container = QWidget(); layout = QHBoxLayout(container); layout.setContentsMargins(0,0,0,0)
        line_edit = QLineEdit(str(self.settings.get(key, ""))); button = QPushButton("Browse..."); button.setFixedWidth(100)
        layout.addWidget(line_edit); layout.addWidget(button)
        if is_file: button.clicked.connect(lambda: self.select_file(line_edit))
        else: button.clicked.connect(lambda: self.select_folder(line_edit))
        setattr(self, f"{key}_edit", line_edit); return QLabel(label), container
        
    def select_file(self, line_edit):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", os.path.dirname(line_edit.text()), "Text Files (*.txt)")
        if path: line_edit.setText(path)
    def select_folder(self, line_edit):
        path = QFileDialog.getExistingDirectory(self, "Select Directory", line_edit.text())
        if path: line_edit.setText(path)

    def create_processing_tab(self):
        widget = QWidget(); layout = QFormLayout(widget)
        self.quality_combo = QComboBox(); self.quality_combo.addItems(["4K (2160p)", "2K (1440p)", "1080p", "720p"])
        self.quality_combo.setCurrentText(self.settings.get("yt_dlp_quality", "1080p"))
        
        self.preset_combo = QComboBox(); self.preset_combo.addItems(["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"])
        self.preset_combo.setCurrentText(self.settings.get("ffmpeg_preset", "fast"))

        # --- YENİ GPU AYARI ---
        self.hardware_combo = QComboBox()
        self.hardware_combo.addItems(["CPU", "NVIDIA (NVENC)", "AMD (AMF)"])
        self.hardware_combo.setCurrentText(self.settings.get("hardware_accel", "CPU"))
        # ----------------------

        layout.addRow("Video Download Quality:", self.quality_combo)
        layout.addRow("Processing Hardware:", self.hardware_combo) # Eklendi
        layout.addRow("FFmpeg Preset (Speed vs Size):", self.preset_combo)
        
        info_label = QLabel("Output is fixed to 2K (1440x2560) @ 60fps.")
        layout.addRow(info_label)
        return widget

    def get_settings(self):
        self.settings["openai_api_key"] = self.api_key_input.text()
        self.settings["openai_model"] = self.model_combo.currentText()
        self.settings["links_file"] = self.links_file_edit.text()
        self.settings["used_links_file"] = self.used_links_file_edit.text()
        self.settings["output_dir"] = self.output_dir_edit.text()
        self.settings["yt_dlp_quality"] = self.quality_combo.currentText()
        self.settings["ffmpeg_preset"] = self.preset_combo.currentText()
        self.settings["hardware_accel"] = self.hardware_combo.currentText()
        # CRF AYARI KALDIRILDI
        # self.settings["ffmpeg_crf"] = self.crf_spinbox.value() 
        return self.settings

# --- Custom Title Bar (Unchanged) ---
class CustomTitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent; self.setFixedHeight(40)
        layout = QHBoxLayout(self); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
        title_icon = QLabel(); title_icon.setPixmap(qta.icon('fa5s.robot', color='#88C0D0').pixmap(22, 22))
        title_label = QLabel("Revolvo YouTube Automation"); title_label.setObjectName("TitleLabel")
        layout.addWidget(title_icon, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch()
        btn_size = QSize(40, 40); icon_color = '#D8DEE9'
        self.minimize_button = self.create_button(qta.icon('fa5s.window-minimize', color=icon_color), btn_size, parent.showMinimized)
        self.maximize_button = self.create_button(qta.icon('fa5s.window-maximize', color=icon_color), btn_size, parent.toggle_fullscreen)
        self.close_button = self.create_button(qta.icon('fa5s.times', color=icon_color), btn_size, parent.close)
        self.close_button.setStyleSheet("QPushButton:hover { background-color: #BF616A; }")
        layout.addWidget(self.minimize_button); layout.addWidget(self.maximize_button); layout.addWidget(self.close_button)
    def create_button(self, icon, size, slot):
        button = QPushButton(); button.setIcon(icon); button.setFixedSize(size); button.clicked.connect(slot)
        button.setStyleSheet("QPushButton { border: none; background-color: transparent; } QPushButton:hover { background-color: #4C566A; }")
        return button
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton: self.parent.start_drag_pos = event.globalPosition().toPoint()
    def mouseMoveEvent(self, event):
        if hasattr(self.parent, 'start_drag_pos') and self.parent.start_drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.parent.move(self.parent.pos() + event.globalPosition().toPoint() - self.parent.start_drag_pos)
            self.parent.start_drag_pos = event.globalPosition().toPoint()

# --- Main Application Window ---
class AutomationApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # Pencere ayarları (Çerçevesiz, Şeffaf)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Ayarları yükle
        self.settings = self.load_settings()
        
        # Değişkenleri başlat
        self.last_processed_metadata = []
        self.creator_worker = None
        self.uploader_worker = None
        self.active_uploaders = [] # Aktif yüklemeleri tutacak liste
        
        self.normal_geometry = self.geometry()
        self.start_drag_pos = None
        
        # Klasörleri ve Arayüzü kur
        self.setup_directories()
        self.init_ui()  # <-- Checkboxlar burada oluşturuluyor
        
        # Temayı uygula
        self.apply_theme(self.settings.get("theme", "Cyber Red"))
        
        # Link sayısını güncelle
        self.update_remaining_links_label()
        
        # Açılış efekti için opaklık ayarı
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

    def init_ui(self):
        container_widget = QWidget(self); container_widget.setObjectName("Container"); self.setCentralWidget(container_widget)
        container_layout = QVBoxLayout(container_widget); container_layout.setContentsMargins(1, 1, 1, 1); container_layout.setSpacing(0)
        self.title_bar = CustomTitleBar(self); container_layout.addWidget(self.title_bar)
        self.create_menu_bar()
        main_content_widget = QWidget()
        main_layout = QHBoxLayout(main_content_widget); main_layout.setContentsMargins(15, 15, 15, 15); main_layout.setSpacing(15)
        container_layout.addWidget(main_content_widget, 1)
        main_layout.addWidget(self.create_left_panel(), 1)
        main_layout.addWidget(self.create_right_panel(), 3)
        self.status_bar = QStatusBar(); self.setStatusBar(self.status_bar); self.status_bar.showMessage("Ready")

    def create_menu_bar(self):
        menu_bar = QMenuBar(self)
        
        # === FILE MENÜSÜ (Mevcuttu, doğru) ===
        file_menu = menu_bar.addMenu("File")
        settings_action = QAction(qta.icon('fa5s.cog'), "Settings", self)
        settings_action.triggered.connect(self.open_settings)
        exit_action = QAction(qta.icon('fa5s.sign-out-alt'), "Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(settings_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        # === YETKİLENDİRME MENÜSÜ (Yeni ekledin, doğru) ===
        auth_menu = menu_bar.addMenu("Yetkilendirme")
        manage_auth_action = QAction(qta.icon('fa5s.key', color='#EBCB8B'), "Kanal Yetkilerini Kontrol Et", self)
        manage_auth_action.triggered.connect(self.open_auth_checker)
        auth_menu.addAction(manage_auth_action)

        # === VIEW (GÖRÜNÜM) MENÜSÜ (EKSİK OLAN BÖLÜM BU) ===
        view_menu = menu_bar.addMenu("View")
        theme_menu = view_menu.addMenu("Theme")
        
        # self.theme_actions burada oluşturuluyor. Hatanın kaynağı bu bloğun olmaması.
        self.theme_actions = {}
        for theme_name in THEMES.keys():
            action = QAction(theme_name, self, checkable=True)
            # lambda'daki checked ve name=theme_name yapısı önemli
            action.triggered.connect(lambda checked, name=theme_name: self.apply_theme(name))
            theme_menu.addAction(action)
            self.theme_actions[theme_name] = action

        # === HELP (YARDIM) MENÜSÜ (Bu da orijinal kodda vardı) ===
        help_menu = menu_bar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        # Menü barını pencereye ekle
        self.setMenuBar(menu_bar)

    # ... (create_left_panel, create_right_panel, start_processing vb. diğer fonksiyonlar değişmedi) ...
    def create_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # --- Diller Grubu ---
        lang_group = QGroupBox("Languages")
        lang_layout = QVBoxLayout()
        self.language_checkboxes = {}
        
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        for key, name in creator_core.SUPPORTED_LANGUAGES.items():
            cb = QCheckBox(name)
            cb.setChecked(key in self.settings.get("selected_languages", []))
            self.language_checkboxes[key] = cb
            scroll_layout.addWidget(cb)
            
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        lang_layout.addWidget(scroll_area)
        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)

        # --- Video Seçenekleri & Otomasyon Grubu ---
        opts_group = QGroupBox("Video Options & Automation")
        opts_layout = QVBoxLayout(opts_group)

        # 1. Yazı Ekleme (Kayıtlı ayarı yükle)
        self.text_overlay_cb = QCheckBox("Add Text Overlay")
        # Varsayılan True, ama ayar varsa onu kullan
        self.text_overlay_cb.setChecked(self.settings.get('enable_overlay', True)) 
        self.text_overlay_cb.setToolTip("If unchecked, video will be processed to 2K/60FPS without adding text.")

        # 2. Otomatik Yükleme (Kayıtlı ayarı yükle)
        self.auto_upload_cb = QCheckBox("Auto Upload After Gen.")
        # Varsayılan False
        self.auto_upload_cb.setChecked(self.settings.get('auto_upload', False)) 
        self.auto_upload_cb.setToolTip("If checked, video will be uploaded immediately after creation.")
        
        # 3. Gizlilik (Kayıtlı ayarı yükle)
        self.privacy_label = QLabel("Privacy Status:")
        self.privacy_combo = QComboBox()
        self.privacy_combo.addItems(["private", "public", "unlisted"])
        # Kayıtlı ayarı seç, yoksa 'private'
        self.privacy_combo.setCurrentText(self.settings.get('privacy_status', 'private'))

        # 4. Limit Ayarları (Kayıtlı ayarları yükle)
        limit_layout = QHBoxLayout()
        self.limit_cb = QCheckBox("Limit Quantity")
        self.limit_cb.setToolTip("Enable to stop after X videos.")
        # Kayıtlı ayar
        limit_is_checked = self.settings.get('limit_enabled', False)
        self.limit_cb.setChecked(limit_is_checked)
        
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(1, 9999)
        self.limit_spin.setValue(self.settings.get('limit_count', 10))
        self.limit_spin.setEnabled(limit_is_checked) # Checkbox durumuna göre aktif/pasif
        
        self.limit_cb.toggled.connect(self.limit_spin.setEnabled)
        
        limit_layout.addWidget(self.limit_cb)
        limit_layout.addWidget(self.limit_spin)

        # Layout'a Ekleme
        opts_layout.addWidget(self.text_overlay_cb)
        opts_layout.addWidget(self.auto_upload_cb)
        opts_layout.addWidget(self.privacy_label)
        opts_layout.addWidget(self.privacy_combo)
        opts_layout.addLayout(limit_layout)
        
        opts_group.setLayout(opts_layout)
        layout.addWidget(opts_group)

        # --- Diğer Buton Grupları ---
        def clean_name(text):
            return text.lower().replace(' ', '_').replace('.', '_')

        for group_title, widgets in [
            ("Link Management", [("Add Link from Clipboard", 'fa5.clipboard', self.add_link_from_clipboard)]),
            ("File Operations", [
                ("Open Output Folder", 'fa5s.folder-open', lambda: self.open_path(self.settings.get("output_dir"))),
                ("Edit links.txt", 'fa5s.edit', lambda: self.open_path(self.settings.get("links_file"))),
                ("Edit used_link.txt", 'fa5s.file-signature', lambda: self.open_path(self.settings.get("used_links_file")))
            ]),
            ("Cleanup", [("Clear Used Links Log", 'fa5s.history', self.clear_used_links), ("Clear Generated Videos", 'fa5s.trash-alt', self.clear_output)])
        ]:
            group = QGroupBox(group_title)
            group_layout = QVBoxLayout(group)
            for text, icon, slot in widgets:
                btn = QPushButton(text)
                btn.setIcon(qta.icon(icon))
                btn.clicked.connect(slot)
                setattr(self, f"{clean_name(text)}_button", btn)
                group_layout.addWidget(btn)
            
            if group_title == "Link Management":
                self.remaining_links_label = QLabel()
                group_layout.addWidget(self.remaining_links_label)
            
            layout.addWidget(group)
            
        layout.addStretch()
        return panel

    def create_right_panel(self):
        panel = QWidget(); layout = QVBoxLayout(panel); layout.setContentsMargins(0,0,0,0); layout.setSpacing(15)
        controls_group = QGroupBox("Main Controls"); controls_layout = QHBoxLayout()
        self.start_button = QPushButton("Start"); self.start_button.setObjectName("StartButton"); self.start_button.clicked.connect(self.start_processing)
        self.stop_button = QPushButton("Stop"); self.stop_button.setObjectName("StopButton"); self.stop_button.clicked.connect(self.stop_processing); self.stop_button.setEnabled(False)
        self.upload_button = QPushButton("Upload"); self.upload_button.setObjectName("UploadButton"); self.upload_button.clicked.connect(self.start_uploading); self.upload_button.setEnabled(False)
        controls_layout.addWidget(self.start_button, 1); controls_layout.addWidget(self.stop_button, 1); controls_layout.addWidget(self.upload_button, 1)
        controls_group.setLayout(controls_layout); layout.addWidget(controls_group)
        logs_group = QGroupBox("Status & Logs"); logs_layout = QVBoxLayout()
        stats_layout = QHBoxLayout(); self.processed_videos_label = QLabel("Processed: 0"); self.total_time_label = QLabel("Total Time: 00:00:00")
        stats_layout.addWidget(self.processed_videos_label); stats_layout.addStretch(); stats_layout.addWidget(self.total_time_label)
        self.progress_bar = QProgressBar(); self.progress_bar.setFormat("%p%")
        self.log_output = QTextEdit(); self.log_output.setReadOnly(True)
        logs_layout.addLayout(stats_layout); logs_layout.addWidget(self.progress_bar); logs_layout.addWidget(QLabel("Logs:")); logs_layout.addWidget(self.log_output)
        logs_group.setLayout(logs_layout); layout.addWidget(logs_group, 1); return panel

    def start_processing(self):
        if self.creator_worker and self.creator_worker.isRunning(): return
        selected_languages = [key for key, cb in self.language_checkboxes.items() if cb.isChecked()]
        if not selected_languages: QMessageBox.warning(self, "Warning", "Please select at least one language."); return
        if not self.settings.get("openai_api_key"): QMessageBox.critical(self, "API Key Missing", "Please set OpenAI API key in File -> Settings."); return
        self.settings['enable_overlay'] = self.text_overlay_cb.isChecked()
        self.settings['limit_enabled'] = self.limit_cb.isChecked()
        self.settings['limit_count'] = self.limit_spin.value()
        creator_core.ENABLED_LANGUAGES = selected_languages; self.set_controls_enabled(False)
        self.log(f"▶️ Starting video creation..."); self.status_bar.showMessage("Processing...")
        self.settings['enable_overlay'] = self.text_overlay_cb.isChecked()
        self.progress_bar.setValue(0); self.upload_button.setEnabled(False); self.last_processed_metadata = []
        spinner_icon = qta.icon('fa5s.spinner', color='white', animation=qta.Spin(self.start_button))
        self.start_button.setIcon(spinner_icon)
        self.creator_worker = CreatorWorker(self.settings); self.creator_worker.log_message.connect(self.log)
        self.creator_worker.progress.connect(self.progress_bar.setValue); self.creator_worker.finished.connect(self.on_creation_finished)
        self.creator_worker.remaining_links_count.connect(self.update_remaining_links_label)
        self.creator_worker.processed_stats.connect(self.update_processed_stats)

        
        self.creator_worker.video_finished.connect(self.on_single_video_finished)
        
        self.creator_worker.start()

    def on_creation_finished(self, success, message, video_id, metadata_list):
        """
        Üretim bittiğinde çağrılır. 
        Eğer arkada çalışan otomatik yüklemeler varsa 'Bitti' mesajı vermez, onları bekler.
        """
        self.creator_worker = None # Üreticinin işi bitti, boşa çıkar
        
        if success:
            self.log("✅ Video creation phase finished.")
            if metadata_list:
                self.last_processed_metadata = metadata_list
        else:
            self.log(f"❌ Creation stopped/error: {message}")

        # --- BEKÇİ KONTROLÜ ---
        if self.active_uploaders:
            count = len(self.active_uploaders)
            self.log(f"⏳ Creation finished, but waiting for {count} background uploads to complete...")
            self.status_bar.showMessage(f"Finishing {count} uploads...")
            # Kontrolleri henüz açmıyoruz!
        else:
            # Hiç yükleme yoksa gerçekten bitmiştir.
            self.finalize_all_processes(success, message)

    def on_single_video_finished(self, metadata_list):
        """Bir video bittiğinde tetiklenir. Eğer Auto Upload açıksa hemen yükler."""
        
        # Son üretilen metadatayı kaydet (Manuel yükleme için)
        self.last_processed_metadata = metadata_list
        self.upload_button.setEnabled(True)

        # Eğer Otomatik Yükleme Kutusu İŞARETLİYSE:
        if self.auto_upload_cb.isChecked():
            privacy = self.privacy_combo.currentText()
            self.log(f"🔄 Auto-Upload triggered for {len(metadata_list)} videos ({privacy})...")
            
            # Yeni bir worker başlat (Mevcut worker'ı ezmemek için listeye atıyoruz)
            uploader = UploaderWorker(metadata_list, privacy_status=privacy)
            uploader.log_message.connect(self.log)
            
            # İş bitince listeyi temizlemek için temizlik fonksiyonu
            uploader.finished.connect(lambda: self.cleanup_uploader(uploader))
            
            self.active_uploaders.append(uploader)
            uploader.start()

    def cleanup_uploader(self, worker):
        """Bir yükleme worker'ı işini bitirdiğinde çalışır."""
        if worker in self.active_uploaders:
            self.active_uploaders.remove(worker)
        
        remaining = len(self.active_uploaders)
        if remaining > 0:
            self.log(f"ℹ️ One upload finished. {remaining} remaining...")
            self.status_bar.showMessage(f"Uploads remaining: {remaining}")
        else:
            # Yüklemeler bitti. Peki üretim (creator) de bitti mi?
            if self.creator_worker is None: # Evet, o da bitmiş (None olmuş)
                self.log("✅ All uploads finished.")
                self.finalize_all_processes(True, "All tasks completed.")

    def finalize_all_processes(self, success, message):
        """Hem üretim hem yükleme tamamen bittiğinde çağrılır."""
        self.set_controls_enabled(True)
        self.progress_bar.setValue(100 if success else 0)
        self.status_bar.showMessage("All Tasks Completed", 5000)
        
        # İkonu eski haline getir
        is_dark_theme = "Dark" in self.settings.get('theme', 'Nord Dark') or "Red" in self.settings.get('theme', '')
        icon_color = '#D6D6D6' if is_dark_theme else 'black'
        self.start_button.setIcon(qta.icon('fa5s.play', color=icon_color))

        if success:
            QMessageBox.information(self, "All Tasks Finished", "✅ Batch processing and uploads completed successfully!")
        else:
            # Sadece bir hata mesajı varsa göster, yoksa 'Completed' yeterli
            if "stopped" not in message.lower():
                QMessageBox.warning(self, "Finished with Warnings", message)
    def stop_processing(self):
        if self.creator_worker and self.creator_worker.isRunning():
            self.log("🛑 Stopping..."); self.status_bar.showMessage("Stopping...")
            self.creator_worker.stop(); self.stop_button.setEnabled(False)
    
    def start_uploading(self):
        if not self.last_processed_metadata: return
        
        # Gizlilik ayarını kutudan al
        privacy = self.privacy_combo.currentText()
        
        self.set_controls_enabled(False); self.upload_button.setEnabled(False)
        self.log(f"🚀 Starting upload ({privacy})..."); self.status_bar.showMessage("Uploading...")
        
        # Privacy parametresini geçir
        self.uploader_worker = UploaderWorker(self.last_processed_metadata, privacy_status=privacy)
        self.uploader_worker.log_message.connect(self.log)
        self.uploader_worker.finished.connect(self.on_upload_finished); self.uploader_worker.start()

    def on_upload_finished(self, success, message):
        self.log(message); self.set_controls_enabled(True)
        self.status_bar.showMessage("Upload Complete" if success else "Upload Error", 5000)
        if success:
            QMessageBox.information(self, "Upload Complete", message); self.upload_button.setEnabled(False); self.last_processed_metadata = []
        else: QMessageBox.critical(self, "Upload Error", message)
        self.uploader_worker = None
    
    def set_controls_enabled(self, enabled):
        self.start_button.setEnabled(enabled)
        self.stop_button.setEnabled(not enabled)
        
        # Tema rengine göre ikon rengi belirleme
        current_theme = self.settings.get('theme', 'Nord Dark')
        is_dark_theme = "Dark" in current_theme or "Dracula" in current_theme or "Red" in current_theme or "Black" in current_theme
        icon_color = '#D6D6D6' if is_dark_theme else 'black' # Cyber Red için uygun renk
        
        self.start_button.setIcon(qta.icon('fa5s.play', color=icon_color))
        self.stop_button.setIcon(qta.icon('fa5s.stop', color=icon_color))
        self.upload_button.setIcon(qta.icon('fa5s.upload', color=icon_color))
        
        # Upload butonu sadece işlenecek veri varsa aktif olur
        self.upload_button.setEnabled(enabled and bool(self.last_processed_metadata))
        
        self.menuBar().setEnabled(enabled)
        
        # Dil kutucuklarını kilitle/aç
        for cb in self.language_checkboxes.values(): 
            cb.setEnabled(enabled)
        
        # Video Ayarları kutucuklarını kilitle/aç
        self.text_overlay_cb.setEnabled(enabled)
        self.auto_upload_cb.setEnabled(enabled)
        self.privacy_combo.setEnabled(enabled)
        self.limit_cb.setEnabled(enabled)
        self.limit_spin.setEnabled(enabled and self.limit_cb.isChecked())

        # --- HATAYI ÇÖZEN KISIM ---
        # Nokta (.) yerine alt çizgi (_) kullanıyoruz çünkü butonlar öyle kaydedildi.
        btn_names = [
            "add_link_from_clipboard", 
            "open_output_folder", 
            "edit_links_txt",          # DÜZELDİ: edit_links.txt -> edit_links_txt
            "edit_used_link_txt",      # YENİ: edit_used_link.txt -> edit_used_link_txt
            "clear_used_links_log", 
            "clear_generated_videos"
        ]
        
        for btn_name in btn_names:
            # Güvenlik kontrolü: Eğer buton o an yoksa programı çökertme, pas geç
            if hasattr(self, f"{btn_name}_button"):
                getattr(self, f"{btn_name}_button").setEnabled(enabled)

    def log(self, msg): self.log_output.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"); QApplication.processEvents()
    
    def update_remaining_links_label(self, count=None):
        try:
            if count is None: count = creator_core.get_remaining_links_count(self.settings.get("links_file"), self.settings.get("used_links_file"))
            self.remaining_links_label.setText(f"Remaining Links: <b>{count}</b>")
        except Exception as e: self.log(f"Could not count links: {e}")

    def update_processed_stats(self, c, s): self.processed_videos_label.setText(f"Processed: <b>{c}</b>"); h, r = divmod(s, 3600); m, s = divmod(r, 60); self.total_time_label.setText(f"Time: <b>{h:02d}:{m:02d}:{s:02d}</b>")
    
    def setup_directories(self):
        try:
            SETTINGS_DIR.mkdir(exist_ok=True)
            for key in ["links_file", "used_links_file", "output_dir"]:
                p = Path(self.settings.get(key)); p.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e: QMessageBox.critical(self, "Directory Error", f"Could not create directories: {e}"); sys.exit(1)
        
    def load_settings(self):
        defaults = {
            "theme": "Nord Dark", "selected_languages": list(creator_core.SUPPORTED_LANGUAGES.keys()),
            "openai_api_key": "", "openai_model": "gpt-3.5-turbo",
            "links_file": str(DEFAULT_LINKS_FILE), "used_links_file": str(DEFAULT_USED_LINKS_FILE), "output_dir": str(DEFAULT_OUTPUT_BASE_DIR),
            "yt_dlp_quality": "1080p", "ffmpeg_preset": "fast"
            # ffmpeg_crf kaldırıldı
        }
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, 'r') as f: defaults.update(json.load(f))
            except (json.JSONDecodeError, IOError) as e: print(f"Could not load settings: {e}")
        return defaults

    def save_settings(self):
        # Mevcut tema
        self.settings["theme"] = next((name for name, action in self.theme_actions.items() if action.isChecked()), "Cyber Red")
        
        # Seçili diller
        self.settings["selected_languages"] = [key for key, cb in self.language_checkboxes.items() if cb.isChecked()]
        
        # Pencere konumu (Tam ekranda değilse)
        if not self.isFullScreen():
            self.settings["window_geometry"] = self.geometry().getRect()
            
        # --- YENİ: VİDEO & OTOMASYON AYARLARINI KAYDET ---
        # Bu satırlar sayesinde bir sonraki açılışta hatırlayacak
        self.settings["enable_overlay"] = self.text_overlay_cb.isChecked()
        self.settings["auto_upload"] = self.auto_upload_cb.isChecked()
        self.settings["privacy_status"] = self.privacy_combo.currentText()
        self.settings["limit_enabled"] = self.limit_cb.isChecked()
        self.settings["limit_count"] = self.limit_spin.value()
        # -------------------------------------------------

        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except IOError as e:
            self.log(f"❌ Error saving settings: {e}")
            
    def open_settings(self):
        dialog = SettingsDialog(self.settings, self); dialog.setStyleSheet(self.styleSheet())
        if dialog.exec():
            self.settings = dialog.get_settings(); self.save_settings()
            self.log("✅ Settings saved."); self.update_remaining_links_label()
    

    def open_auth_checker(self):
        # AuthCheckDialog'u çağırırken log fonksiyonumuzu ona iletiyoruz
        dialog = AuthCheckDialog(log_function=self.log, parent=self)
        dialog.setStyleSheet(self.styleSheet()) # Ana pencerenin temasını uygula
        dialog.exec()
        
    def apply_theme(self, theme_name):
        self.settings["theme"] = theme_name
        self.setStyleSheet(THEMES.get(theme_name))
        for name, action in self.theme_actions.items(): action.setChecked(name == theme_name)
        self.set_controls_enabled(self.start_button.isEnabled())

    def open_path(self, path_str):
        if not path_str: QMessageBox.warning(self, "Path Not Set", "Path not configured in settings."); return
        path = Path(path_str).resolve()
        if not path.exists():
            if ".txt" in path.name:
                if QMessageBox.question(self, "Create?", f"'{path.name}' not found. Create it?") == QMessageBox.StandardButton.Yes: path.touch()
                else: return
            else: QMessageBox.warning(self, "Not Found", f"Path does not exist:\n{path}"); return
        if sys.platform == "win32": os.startfile(path)
        elif sys.platform == "darwin": subprocess.run(["open", path])
        else: subprocess.run(["xdg-open", path])

    def add_link_from_clipboard(self):
        try:
            with open(self.settings.get("links_file"), 'a') as f: f.write(QApplication.clipboard().text().strip() + '\n')
            self.log("✅ Link added."); self.update_remaining_links_label()
        except Exception as e: QMessageBox.critical(self, "File Error", f"Could not write to links file: {e}")
    
    def clear_used_links(self):
        if QMessageBox.question(self, "Confirm", "Clear used links log?") == QMessageBox.StandardButton.Yes:
            try: Path(self.settings.get("used_links_file")).write_text(''); self.log("✅ Used links log cleared."); self.update_remaining_links_label()
            except Exception as e: QMessageBox.critical(self, "File Error", f"Could not clear file: {e}")
    
    def clear_output(self):
        if QMessageBox.question(self, "Confirm", f"Delete all content in output directory?") == QMessageBox.StandardButton.Yes:
            try:
                import shutil; output_dir = Path(self.settings.get("output_dir"))
                for item in output_dir.iterdir():
                    if item.is_dir(): shutil.rmtree(item)
                    else: item.unlink()
                self.log("✅ Output directory cleared.")
            except Exception as e: QMessageBox.critical(self, "Deletion Error", f"Could not clear output: {e}")
    
    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal(); self.setGeometry(*self.settings.get("window_geometry", QRect(100, 100, 1280, 720)))
            self.title_bar.maximize_button.setIcon(qta.icon('fa5s.window-maximize', color='#D8DEE9'))
        else:
            self.settings["window_geometry"] = self.geometry().getRect(); self.showFullScreen()
            self.title_bar.maximize_button.setIcon(qta.icon('fa5s.window-restore', color='#D8DEE9'))
    
    def show_with_fade_in(self):
        self.animation = QPropertyAnimation(self.opacity_effect, b"opacity"); self.animation.setDuration(500)
        self.animation.setStartValue(0.0); self.animation.setEndValue(1.0); self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.showFullScreen(); self.title_bar.maximize_button.setIcon(qta.icon('fa5s.window-restore', color='#D8DEE9'))
        self.animation.start()

    def show_about(self): QMessageBox.about(self, "About", "Revolvo YouTube Automation v2.3")

    def closeEvent(self, event):
        self.save_settings()
        if self.creator_worker and self.creator_worker.isRunning(): self.creator_worker.stop(); self.creator_worker.wait()
        event.accept()

# --- APP.PY DOSYASININ EN ALTI ---

def get_saved_theme():
    """Ayarlar dosyasından son seçilen temayı okur."""
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, 'r') as f:
                data = json.load(f)
                # Kayıtlı temayı döndür, yoksa varsayılan olarak Cyber Red olsun
                return data.get("theme", "Cyber Red")
    except Exception:
        pass
    return "Cyber Red" # Dosya okunamazsa varsayılan

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 1. Kayıtlı temayı bul
    saved_theme_name = get_saved_theme()
    
    # 2. Temanın CSS kodunu sözlükten çek (Bulamazsa Cyber Red kullan)
    current_theme_css = THEMES.get(saved_theme_name, THEMES.get("Cyber Red"))

    # 3. Login ekranını oluştur ve temayı uygula
    login_dialog = LoginDialog()
    login_dialog.setStyleSheet(current_theme_css) 
    
    # İkonları temaya uygun hale getirelim (Beyaz/Gri tonlar Cyber Red için uygun)
    login_dialog.setWindowIcon(qta.icon('fa5s.lock', color='#D6D6D6'))
    login_dialog.login_button.setIcon(qta.icon('fa5s.sign-in-alt', color='#D6D6D6'))
    
    # 4. Login penceresini göster
    if login_dialog.exec():
        # Giriş başarılıysa ana uygulamayı başlat
        window = AutomationApp()
        # Ana uygulama zaten kendi içinde settings dosyasını okuyup aynı temayı açacak
        window.show_with_fade_in()
        sys.exit(app.exec())
    else:
        sys.exit(0)