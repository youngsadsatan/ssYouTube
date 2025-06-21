#!/usr/bin/env python3
import os
import re
import subprocess
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from PIL import Image
from urllib.parse import urlparse

# Configurações globais
USER_AGENT = "IPTV-Updater/1.0"
MAX_STREAMS_PER_CHANNEL = 3
ICON_SIZE = (128, 128)
BASE_URL = "https://raw.githubusercontent.com/youngsadsatan/ssYouTube/gh-pages/"

# ====================== LISTA DE CANAIS ORGANIZADA ======================
# (Categorias e canais já em ordem alfabética A-Z)
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
        "@France24_en",
        "@LiveNowFox",
        "@NBCNews",
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

# ====================== FUNÇÕES AUXILIARES ======================
def get_live_url(channel_url):
    """Obtém URL de live ativa a partir de um canal do YouTube"""
    try:
        if not channel_url.endswith('/live'):
            channel_url = channel_url.rstrip('/') + '/live'
            
        response = requests.get(
            channel_url,
            timeout=15,
            headers={'User-Agent': USER_AGENT}
        )
        
        # Verifica redirecionamento direto
        if "watch?v=" in response.url:
            return response.url
            
        # Parse do HTML para encontrar link da live
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Tenta encontrar o link canonical
        live_link = soup.find('link', {'rel': 'canonical', 'href': True})
        if live_link and "watch?v=" in live_link['href']:
            return live_link['href']
            
        # Fallback: Procura por meta tag de URL
        meta_url = soup.find('meta', {'property': 'og:url', 'content': True})
        if meta_url and "watch?v=" in meta_url['content']:
            return meta_url['content']
            
        return None
    except Exception as e:
        print(f"[ERRO] Falha ao obter live de {channel_url}: {str(e)}")
        return None

def fetch_streams(youtube_url, max_streams=MAX_STREAMS_PER_CHANNEL):
    """Obtém URLs de stream usando Streamlink"""
    try:
        result = subprocess.run(
            ["streamlink", "--stream-url", youtube_url],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            return None
            
        # Processa múltiplas streams
        streams = []
        for line in result.stdout.splitlines():
            if re.match(r'^\d{3,4}p', line.strip()):
                quality, url = line.split(' ', 1)
                streams.append(url.strip())
        
        return streams[:max_streams] if streams else [result.stdout.strip()]
    except Exception as e:
        print(f"[ERRO] Streamlink falhou para {youtube_url}: {str(e)}")
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
            
        # Tenta diferentes resoluções de thumbnail
        resolutions = ['maxresdefault', 'hqdefault', 'mqdefault', 'sddefault']
        for res in resolutions:
            url = f"https://img.youtube.com/vi/{channel_id}/{res}.jpg"
            response = requests.get(
                url,
                headers={'User-Agent': USER_AGENT},
                stream=True
            )
            
            if response.status_code == 200:
                with open(icon_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # Processa a imagem
                img = Image.open(icon_path)
                img = img.convert("RGBA")
                
                # Cria fundo branco para ícones com transparência
                if img.mode in ('RGBA', 'LA'):
                    background = Image.new('RGBA', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background.convert('RGB')
                
                img.thumbnail(ICON_SIZE)
                img.save(icon_path, "PNG")
                return icon_path
                
        print(f"[AVISO] Ícone não encontrado para {channel_id}")
        return None
    except Exception as e:
        print(f"[ERRO] Falha ao baixar ícone {channel_id}: {str(e)}")
        return None

# ====================== GERADOR DE PLAYLIST ======================
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
            live_url = get_live_url(channel_url)
            
            if not live_url:
                print(f"   [AVISO] Nenhuma live ativa encontrada para {channel}")
                continue
                
            streams = fetch_streams(live_url)
            if not streams:
                print(f"   [AVISO] Nenhum stream encontrado para {channel}")
                continue
                
            # Baixa ícone
            icon_path = download_icon(channel)
            icon_url = f"{BASE_URL}icons/{channel}.png" if icon_path else ""
            
            # Adiciona entradas para cada stream
            for i, stream_url in enumerate(streams):
                stream_name = channel[1:]  # Remove '@'
                if len(streams) > 1:
                    stream_name += f"_live{i+1}"
                
                entry = (
                    f'#EXTINF:-1 tvg-id="{channel}" tvg-name="{stream_name}" '
                    f'tvg-logo="{icon_url}" group-title="{category}",{stream_name}\n'
                    f"{stream_url}\n"
                )
                category_entries[category].append(entry)
    
    # Gera arquivos por categoria
    for category, entries in category_entries.items():
        if not entries:
            continue
            
        playlist_path = os.path.join(playlists_dir, f"{category}.m3u")
        with open(playlist_path, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.writelines(sorted(entries))
        
        print(f"Playlist gerada: {playlist_path} ({len(entries)} streams)")

# ====================== EXECUÇÃO PRINCIPAL ======================
if __name__ == "__main__":
    print("="*60)
    print(f"Iniciando atualização de playlists - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    generate_playlists()
    
    print("\n" + "="*60)
    print("Atualização concluída com sucesso!")
    print("="*60)
