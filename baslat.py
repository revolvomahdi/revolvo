import sys
import os
import time
import requests
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QProgressBar, QMessageBox
from PyQt6.QtCore import QThread, pyqtSignal, Qt

# --- SENİN DOĞRULADIĞIN LİNK ---
BASE_URL = "https://raw.githubusercontent.com/revolvomahdi/revolvo/main/"
# -----------------------------

class ForceUpdateWorker(QThread):
    progress = pyqtSignal(str, int)
    finished = pyqtSignal(bool, str)

    def run(self):
        try:
            self.progress.emit("Sunucuya bağlanılıyor...", 5)
            
            # 1. Manifest İndir
            manifest_url = BASE_URL + "manifest.json?t=" + str(time.time())
            print(f"Manifest indiriliyor: {manifest_url}")
            
            r = requests.get(manifest_url)
            if r.status_code != 200:
                raise Exception(f"Manifest indirilemedi! Kod: {r.status_code}")
            
            remote_manifest = r.json()
            print(f"Manifest okundu: {len(remote_manifest)} dosya var.")

            # 2. HİÇ KONTROL ETMEDEN ZORLA İNDİR
            # (Dosya var mı yok mu bakmıyoruz, üzerine yazıyoruz)
            files_to_download = list(remote_manifest.keys())
            
            count = len(files_to_download)
            self.progress.emit(f"{count} dosya indiriliyor...", 10)
            
            for i, file_path in enumerate(files_to_download):
                url = BASE_URL + file_path
                self.progress.emit(f"İndiriliyor: {file_path}", int(10 + (i / count * 90)))
                print(f"-> İndiriliyor: {file_path}")
                
                # Dosyayı indir
                r_file = requests.get(url)
                if r_file.status_code == 200:
                    # Klasör yolunu hazırla
                    p = Path(file_path)
                    p.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Yaz (utf-8 değil, binary modda 'wb')
                    with open(p, "wb") as f:
                        f.write(r_file.content)
                else:
                    print(f"!!! HATA: {file_path} indirilemedi.")
                    raise Exception(f"Dosya indirilemedi: {file_path}")
                
            self.progress.emit("Kurulum Tamamlandı!", 100)
            time.sleep(1)
            self.finished.emit(True, "Hazır")

        except Exception as e:
            print(f"GENEL HATA: {e}")
            self.finished.emit(False, str(e))

class UpdaterDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setFixedSize(350, 150)
        self.setStyleSheet("""
            QDialog { background-color: #050A14; border: 2px solid #006064; }
            QLabel { color: #CFD8DC; font-size: 13px; font-weight: bold; }
            QProgressBar { border: 1px solid #1C3A50; background-color: #020406; text-align: center; color: white; }
            QProgressBar::chunk { background-color: #00BCD4; }
        """)
        
        layout = QVBoxLayout(self)
        self.lbl = QLabel("Kurulum Başlatılıyor...")
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bar = QProgressBar()
        layout.addWidget(self.lbl)
        layout.addWidget(self.bar)
        
        self.worker = ForceUpdateWorker()
        self.worker.progress.connect(self.update_ui)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def update_ui(self, msg, val):
        self.lbl.setText(msg)
        self.bar.setValue(val)

    def on_finished(self, success, msg):
        if not success:
            QMessageBox.critical(self, "Kurulum Hatası", f"Hata:\n{msg}")
            self.close()
        else:
            self.lbl.setText("Uygulama Başlatılıyor...")
            # Son kontrol: Dosya gerçekten indi mi?
            if os.path.exists("app.py"):
                # Programı çalıştır ve launcher'ı kapat
                subprocess.Popen([sys.executable, "app.py"])
                self.close()
            else:
                QMessageBox.critical(self, "Kritik Hata", "İndirme başarılı dedi ama 'app.py' dosyası klasörde yok!\nLütfen klasör izinlerini kontrol edin.")
                self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UpdaterDialog()
    window.show()
    sys.exit(app.exec())