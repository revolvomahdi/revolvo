# Automation/settings/check.py

import os
from pathlib import Path

# Gerekli PyQt6 ve diğer kütüphaneleri import ediyoruz
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QWidget, QMessageBox
)
from PyQt6.QtGui import QFont
import qtawesome as qta

# Projenin diğer modüllerinden gerekli bilgileri alıyoruz
# Bu importların doğru çalışması için app.py'nin ana dizinde olması gerekir
from uploader import config as uploader_config
from uploader import youtube_uploader

class AuthCheckDialog(QDialog):
    def __init__(self, log_function, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kanal Yetkilendirmelerini Kontrol Et ve Yönet")
        self.setMinimumSize(650, 450)
        self.log_function = log_function
        
        main_layout = QVBoxLayout(self)
        
        info_label = QLabel(
            "Bu ekrandan her kanalın YouTube yetkilendirme durumunu kontrol edebilirsiniz.\n"
            "Kırmızı (❌) ikonlu kanalları 'Yeniden Yetkilendir' butonu ile yetkilendirin.\n"
            "<b>ÖNEMLİ:</b> Yetkilendirme yapmadan önce tarayıcınızdaki tüm Google hesaplarından çıkış yapın."
        )
        info_label.setWordWrap(True)
        
        self.channel_list = QListWidget()
        self.populate_channel_list()
        
        button_layout = QHBoxLayout()
        reset_all_button = QPushButton("Tüm Yetkileri (Token'ları) Sıfırla")
        reset_all_button.setStyleSheet("background-color: #BF616A;") # Kırmızı temalı buton
        reset_all_button.clicked.connect(self.reset_all_tokens)
        
        button_layout.addStretch()
        button_layout.addWidget(reset_all_button)
        
        main_layout.addWidget(info_label)
        main_layout.addWidget(self.channel_list)
        main_layout.addLayout(button_layout)
        
    def populate_channel_list(self):
        self.channel_list.clear()
        for lang_code, config in uploader_config.CHANNEL_CONFIGS.items():
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(5, 5, 5, 5)
            
            token_exists = Path(config["token_file"]).exists()
            icon_name = 'fa5s.check-circle' if token_exists else 'fa5s.times-circle'
            icon_color = 'green' if token_exists else '#BF616A'
            status_icon = qta.icon(icon_name, color=icon_color)
            
            status_label = QLabel()
            status_label.setPixmap(status_icon.pixmap(20, 20))
            
            channel_name_label = QLabel(f"<b>{config['channel_name']}</b> ({lang_code.upper()})")
            channel_name_label.setFont(QFont("Segoe UI", 10))
            
            auth_button = QPushButton("Yeniden Yetkilendir")
            auth_button.setFixedWidth(150)
            # lambda'nın içine lang_code=lang_code eklemek çok önemli!
            auth_button.clicked.connect(lambda _, lc=lang_code: self.authorize_channel(lc))
            
            layout.addWidget(status_label)
            layout.addWidget(channel_name_label)
            layout.addStretch()
            layout.addWidget(auth_button)
            
            list_item = QListWidgetItem(self.channel_list)
            list_item.setSizeHint(widget.sizeHint())
            self.channel_list.addItem(list_item)
            self.channel_list.setItemWidget(list_item, widget)

    def authorize_channel(self, lang_code):
        config = uploader_config.CHANNEL_CONFIGS.get(lang_code)
        if not config:
            self.log_function(f"❌ '{lang_code}' için yapılandırma bulunamadı.")
            return

        QMessageBox.information(self, "Önemli Hatırlatma", 
                                "Tarayıcınız şimdi açılacak.\n\n"
                                "1. Lütfen devam etmeden önce tarayıcınızdaki <b>TÜM Google hesaplarından çıkış yapın.</b>\n"
                                f"2. Ardından, <b>{config['channel_name']}</b> kanalına ait Google hesabıyla giriş yapın.")

        success = youtube_uploader.force_reauthorize(config["token_file"], self.log_function)
        if success:
            QMessageBox.information(self, "Başarılı", f"<b>{config['channel_name']}</b> kanalı başarıyla yetkilendirildi.")
        else:
            QMessageBox.critical(self, "Hata", "Yetkilendirme sırasında bir hata oluştu. Ana penceredeki logları kontrol edin.")
            
        self.populate_channel_list()

    def reset_all_tokens(self):
        reply = QMessageBox.question(self, "Tüm Yetkileri Sıfırla Onayı", 
                                     "Emin misiniz? Bu işlem, kaydedilmiş TÜM kanal giriş bilgilerini (token dosyalarını) silecek.\n"
                                     "Sonrasında tüm kanalları yeniden yetkilendirmeniz gerekecek.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            deleted_count = 0
            for config in uploader_config.CHANNEL_CONFIGS.values():
                token_file = Path(config["token_file"])
                if token_file.exists():
                    try:
                        os.remove(token_file)
                        self.log_function(f"🗑️ Yetki (token) silindi: {token_file.name}")
                        deleted_count += 1
                    except OSError as e:
                        self.log_function(f"❌ Token silinemedi: {e}")
            
            QMessageBox.information(self, "İşlem Tamamlandı", f"{deleted_count} adet yetki (token) dosyası başarıyla silindi.")
            self.populate_channel_list()