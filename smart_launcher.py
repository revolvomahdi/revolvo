import sys
import os
import json
import time
import requests
import hashlib
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QProgressBar, QMessageBox
from PyQt6.QtCore import QThread, pyqtSignal, Qt

# --- AYARLAR (GitHub'daki "Raw" linkinin kökü) ---
# Örn: https://raw.githubusercontent.com/TheReis/Otomasyon/main/
BASE_URL = "BURAYA_GITHUB_RAW_LINKINI_YAPIŞTIR_SONU_SLASH_ILE_BİTSİN/" 
# ------------------------------------------------

class SmartUpdateWorker(QThread):
    progress = pyqtSignal(str, int) # Mesaj, Yüzde
    finished = pyqtSignal(bool, str)

    def calculate_local_md5(self, file_path):
        if not os.path.exists(file_path): return None
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except: return None

    def run(self):
        try:
            self.progress.emit("Sunucu kontrol ediliyor...", 10)
            
            # 1. Manifest Dosyasını İndir (Envanter Listesi)
            # Cache'i önlemek için sonuna rastgele sayı ekliyoruz
            manifest_url = BASE_URL + "manifest.json?t=" + str(time.time())
            try:
                r = requests.get(manifest_url)
                if r.status_code != 200: raise Exception("Sunucuya ulaşılamadı.")
                remote_manifest = r.json()
            except Exception as e:
                self.finished.emit(True, "İnternet yok, güncelleme geçildi.")
                return

            # 2. Farklılıkları Bul
            files_to_download = []
            
            total_checked = 0
            for file_path, remote_hash in remote_manifest.items():
                local_hash = self.calculate_local_md5(file_path)
                
                # Dosya yoksa VEYA Hash'ler tutmuyorsa -> İndirilecekler listesine ekle
                if local_hash != remote_hash:
                    files_to_download.append(file_path)
                
                total_checked += 1
            
            # 3. İndirme İşlemi
            if not files_to_download:
                self.progress.emit("Her şey güncel! Başlatılıyor...", 100)
                time.sleep(1)
                self.finished.emit(True, "Up to date")
                return

            count = len(files_to_download)
            self.progress.emit(f"{count} yeni dosya indiriliyor...", 20)
            
            for i, file_path in enumerate(files_to_download):
                url = BASE_URL + file_path
                self.progress.emit(f"İndiriliyor: {file_path}", int(20 + (i / count * 80)))
                
                r = requests.get(url)
                if r.status_code == 200:
                    # Klasör yapısını oluştur
                    p = Path(file_path)
                    p.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Dosyayı yaz
                    with open(p, "wb") as f:
                        f.write(r.content)
                
            self.progress.emit("Güncelleme Tamamlandı!", 100)
            time.sleep(0.5)
            self.finished.emit(True, "Updated")

        except Exception as e:
            self.finished.emit(False, str(e))

class UpdaterDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(350, 120)
        # Midnight Rain Teması
        self.setStyleSheet("""
            QDialog { background-color: #050A14; border: 2px solid #006064; }
            QLabel { color: #CFD8DC; font-family: 'Segoe UI'; font-size: 13px; }
            QProgressBar { border: 1px solid #1C3A50; background-color: #020406; text-align: center; color: white; }
            QProgressBar::chunk { background-color: #00BCD4; }
        """)
        
        layout = QVBoxLayout(self)
        
        self.lbl_status = QLabel("Güncellemeler denetleniyor...")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.prog_bar = QProgressBar()
        self.prog_bar.setValue(0)
        
        layout.addWidget(self.lbl_status)
        layout.addWidget(self.prog_bar)
        
        self.worker = SmartUpdateWorker()
        self.worker.progress.connect(self.update_ui)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def update_ui(self, msg, val):
        self.lbl_status.setText(msg)
        self.prog_bar.setValue(val)

    def on_finished(self, success, msg):
        if not success:
            QMessageBox.warning(self, "Hata", f"Güncelleme hatası: {msg}\nMevcut sürüm açılıyor...")
        
        # app.py'yi başlat ve bu pencereyi kapat
        subprocess.Popen([sys.executable, "app.py"])
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UpdaterDialog()
    window.show()
    sys.exit(app.exec())