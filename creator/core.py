# Automation/creator/core.py
# Handles video downloading, processing, and metadata generation.
# --- FULLY CORRECTED VERSION FOR 2K 60FPS OUTPUT & GPU SUPPORT ---

import os
import re
import json
import time
import traceback
import subprocess
import threading
from pathlib import Path
import sys

import yt_dlp
from openai import OpenAI
from deep_translator import GoogleTranslator
from PIL import Image, ImageDraw, ImageFont
from langdetect import detect, LangDetectException
from PyQt6.QtCore import QObject, pyqtSignal

# --- Configuration ---
CREATOR_DIR = Path(__file__).parent
FONT_PATH = CREATOR_DIR / "Oswald-Regular.ttf"

# Supported languages
SUPPORTED_LANGUAGES = {
    "en": "English", "de": "German", "fr": "French",
    "es": "Spanish", "ru": "Russian", "it": "Italian", "tr": "Turkish"
}
LANG_CODE_MAP = {k: k for k in SUPPORTED_LANGUAGES}
ENABLED_LANGUAGES = list(SUPPORTED_LANGUAGES.keys())


# --- PyQt Signals for GUI Communication ---
class WorkerSignals(QObject):
    progress = pyqtSignal(int)
    log_message = pyqtSignal(str)
    remaining_links_count = pyqtSignal(int)
    processed_stats = pyqtSignal(int, int)
    video_finished = pyqtSignal(list)  


# --- File I/O Helper Functions ---
def read_lines_from_file(filepath):
    if not Path(filepath).exists(): return []
    with open(filepath, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def write_lines_to_file(filepath, lines):
    with open(filepath, 'w', encoding='utf-8') as f:
        for line in lines: f.write(line + '\n')

def append_line_to_file(filepath, line):
    with open(filepath, 'a', encoding='utf-8') as f: f.write(line + '\n')

def get_remaining_links_count(links_file_path, used_links_file_path):
    all_links = set(read_lines_from_file(links_file_path))
    used_links = set(read_lines_from_file(used_links_file_path))
    return len(all_links - used_links)


# --- Video Processing Core Functions ---
def get_video_id(youtube_url):
    match = re.search(r"(?:v=|\/|be\/)([a-zA-Z0-9_-]{11})(?:&|\?|$)", youtube_url)
    return match.group(1) if match else None

def download_video_and_metadata(youtube_url, output_base_dir, quality, signals: WorkerSignals):
    video_id = get_video_id(youtube_url)
    if not video_id:
        signals.log_message.emit(f"❌ Invalid YouTube URL: {youtube_url}")
        return None

    video_output_dir = output_base_dir / video_id
    video_output_dir.mkdir(parents=True, exist_ok=True)
    output_template = video_output_dir / '%(id)s.%(ext)s'
    
    quality_map = {
        "4K (2160p)": "2160", "2K (1440p)": "1440",
        "1080p": "1080", "720p": "720"
    }
    height_constraint = quality_map.get(quality, "1080")
    format_string = f'bestvideo[height<={height_constraint}]+bestaudio/best[height<={height_constraint}]'

    ydl_opts = {
        'outtmpl': str(output_template), 'format': format_string, 'merge_output_format': 'mp4',
        'writedescription': True, 'writeinfojson': True, 'quiet': True, 'no_warnings': True,
        'progress_hooks': [lambda d: signals.progress.emit(20) if d['status'] == 'finished' else None],
    }

    try:
        signals.log_message.emit(f"⏳ Downloading video ({quality}) for: {youtube_url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(youtube_url, download=True)
        downloaded_filepath = Path(ydl.prepare_filename(info_dict))
        info_dict['downloaded_filepath'] = str(downloaded_filepath)
        signals.log_message.emit(f"✅ Download complete: {info_dict.get('title', 'Untitled Video')}")
        return info_dict
    except Exception as e:
        signals.log_message.emit(f"❌ Error during download: {e}\n{traceback.format_exc()}")
        return None

def add_text_overlay_to_video(input_path, output_path, text, ffmpeg_preset, signals: WorkerSignals, enable_text=True, hardware_accel="CPU"):
    signals.log_message.emit(f"⏳ Processing (2K/60fps) | Text: {'ON' if enable_text else 'OFF'} | Encoder: {hardware_accel}")

    try:
        # 1. Encoder ve Preset Ayarlaması (Tercüman Kısmı)
        video_codec = 'libx264' # Varsayılan CPU
        final_preset = ffmpeg_preset # Varsayılan olarak arayüzden geleni kullan

        if hardware_accel == "NVIDIA (NVENC)":
            video_codec = 'h264_nvenc'
            # NVIDIA 'veryslow' anlamaz, onu P1-P7 arasına çevirmemiz lazım
            # P1: En Hızlı, P7: En Kaliteli
            if ffmpeg_preset in ["ultrafast", "superfast"]:
                final_preset = "p1"
            elif ffmpeg_preset in ["veryfast", "faster"]:
                final_preset = "p3"
            elif ffmpeg_preset in ["fast", "medium"]:
                final_preset = "p5"
            else: # slow, slower, veryslow
                final_preset = "p7" # En yüksek kaliteye sabitle
                
        elif hardware_accel == "AMD (AMF)":
            video_codec = 'h264_amf'
            # AMD için basit çeviri
            if "fast" in ffmpeg_preset: final_preset = "speed"
            elif "slow" in ffmpeg_preset: final_preset = "quality"
            else: final_preset = "balanced"
        
        # 2. Filtreler: 2K ölçekleme ve kare piksel
        vf_options = [f"scale=1440:2560", f"setsar=1"]

        # 3. Yazı Ekleme (İsteniyorsa)
        if enable_text:
            max_font_size = int(2560 / 25)
            min_font_size = int(2560 / 50)
            max_text_width = int(1440 * 0.9)

            font_size = max_font_size
            wrapped_text = text
            while font_size >= min_font_size:
                pil_font = ImageFont.truetype(str(FONT_PATH), font_size)
                avg_char_width = pil_font.getlength("x")
                max_chars_per_line = int(max_text_width / avg_char_width) if avg_char_width > 0 else 20
                wrapper = re.compile(f'.{{1,{max_chars_per_line}}}(?=\\s|$)')
                lines = wrapper.findall(text)
                wrapped_text = "\n".join(lines)
                text_w = max(pil_font.getlength(line) for line in lines) if lines else 0
                if text_w <= max_text_width:
                    break
                font_size -= 2
            else:
                signals.log_message.emit("⚠️ Text may overflow even at minimum font size.")
            
            escaped_font_path = str(FONT_PATH.resolve()).replace('\\', '/').replace(':', '\\:')
            vf_options.append(f"drawtext=fontfile='{escaped_font_path}':text='{wrapped_text}':fontcolor=white:fontsize={font_size}:x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.5:boxborderw=15")

        # 4. FFmpeg Komutunu Oluştur
        ffmpeg_cmd = [
            'ffmpeg', '-y', '-i', str(input_path),
            '-vf', ",".join(vf_options),
            '-r', '60',
            '-c:v', video_codec,
            '-preset', final_preset, # Artık çevrilmiş doğru preset kullanılıyor
            '-b:v', '15000k',
            '-maxrate', '20000k',
            '-bufsize', '30000k',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '192k',
            str(output_path)
        ]

        subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
        signals.log_message.emit(f"✅ Video processing complete: {output_path.name}")
        return True

    except FileNotFoundError:
        signals.log_message.emit("❌ FFmpeg/FFprobe not found. Check installation and system's PATH.")
        return False
    except subprocess.CalledProcessError as e:
        signals.log_message.emit(f"❌ FFmpeg error: {e.stderr}")
        return False
    except Exception as e:
        signals.log_message.emit(f"❌ Error during text overlay: {e}\n{traceback.format_exc()}")
        return False


# --- AI and Translation Functions ---
def generate_text_with_openai(client, prompt, model):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant for creating viral YouTube shorts content."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500, temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI API Error: {e}"); return None

def generate_motivational_sentence(client, model):
    prompt = "Generate a short, reverse-psychology motivational quote. Keep it under 10 words. Do not use emojis or quotes. Example: You're not good enough. Prove me wrong."
    return generate_text_with_openai(client, prompt, model) or "Go ahead, prove them right."

def translate_text(text, target_lang_code, signals: WorkerSignals):
    try:
        return GoogleTranslator(source='auto', target=target_lang_code).translate(text)
    except Exception as e:
        signals.log_message.emit(f"❌ Translation to '{target_lang_code}' failed: {e}")
        return text

def generate_seo_metadata(client, model, video_data, lang_key, signals: WorkerSignals):
    target_lang_code = LANG_CODE_MAP[lang_key]; target_lang_name = SUPPORTED_LANGUAGES[lang_key]
    signals.log_message.emit(f"⏳ Generating SEO metadata for {target_lang_name}...")
    
    context_title = translate_text(video_data.get('title', ''), target_lang_code, signals)
    context_description = translate_text(video_data.get('description', ''), target_lang_code, signals)
    context = f"Original Title: {context_title}\nOriginal Description: {context_description[:500]}"
    
    # Promptları biraz daha kesinleştirdim
    prompt_title = f"Create a viral, SEO-optimized YouTube Shorts title in {target_lang_name} under 60 characters. Do not use quotation marks. Context:\n{context}"
    prompt_description = f"Write a compelling, 2-3 sentence YouTube Shorts description in {target_lang_name}. Context:\n{context}"
    prompt_tags = f"List 5-10 relevant YouTube tags in {target_lang_name}, comma-separated. Context:\n{context}"
    
    title = generate_text_with_openai(client, prompt_title, model)
    description = generate_text_with_openai(client, prompt_description, model)
    tags_str = generate_text_with_openai(client, prompt_tags, model)
    
    if not all([title, description, tags_str]):
        signals.log_message.emit(f"❌ Failed to generate SEO metadata for {target_lang_name}."); return None
    
    # --- TEMİZLİK OPERASYONU (Tırnak Silici) ---
    # 1. Çift tırnakları sil (")
    title = title.replace('"', '')
    # 2. Tek tırnakları sil (') - İsteğe bağlı, bazen kesme işareti lazım olabilir ama başlıkta riskli duruyor
    # title = title.replace("'", "") 
    # 3. Başında ve sonunda boşluk varsa sil
    title = title.strip()
    
    # Bazen AI "Title: Milyarder..." diye cevap verir, "Title:" kısmını silelim
    if ":" in title:
        title = title.split(":")[-1].strip()
    # -------------------------------------------

    tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
    
    signals.log_message.emit(f"✅ SEO metadata generated for {target_lang_name}: {title}")
    return {"title": title, "description": description, "tags": tags}

def save_seo_metadata(video_id, metadata, lang_key, output_base_dir, signals: WorkerSignals):
    lang_output_dir = output_base_dir / video_id / lang_key
    lang_output_dir.mkdir(parents=True, exist_ok=True)
    filepath = lang_output_dir / f"metadata_{lang_key}.json"
    try:
        with open(filepath, 'w', encoding='utf-8') as f: json.dump(metadata, f, indent=4, ensure_ascii=False)
        signals.log_message.emit(f"💾 Metadata saved: {filepath.name}")
    except IOError as e: signals.log_message.emit(f"❌ Could not save metadata file: {e}")


# --- Main Processing Workflow ---
class InterruptedError(Exception): pass

def process_link(
    links_file_path, used_links_file_path, output_base_dir,
    openai_api_key, openai_model, yt_dlp_quality, ffmpeg_preset,
    signals: WorkerSignals, stop_event: threading.Event,
    enable_overlay=True, hardware_accel="CPU", max_limit=0): # max_limit parametresi eklendi
    
    if not openai_api_key:
        signals.log_message.emit("❌ OpenAI API key missing.")
        return False, "API Key missing", None, []
    try:
        client = OpenAI(api_key=openai_api_key)
    except Exception as e:
        signals.log_message.emit(f"❌ OpenAI Error: {e}")
        return False, str(e), None, []

    processed_count = 0
    total_time = 0
    
    # --- ANA DÖNGÜ BAŞLIYOR ---
    while True:
        # 1. Durdurma ve Limit Kontrolü
        if stop_event.is_set():
            signals.log_message.emit("🛑 Processing stopped by user.")
            break
            
        if max_limit > 0 and processed_count >= max_limit:
            signals.log_message.emit(f"🛑 Limit reached ({max_limit} videos). Stopping.")
            break

        # 2. Linkleri Oku
        all_links = read_lines_from_file(links_file_path)
        used_links = read_lines_from_file(used_links_file_path)
        links_to_process = [link for link in all_links if link not in used_links]

        if not links_to_process:
            signals.log_message.emit("ℹ️ No more links to process.")
            break

        link_to_process = links_to_process[0]
        video_id = None
        
        try:
            start_time = time.time()
            signals.log_message.emit(f"▶️ [{processed_count + 1}] Processing: {link_to_process}")
            
            # Linki 'kullanıldı' işaretle (Hata olsa bile tekrar denememek için başta işaretliyoruz, istersen sona alabilirsin)
            append_line_to_file(used_links_file_path, link_to_process)
            
            # Kalan link sayısını güncelle
            signals.remaining_links_count.emit(len(links_to_process) - 1)
            signals.progress.emit(10)

            # 3. İndirme İşlemi
            video_info = download_video_and_metadata(link_to_process, output_base_dir, yt_dlp_quality, signals)
            if not video_info or 'downloaded_filepath' not in video_info:
                raise ValueError("Download failed.")
            
            video_id = video_info.get('id')
            original_video_path = Path(video_info['downloaded_filepath'])
            signals.progress.emit(30)
            
            if stop_event.is_set(): break

            # 4. AI ve İşleme
            translated_sentence = ""
            if enable_overlay:
                signals.log_message.emit("⏳ Generating motivation...")
                base_motivation_sentence = generate_motivational_sentence(client, openai_model)
                signals.log_message.emit(f"✅ Quote: '{base_motivation_sentence}'")
            
            current_batch_metadata = [] # Bu videoya ait tüm dillerin çıktısı

            for i, lang_key in enumerate(ENABLED_LANGUAGES):
                if stop_event.is_set(): break
                
                # SEO
                seo_metadata = generate_seo_metadata(client, openai_model, video_info, lang_key, signals)
                if not seo_metadata: continue
                save_seo_metadata(video_id, seo_metadata, lang_key, output_base_dir, signals)

                # Çeviri ve Overlay
                if enable_overlay:
                    translated_sentence = translate_text(base_motivation_sentence, LANG_CODE_MAP[lang_key], signals)
                
                lang_output_dir = output_base_dir / video_id / lang_key
                output_video_path = lang_output_dir / f"{lang_key}.mp4"
                
                overlay_success = add_text_overlay_to_video(
                    original_video_path, output_video_path, translated_sentence,
                    ffmpeg_preset, signals, enable_overlay, hardware_accel
                )
                
                if overlay_success:
                    upload_package = {**seo_metadata, 'lang': lang_key, 'video_path': str(output_video_path.resolve())}
                    current_batch_metadata.append(upload_package)
                
                # Progress barı her dil için biraz ilerlet
                signals.progress.emit(40 + int((i + 1) / len(ENABLED_LANGUAGES) * 60))

            # 5. Video Bitti, İstatistikleri Güncelle
            time_taken = int(time.time() - start_time)
            processed_count += 1
            total_time += time_taken
            signals.processed_stats.emit(processed_count, total_time)
            
            # --- TEK VİDEO SİNYALİ (Otomatik Yükleme İçin) ---
            if current_batch_metadata:
                signals.video_finished.emit(current_batch_metadata)
            
            signals.log_message.emit(f"✅ Finished processing link: {link_to_process}")
            signals.progress.emit(0) # Bir sonraki için barı sıfırla

        except Exception as e:
            signals.log_message.emit(f"❌ Error on {link_to_process}: {e}")
            # Hata olsa bile döngü devam eder, bir sonraki linke geçer.
            continue
            
    return True, "Batch processing completed.", None, []