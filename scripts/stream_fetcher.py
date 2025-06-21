#!/usr/bin/env python3
import os
import re
import subprocess
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from PIL import Image
from urllib.parse import urlparse
import json
import time

# Configurações globais
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
BASE_URL = "https://raw.githubusercontent.com/youngsadsatan/ssYouTube/gh-pages/"

# ====================== LISTA DE CANAIS ORGANIZADA ======================
CHANNELS = {
    "Cams": [
        "@CGTNEurope",
        "@DDCyprus1Click",
        "@intelcamslive",
        "@SourceGlobal"
    ],
    "News": [
        "@ABCNews",
        "@AlJazeera",
        "@AlJazeeraEnglish",
        "@AssociatedPress",
        "@CNNbrasil",
        "@CRUXnews",
        "@France24",  # Corrigido: removido _en que tinha DRM
        "@LiveNowFox",
        "@Reuters",
        "@SkyNews",
        "@WION"
    ],
    "Rap": [
        "@RapMafia"
    ],
    "Synthwave": [
        "@80sNeonWave",
        "@DjScenester",
        "@LofiGirl",
        "@NightRideFM",
        "@StarBurstMusic",
        "@ThePrimeThanatos",
        "@VibeRetro"
    ],
    "Tornados": [
        "@MaxVelocityWX",
        "@ReedTimmerWx",
        "@RyanHallYall"
    ],
    "YouTubers": [
        "@Vaush"
    ]
}

# ====================== FUNÇÕES AUXILIARES ATUALIZADAS ======================
def get_live_url(channel_url):
    """Obtém URL de live ativa a partir de um canal do YouTube"""
    try:
        if not channel_url.endswith('/live'):
            channel_url = channel_url.rstrip('/') + '/live'
            
        response = requests.get(
            channel_url,
            timeout=20,
            headers={'User-Agent': USER_AGENT}
        )
        response.raise_for_status()
        
        # Verifica redirecionamento direto
        if "watch?v=" in response.url:
            return response.url
            
        # Parse do HTML para encontrar link da live
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Tenta 1: Meta tag og:url
        meta_url = soup.find('meta', property='og:url')
        if meta_url and "watch?v=" in meta_url.get('content', ''):
            return meta_url['content']
        
        # Tenta 2: Link canonical
        canonical = soup.find('link', rel='canonical')
        if canonical and "watch?v=" in canonical.get('href', ''):
            return canonical['href']
        
        # Tenta 3: JSON-LD
        script = soup.find('script', type='application/ld+json')
        if script:
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    data = data[0]
                if data.get('url') and "watch?v=" in data['url']:
                    return data['url']
            except:
                pass
        
        return None
    except Exception as e:
        print(f"[ERRO] Falha ao obter live de {channel_url}: {str(e)}")
        return None

def fetch_stream_with_ytdlp(youtube_url):
    """Obtém URL de stream usando yt-dlp (formato m3u8)"""
    try:
        command = [
            "yt-dlp",
            "-g",
            "--format", "best",
            "--no-check-certificates",
            youtube_url
        ]
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            # yt-dlp retorna a URL direta do stream
            return result.stdout.strip()
        else:
            print(f"[ERRO] yt-dlp retornou erro: {result.stderr}")
            return None
    except Exception as e:
        print(f"[ERRO] yt-dlp falhou para {youtube_url}: {str(e)}")
        return None

def download_icon(channel_id):
    """Baixa e processa ícone do canal do YouTube"""
    try:
        icon_dir = "icons"
        os.makedirs(icon_dir, exist_ok=True)
        icon_path = os.path.join(icon_dir, f"{channel_id}.png")
        
        # Verifica se o ícone já existe
        if os.path.exists(icon_path):
            return icon_path
            
        # URL alternativa para ícones de canal
        response = requests.get(
            f"https://www.youtube.com/{channel_id}",
            headers={'User-Agent': USER_AGENT},
            timeout=15
        )
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Tenta encontrar o link do ícone
        icon_link = soup.find('link', rel='image_src')
        if icon_link and 'href' in icon_link.attrs:
            icon_url = icon_link['href']
        else:
            # Fallback para thumbnail padrão
            icon_url = f"https://img.youtube.com/vi/{channel_id}/hqdefault.jpg"
        
        # Baixa o ícone
        response = requests.get(
            icon_url,
            headers={'User-Agent': USER_AGENT},
            stream=True,
            timeout=20
        )
        response.raise_for_status()
        
        with open(icon_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Processa a imagem
        img = Image.open(icon_path)
        img = img.convert("RGBA")
        
        # Redimensiona mantendo proporção
        img.thumbnail((128, 128))
        
        # Salva como PNG
        img.save(icon_path, "PNG")
        return icon_path
    except Exception as e:
        print(f"[ERRO] Falha ao baixar ícone {channel_id}: {str(e)}")
        return None

# ====================== GERADOR DE PLAYLIST CORRIGIDO ======================
def generate_playlists():
    """Gera playlists M3U organizadas por categoria"""
    playlists_dir = "playlists"
    os.makedirs(playlists_dir, exist_ok=True)
    
    # Dicionário para armazenar entradas por categoria
    category_entries = {category: [] for category in CHANNELS.keys()}
    
    # Processa todos os canais
    for category, channels in CHANNELS.items():
        print(f"\nProcessando categoria: {category}")
        
        for channel in sorted(channels):
            print(f" - Canal: {channel}")
            channel_url = f"https://www.youtube.com/{channel}"
            
            # Obtém URL da live
            live_url = get_live_url(channel_url)
            if not live_url:
                print(f"   [AVISO] Nenhuma live ativa encontrada para {channel}")
                continue
            
            print(f"   Live encontrada: {live_url}")
            
            # Obtém stream URL com yt-dlp
            stream_url = fetch_stream_with_ytdlp(live_url)
            if not stream_url:
                print(f"   [AVISO] Nenhum stream encontrado para {channel}")
                continue
            
            print(f"   Stream obtido: {stream_url[:60]}...")
            
            # Baixa ícone
            icon_path = download_icon(channel)
            icon_url = f"{BASE_URL}icons/{channel}.png" if icon_path else ""
            
            # Cria entrada M3U
            stream_name = channel[1:]  # Remove '@'
            entry = (
                f'#EXTINF:-1 tvg-id="{channel}" tvg-name="{stream_name}" '
                f'tvg-logo="{icon_url}" group-title="{category}",{stream_name}\r\n'
                f"{stream_url}\r\n"
            )
            category_entries[category].append(entry)
    
    # Gera arquivos por categoria
    for category, entries in category_entries.items():
        if not entries:
            continue
            
        playlist_path = os.path.join(playlists_dir, f"{category}.m3u")
        with open(playlist_path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\r\n")
            # Ordena entradas alfabeticamente
            sorted_entries = sorted(entries, key=lambda x: x.split(',')[1].lower())
            f.writelines(sorted_entries)
        
        print(f"Playlist gerada: {playlist_path} ({len(entries)} streams)")

# ====================== EXECUÇÃO PRINCIPAL ======================
if __name__ == "__main__":
    print("="*60)
    print(f"Iniciando atualização de playlists - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    try:
        generate_playlists()
        print("\n" + "="*60)
        print("Atualização concluída com sucesso!")
        print("="*60)
    except Exception as e:
        print("\n" + "="*60)
        print(f"ERRO CRÍTICO: {str(e)}")
        print("="*60)
        raise
