#!/usr/bin/env python3
import os
import subprocess
import requests
from datetime import datetime
import logging
import json
import re

# Configurações globais
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
BASE_URL = "https://raw.githubusercontent.com/youngsadsatan/ssYouTube/gh-pages/"

# Configurar logging
def setup_logging():
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"stream_fetcher_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return log_file

# ====================== LISTA DIRETA DE STREAMS ======================
LIVE_STREAMS = {
    "News": [
        # Al Jazeera English
        {
            "name": "AlJazeeraEnglish",
            "url": "https://www.youtube.com/watch?v=zSM4ZyVe8xs",
            "icon": "https://i.ytimg.com/vi/zSM4ZyVe8xs/hqdefault.jpg"
        },
        # Al Jazeera Arabic
        {
            "name": "AlJazeera",
            "url": "https://www.youtube.com/watch?v=ZVJ5jVf3YAI",
            "icon": "https://i.ytimg.com/vi/ZVJ5jVf3YAI/hqdefault.jpg"
        },
        # France 24 English
        {
            "name": "France24_en",
            "url": "https://www.youtube.com/watch?v=HeTWwH1a5CQ",
            "icon": "https://i.ytimg.com/vi/HeTWwH1a5CQ/hqdefault.jpg"
        },
        # Reuters
        {
            "name": "Reuters",
            "url": "https://www.youtube.com/watch?v=wQOjBdzVvSU",
            "icon": "https://i.ytimg.com/vi/wQOjBdzVvSU/hqdefault.jpg"
        }
    ],
    "Synthwave": [
        # Lofi Girl
        {
            "name": "LofiGirl",
            "url": "https://www.youtube.com/watch?v=jfKfPfyJRdk",
            "icon": "https://i.ytimg.com/vi/jfKfPfyJRdk/hqdefault.jpg"
        }
    ]
}

# ====================== FUNÇÃO DE EXTRAÇÃO DIRETA ======================
def extract_stream_url(youtube_url):
    """Extrai URL de stream usando yt-dlp com fallback para API interna"""
    try:
        # Método 1: yt-dlp (prioritário)
        try:
            result = subprocess.run(
                ["yt-dlp", "-g", "--format", "best", youtube_url],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass

        # Método 2: API interna do YouTube
        video_id = youtube_url.split("v=")[1].split("&")[0]
        api_url = f"https://www.youtube.com/watch?v={video_id}"
        
        response = requests.get(api_url, headers={'User-Agent': USER_AGENT}, timeout=15)
        data = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?})\s*;', response.text)
        
        if data:
            player_data = json.loads(data.group(1))
            hls_url = player_data['streamingData']['hlsManifestUrl']
            return hls_url
        
        return None
    except Exception as e:
        logging.error(f"Falha na extração: {str(e)}")
        return None

# ====================== GERADOR DE PLAYLIST ======================
def generate_playlists():
    """Gera playlists M3U a partir de URLs diretas"""
    playlists_dir = "playlists"
    os.makedirs(playlists_dir, exist_ok=True)
    
    for category, streams in LIVE_STREAMS.items():
        playlist_path = os.path.join(playlists_dir, f"{category}.m3u")
        entries = []
        
        for stream in streams:
            logging.info(f"Processando: {stream['name']}")
            stream_url = extract_stream_url(stream['url'])
            
            if stream_url:
                entry = (
                    f'#EXTINF:-1 tvg-id="{stream["name"]}" '
                    f'tvg-logo="{stream["icon"]}" '
                    f'group-title="{category}",{stream["name"]}\r\n'
                    f"{stream_url}\r\n"
                )
                entries.append(entry)
                logging.info(f"Stream obtido: {stream_url[:60]}...")
            else:
                logging.warning(f"Falha ao extrair stream para {stream['name']}")
        
        # Escreve a playlist
        with open(playlist_path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\r\n")
            f.writelines(entries)
        
        logging.info(f"Playlist gerada: {playlist_path} ({len(entries)} streams)")

# ====================== EXECUÇÃO PRINCIPAL ======================
if __name__ == "__main__":
    log_file = setup_logging()
    logging.info("="*60)
    logging.info("SOLUÇÃO DIRETA - INÍCIO DA EXECUÇÃO")
    logging.info("="*60)
    
    try:
        generate_playlists()
        logging.info("\n" + "="*60)
        logging.info("EXECUÇÃO CONCLUÍDA COM SUCESSO!")
        logging.info("="*60)
    except Exception as e:
        logging.error("\n" + "="*60)
        logging.error(f"ERRO CRÍTICO: {str(e)}")
        logging.error("="*60)
    
    logging.info(f"Log completo salvo em: {log_file}")
