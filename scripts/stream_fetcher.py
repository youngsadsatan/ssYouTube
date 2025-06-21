#!/usr/bin/env python3
import os
import re
import subprocess
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from PIL import Image
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

# ====================== FUNÇÕES AUXILIARES ATUALIZADAS ======================
def get_active_live(channel_id):
    """Obtém URL de transmissão ao vivo ativa usando a API do YouTube"""
    try:
        # URL da API de busca do YouTube
        url = f"https://www.youtube.com/{channel_id}/live"
        
        response = requests.get(
            url,
            headers={'User-Agent': USER_AGENT},
            timeout=20
        )
        response.raise_for_status()
        
        # Extrai dados do JSON embutido
        soup = BeautifulSoup(response.text, 'html.parser')
        script = soup.find('script', string=re.compile('var ytInitialData'))
        
        if not script:
            print(f"   [ERRO] Script ytInitialData não encontrado para {channel_id}")
            return None
            
        # Extrai o objeto JSON
        json_str = script.string.split(' = ')[1].rstrip(';')
        data = json.loads(json_str)
        
        # Navega na estrutura para encontrar a transmissão ao vivo
        contents = data.get('contents', {}) \
                      .get('twoColumnBrowseResultsRenderer', {}) \
                      .get('tabs', [{}])[0] \
                      .get('tabRenderer', {}) \
                      .get('content', {}) \
                      .get('sectionListRenderer', {}) \
                      .get('contents', [{}])[0] \
                      .get('itemSectionRenderer', {}) \
                      .get('contents', [{}])[0] \
                      .get('channelFeaturedContentRenderer', {}) \
                      .get('items', [])
        
        for item in contents:
            video = item.get('videoRenderer', {})
            if video.get('thumbnailOverlays') and any(
                overlay.get('thumbnailOverlayTimeStatusRenderer', {}).get('style', '') == 'LIVE'
                for overlay in video.get('thumbnailOverlays', [])
            ):
                video_id = video.get('videoId')
                if video_id:
                    return f"https://www.youtube.com/watch?v={video_id}"
        
        return None
    except Exception as e:
        print(f"[ERRO] Falha ao obter live de {channel_id}: {str(e)}")
        return None

def extract_stream_url(youtube_url):
    """Extrai URL de stream usando métodos alternativos"""
    try:
        # Tentativa 1: yt-dlp
        try:
            result = subprocess.run(
                ["yt-dlp", "-g", "--format", "best", youtube_url],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except:
            pass
        
        # Tentativa 2: Extração direta via regex
        response = requests.get(
            youtube_url,
            headers={'User-Agent': USER_AGENT},
            timeout=20
        )
        response.raise_for_status()
        
        # Procura por URLs m3u8 no código fonte
        m3u8_urls = re.findall(r'(https?://[^\s]+?\.m3u8(?:\?[^\s"]+)?)', response.text)
        if m3u8_urls:
            return m3u8_urls[0]
        
        # Tentativa 3: Player_response JSON
        player_response = re.search(r'var ytInitialPlayerResponse\s*=\s*({.+?});', response.text)
        if player_response:
            player_data = json.loads(player_response.group(1))
            streaming_data = player_data.get('streamingData', {})
            formats = streaming_data.get('formats', []) + streaming_data.get('adaptiveFormats', [])
            for fmt in formats:
                if fmt.get('url'):
                    return fmt['url']
        
        return None
    except Exception as e:
        print(f"[ERRO] Falha ao extrair stream de {youtube_url}: {str(e)}")
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
            
        # Tenta obter o ícone via API
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
            icon_url = f"https://img.youtube.com/vi/{channel_id.split('@')[-1]}/hqdefault.jpg"
        
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
        img.thumbnail((128, 128))
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
            
            # Obtém URL da live
            live_url = get_active_live(channel)
            if not live_url:
                print(f"   [AVISO] Nenhuma live ativa encontrada para {channel}")
                continue
            
            print(f"   Live encontrada: {live_url}")
            
            # Obtém stream URL
            stream_url = extract_stream_url(live_url)
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
            
            # Delay para evitar bloqueio
            time.sleep(1)
    
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
