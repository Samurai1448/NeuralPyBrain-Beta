# -*- coding: utf-8 -*-
# Устанавливаем все нужные библиотеки
!pip install -q transformers torch accelerate diffusers beautifulsoup4 requests youtube-search-python yt-dlp openai-whisper duckduckgo_search geopy pillow gTTS ipywidgets pyacoustid pypdf python-docx wikipedia matplotlib

import torch
import requests
import os
import time
import sys
import json
import random
import whisper
import acoustid
import wikipedia
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
from bs4 import BeautifulSoup
from gtts import gTTS
from IPython.display import Audio, display, HTML, clear_output
import ipywidgets as widgets
from transformers import AutoModelForCausalLM, AutoTokenizer
from diffusers import StableDiffusionPipeline
from youtubesearchpython import VideosSearch
from duckduckgo_search import DDGS
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from pypdf import PdfReader
from docx import Document

wikipedia.set_lang("ru")

model_name = "Qwen/Qwen2.5-1.5B-Instruct"
ACOUSTID_API_KEY = "k7eVbrbF4Q"
HISTORY_FILE = "npb_chat_history.json"

print("Загружаем NeuralPyBrain... Пожалуйста, подожди пару минут.")
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
    device_map="auto"
)

print("Загружаем модель генерации изображений...")
image_model_id = "runwayml/stable-diffusion-v1-5"
image_pipe = StableDiffusionPipeline.from_pretrained(image_model_id, torch_dtype=torch.float16)
image_pipe = image_pipe.to("cuda")
image_pipe.enable_attention_slicing()

print("Загружаем модуль слуха и музыки (Whisper)...")
audio_model = whisper.load_model("tiny")

# --- СИСТЕМА СОХРАНЕНИЯ И ЗАГРУЗКИ ДИАЛОГОВ ---
def load_sessions_from_disk():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"Диалог 1 (Основной)": []}

def save_sessions_to_disk():
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(all_sessions, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ошибка сохранения истории: {e}")

all_sessions = load_sessions_from_disk()
current_session_key = list(all_sessions.keys())[0]

print(f"\nNeuralPyBrain полностью запущена! Загружено диалогов: {len(all_sessions)}\n")
print("-" * 50)

def waiting_animation(message="NeuralPyBrain думает"):
    sys.stdout.write(message)
    sys.stdout.flush()
    for _ in range(3):
        time.sleep(0.5)
        sys.stdout.write(".")
        sys.stdout.flush()
    print()

def speak_response(text, lang="ru"):
    try:
        clean_text = text.replace("??", "").replace("??", "").replace("??", "").replace("??", "").replace("**", "").replace("??", "").replace("??", "").replace("??", "").replace("??", "").replace("??", "").replace("??", "").replace("«", "").replace("»", "")
        tts = gTTS(text=clean_text, lang=lang, slow=False)
        filename = "response_audio.mp3"
        tts.save(filename)
        display(Audio(filename, autoplay=True))
    except Exception as e:
        print(f"Не удалось озвучить ответ: {e}")

def display_message_with_actions(message_text):
    safe_text = message_text.replace('`', '').replace('"', '&quot;').replace('\n', '<br>')
    html_code = f"""
    <div class="npb-container">
      <div class="npb-bubble">
        <div class="npb-text">{safe_text}</div>
      </div>
      <div class="npb-actions">
        <button class="npb-btn" title="Полезно" onclick="npbLike(this)"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path></svg></button>
<button class="npb-btn" title="Неплохо" onclick="npbDislike(this)"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3"></path></svg></button>
        <button class="npb-btn" title="Копировать текст" onclick="npbCopy(this, {message_text})"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg></button>
      </div>
    </div>
    <style>
      .npb-container {{ max-width: 650px; font-family: sans-serif; margin: 15px 0; }}
      .npb-bubble {{ background: #f0f4f9; padding: 14px 18px; border-radius: 14px; color: #1f1f1f; line-height: 1.5; }}
      .npb-actions {{ display: flex; align-items: center; gap: 4px; margin-top: 4px; }}
      .npb-btn {{ background: transparent; border: none; cursor: pointer; padding: 6px; border-radius: 50%; color: #585858; display: flex; align-items: center; justify-content: center; transition: background 0.2s, color 0.2s; }}
      .npb-btn:hover {{ background: rgba(0, 0, 0, 0.06); color: #1a73e8; }}
      .npb-btn.active {{ color: #1a73e8; }}
    </style>
    <script>
      function npbLike(btn) {{ btn.classList.toggle('active'); btn.parentElement.children[1].classList.remove('active'); }}
      function npbDislike(btn) {{ btn.classList.toggle('active'); btn.parentElement.children[0].classList.remove('active'); }}
      function npbCopy(btn, text) {{ navigator.clipboard.writeText(text); let orig = btn.style.color; btn.style.color = '#1a73e8'; setTimeout(() => btn.style.color = orig, 1000); }}
    </script>
    """
    display(HTML(html_code))
    speak_response(message_text)

# --- ИНСТРУМЕНТЫ ---

def get_weather(city):
    try:
        city_cleaned = city.strip().replace(" ", "+")
        url = f"https://wttr.in/{city_cleaned}?format=j1"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            current = data['current_condition'][0]
            temp = current.get('temp_C')
            feels = current.get('FeelsLikeC')
            desc = current.get('weatherDesc')[0].get('value')
            wind_speed = current.get('windspeedKmph')
            humidity = current.get('humidity')
            
            return f"??? Погода в городе {city.strip()}:\n\n??? Температура: {temp}°C (ощущается как {feels}°C)\n?? Состояние: {desc}\n?? Скорость ветра: {wind_speed} км/ч\n?? Влажность: {humidity}%"
        else:
            return f"?? Не удалось найти погоду для города: {city}"
    except Exception as e:
        return f"? Ошибка получения погоды: {e}"

def search_wikipedia(query):
    try:
        query = query.replace("вики", "").replace("wikipedia", "").strip()
        summary = wikipedia.summary(query, sentences=3)
        page = wikipedia.page(query)
        return f"?? Википедия — {page.title}:\n\n{summary}\n\n?? [Ссылка на статью]({page.url})"
    except Exception as e:
        return f"?? Ошибка поиска в Википедии: {e}"

def check_air_alarms():
    return "?? Статус воздушных тревог в Украине:\n\n?? Интерактивная карта в реальном времени:\n?? [Карта тревог (alerts.in.ua)](https://alerts.in.ua/)\n\n?? Переходите в укрытие при тревоге!"

def read_document_file(file_path):
    try:
        file_path = file_path.strip()
        if not os.path.exists(file_path): return f"?? Файл не найден: {file_path}"
        text_content = ""
        if file_path.endswith('.pdf'):
            reader = PdfReader(file_path)
            for page in reader.pages: text_content += page.extract_text() or ""
elif file_path.endswith('.docx'):
            doc = Document(file_path)
            for para in doc.paragraphs: text_content += para.text + "\n"
        elif file_path.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f: text_content = f.read()
        return f"?? Содержимое документа ({os.path.basename(file_path)}):\n\n{text_content[:1000]}..."
    except Exception as e:
        return f"? Ошибка чтения документа: {e}"

def transcribe_voice_message(audio_path):
    try:
        result = audio_model.transcribe(audio_path.strip(), task="transcribe")
        return f"??? Распознанный текст:\n\n\"{result['text']}\""
    except Exception as e:
        return f"? Ошибка аудио: {e}"

def search_roblox_places(query):
    try:
        response_text = f"?? Roblox плейсы:\n\n"
        with DDGS() as ddgs:
            for r in ddgs.text(f"roblox {query} плейс режим коды", max_results=3):
                response_text += f"?? {r.get('title')}\n  ?? {r.get('href')}\n\n"
        return response_text
    except Exception as e:
        return f"Ошибка: {e}"

def generate_meme(text):
    try:
        img = Image.new('RGB', (600, 350), color = (30, 30, 46))
        d = ImageDraw.Draw(img)
        d.rectangle([15, 15, 585, 335], outline=(100, 149, 237), width=3)
        d.text((30, 50), "?? NeuralPyBrain Meme Generator:", fill=(100, 149, 237))
        d.text((30, 120), text, fill=(255, 255, 255))
        img.save("generated_meme.png")
        display(img)
        return "??? Мем успешно создан и отрисован!"
    except Exception as e:
        return f"Ошибка создания мема: {e}"

def generate_chart(query):
    try:
        plt.figure(figsize=(6, 3.5))
        x = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн']
        y = [random.randint(10, 100) for _ in range(6)]
        plt.plot(x, y, marker='o', color='#1a73e8', linewidth=2, markersize=8)
        plt.title(f"?? График по запросу: {query}")
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.tight_layout()
        plt.savefig("generated_chart.png")
        plt.show()
        return "?? График успешно построен!"
    except Exception as e:
        return f"Ошибка построения графика: {e}"

def translate_and_speak(text):
    try:
        parts = text.split("|")
        to_translate = parts[0].strip()
        lang_code = parts[1].strip() if len(parts) > 1 else "en"
        inputs = tokenizer(f"Переведи на {lang_code}: {to_translate}", return_tensors="pt").to("cuda")
        outputs = model.generate(**inputs, max_new_tokens=60, pad_token_id=tokenizer.eos_token_id)
        translated = tokenizer.decode(outputs[0], skip_special_tokens=True)
        speak_response(translated, lang=lang_code)
        return f"?? Перевод ({lang_code}):\n\n{translated}"
    except Exception as e:
        return f"Ошибка перевода: {e}"

def search_youtube_simple(query):
    try:
        res = VideosSearch(query, limit=1).result().get('result', [])
        return res[0].get('link') if res else None
    except:
        return None

def identify_song(audio_path):
    try:
        duration, fingerprint = acoustid.fingerprint_file(audio_path.strip())
        response = acoustid.lookup(ACOUSTID_API_KEY, fingerprint, duration)
        match = response['results'][0]['recordings'][0]
        title, artist = match.get('title', 'Неизвестно'), match['artists'][0].get('name', 'Неизвестный')
        yt = search_youtube_simple(f"{artist} - {title}")
        return f"?? Песня: {title} - {artist}\n?? {yt}"
    except Exception as e:
        return f"? Ошибка музыки: {e}"

def generate_image(prompt):
    try:
        image = image_pipe(prompt, num_inference_steps=35, guidance_scale=7.5).images[0]
        image.save("generated_image.png")
        display(image)
        return "? Картинка успешно создана!"
    except Exception as e:
        return f"Ошибка: {e}"
def search_web(query):
    try:
        res_text = "?? Поиск:\n\n"
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=3):
                res_text += f"?? {r.get('title')}\n  ?? {r.get('href')}\n\n"
        return res_text
    except Exception as e:
        return f"Ошибка: {e}"

# --- ИНТЕРФЕЙС ---

history_selector = widgets.Dropdown(
    options=list(all_sessions.keys()),
    value=current_session_key,
    description='? Диалоги:',
    style={'description_width': 'initial'}
)

new_chat_btn = widgets.Button(
    description='? Новый диалог',
    button_style='info'
)

mode_selector = widgets.Dropdown(
    options=[
        ('?? Обычный чат', 'chat'),
        ('?? Эксперт по ИИ/Коду', 'ai_dev'),
        ('?? Прожарка (без матов)', 'roast'),
        ('??? Погода', 'weather'),
        ('?? График', 'chart'),
        ('??? Мем / Картинка', 'meme'),
        ('?? Перевод + Аудио', 'translate'),
        ('?? Тревога', 'alarm'),
        ('?? Википедия', 'wiki'),
        ('?? Roblox', 'roblox'),
        ('?? Арт по промпту', 'image'),
        ('?? Документ', 'doc'),
        ('??? Аудио', 'audio'),
        ('?? Музыка', 'song'),
        ('?? Поиск', 'search')
    ],
    value='chat',
    description='? Меню:',
    style={'description_width': 'initial'}
)

thinking_selector = widgets.Dropdown(
    options=[('? Быстро', 'fast'), ('?? Обычный', 'normal'), ('?? Раздумья', 'deep')],
    value='normal',
    description='?? Режим:',
    style={'description_width': 'initial'}
)

input_box = widgets.Text(
    value='',
    placeholder='Введи запрос...',
    description='Сообщение:',
    style={'description_width': 'initial'},
    layout=widgets.Layout(width='50%')
)

send_btn = widgets.Button(
    description='Отправить ??',
    button_style='success'
)

output_area = widgets.Output()

def on_new_chat_clicked(b):
    global current_session_key, all_sessions
    new_key = f"Диалог {len(all_sessions) + 1}"
    all_sessions[new_key] = []
    current_session_key = new_key
    history_selector.options = list(all_sessions.keys())
    history_selector.value = new_key
    save_sessions_to_disk()
    with output_area:
        clear_output(wait=True)
        print(f"? Создан и сохранен новый '{new_key}'!")

def on_history_changed(change):
    global current_session_key
    if change['type'] == 'change' and change['name'] == 'value':
        current_session_key = change['new']

history_selector.observe(on_history_changed)
new_chat_btn.on_click(on_new_chat_clicked)

def on_send_clicked(b):
    with output_area:
        clear_output(wait=True)
        user_text = input_box.value.strip()
        selected_mode = mode_selector.value
        thinking_mode = thinking_selector.value
        
        if not user_text and selected_mode not in ['chat', 'alarm']:
            print("?? Поле ввода пустое!")
            return

        waiting_animation("NeuralPyBrain думает")
        
        reply = ""
        current_history = all_sessions[current_session_key]

        if selected_mode == 'roast':
            prompt_text = f"Напиши едкую, остроумную и уничтожающую прожарку (без матов и нецензурных слов) на человека по имени или описанию: '{user_text}'. Используй сарказм, иронию и яркие метафоры:"
            try:
                inputs = tokenizer(prompt_text, return_tensors="pt").to("cuda")
                outputs = model.generate(**inputs, max_new_tokens=250, temperature=0.85, pad_token_id=tokenizer.eos_token_id)
                full_reply = tokenizer.decode(outputs[0], skip_special_tokens=True)
                reply = full_reply.replace(prompt_text, "").strip()
                reply = f"?? Интеллигентная прожарка:\n\n{reply}"
            except Exception as e:
                reply = f"Ошибка генерации: {e}"
            
            current_history.append(f"Ты (прожарка для {user_text}): {reply}")
            save_sessions_to_disk()
elif selected_mode in ['chat', 'ai_dev']:
            try:
                if selected_mode == 'ai_dev':
                    user_text = f"[Режим разработчика ИИ]: Напиши код, объясни архитектуру или помоги создать нейросеть для задачи: {user_text}"
                
                current_history.append(f"Ты: {user_text}")
                
                max_tokens, temp, prefix = (150, 0.4, "Кратко: ") if thinking_mode == 'fast' else (500, 0.7, "Подумай шаг за шагом как профессиональный архитектор ИИ: ") if thinking_mode == 'deep' else (300, 0.7, "")
                
                context_prompt = "\n".join(current_history[-6:]) + f"\n{prefix}NeuralPyBrain:"
                inputs = tokenizer(context_prompt, return_tensors="pt").to("cuda")
                outputs = model.generate(**inputs, max_new_tokens=max_tokens, temperature=temp, pad_token_id=tokenizer.eos_token_id)
                
                full_reply = tokenizer.decode(outputs[0], skip_special_tokens=True)
                reply = full_reply.split("NeuralPyBrain:")[-1].strip() if "NeuralPyBrain:" in full_reply else full_reply.strip()
                
                if selected_mode == 'ai_dev':
                    reply = "?? AI Developer Studio:\n\n" + reply
                elif thinking_mode == 'deep':
                    reply = "?? Режим глубоких раздумий:\n\n" + reply
                    
                current_history.append(f"NeuralPyBrain: {reply}")
                save_sessions_to_disk()
            except Exception as e:
                reply = f"Ошибка: {e}"
        elif selected_mode == 'weather': reply = get_weather(user_text)
        elif selected_mode == 'alarm': reply = check_air_alarms()
        elif selected_mode == 'wiki': reply = search_wikipedia(user_text)
        elif selected_mode == 'roblox': reply = search_roblox_places(user_text)
        elif selected_mode == 'meme': reply = generate_meme(user_text)
        elif selected_mode == 'chart': reply = generate_chart(user_text)
        elif selected_mode == 'translate': reply = translate_and_speak(user_text)
        elif selected_mode == 'image': reply = generate_image(user_text)
        elif selected_mode == 'doc': reply = read_document_file(user_text)
        elif selected_mode == 'audio': reply = transcribe_voice_message(user_text)
        elif selected_mode == 'song': reply = identify_song(user_text)
        elif selected_mode == 'search': reply = search_web(user_text)
            
        display_message_with_actions(reply)

send_btn.on_click(on_send_clicked)

display(widgets.VBox([
    widgets.HBox([history_selector, new_chat_btn]),
    widgets.HBox([mode_selector, thinking_selector, input_box, send_btn]), 
    output_area
]))