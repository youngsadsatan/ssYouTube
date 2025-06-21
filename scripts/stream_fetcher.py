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
import logging
import traceback

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
def get_live_url(channel_id):
    """Obtém URL de live ativa a partir de um canal do YouTube"""
    try:
        logging.info(f"Buscando live para {channel_id}")
        url = f"https://www.youtube.com/{channel_id}/live"
        
        response = requests.get(
            url,
            headers={'User-Agent': USER_AGENT},
            timeout=20
        )
        logging.debug(f"Status code: {response.status_code}, URL final: {response.url}")
        
        # Se foi redirecionado para uma URL de vídeo, retorna
        if "watch?v=" in response.url:
            logging.info(f"Live encontrada por redirecionamento: {response.url}")
            return response.url
        
        # Parse do HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        logging.debug(f"HTML parseado para {channel_id}")
        
        # Tenta encontrar via JSON-LD
        script = soup.find('script', type='application/ld+json')
        if script:
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    data = data[0]
                if data.get('url') and "watch?v=" in data['url']:
                    logging.info(f"Live encontrada via JSON-LD: {data['url']}")
                    return data['url']
            except Exception as e:
                logging.error(f"Erro ao parsear JSON-LD: {str(e)}")
        
        # Tenta encontrar via link canonical
        canonical = soup.find('link', rel='canonical')
        if canonical and "watch?v=" in canonical.get('href', ''):
            logging.info(f"Live encontrada via canonical: {canonical['href']}")
            return canonical['href']
        
        # Tenta encontrar via meta tag og:url
        meta_url = soup.find('meta', property='og:url')
        if meta_url and "watch?v=" in meta_url.get('content', ''):
            logging.info(f"Live encontrada via og:url: {meta_url['content']}")
            return meta_url['content']
        
        logging.warning(f"Nenhuma live encontrada para {channel_id}")
        return None
    except Exception as e:
        logging.error(f"Falha ao obter live de {channel_id}: {str(e)}")
        logging.debug(traceback.format_exc())
        return None

def get_stream_url(youtube_url):
    """Obtém URL de stream usando métodos confiáveis"""
    try:
        logging.info(f"Obtendo stream para: {youtube_url}")
        
        # Método 1: Usando yt-dlp
        try:
            result = subprocess.run(
                ["yt-dlp", "-g", "--format", "best", youtube_url],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                stream_url = result.stdout.strip()
                logging.info(f"Stream obtido via yt-dlp: {stream_url[:60]}...")
                return stream_url
        except Exception as e:
            logging.error(f"yt-dlp falhou: {str(e)}")
        
        # Método 2: Extração direta do HTML
        response = requests.get(
            youtube_url,
            headers={'User-Agent': USER_AGENT},
            timeout=20
        )
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Procura por player_response
        scripts = soup.find_all('script')
        for script in scripts:
            if 'ytInitialPlayerResponse' in script.text:
                match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?})\s*;', script.text)
                if match:
                    player_data = json.loads(match.group(1))
                    streaming_data = player_data.get('streamingData', {})
                    
                    # Tenta obter URL direta
                    formats = streaming_data.get('formats', []) + streaming_data.get('adaptiveFormats', [])
                    for fmt in formats:
                        if fmt.get('url'):
                            stream_url = fmt['url']
                            logging.info(f"Stream encontrado em player_response: {stream_url[:60]}...")
                            return stream_url
                    
                    # Tenta obter URL do manifest
                    hls_url = streaming_data.get('hlsManifestUrl')
                    if hls_url:
                        logging.info(f"Manifest HLS encontrado: {hls_url}")
                        return hls_url
        
        # Método 3: Procura por links m3u8 no HTML
        m3u8_urls = re.findall(r'(https?://[^\s]+?\.m3u8(?:\?[^\s"]+)?)', response.text)
        if m3u8_urls:
            stream_url = m3u8_urls[0]
            logging.info(f"Stream encontrado via regex: {stream_url[:60]}...")
            return stream_url
        
        logging.warning("Nenhum método de extração funcionou")
        return None
    except Exception as e:
        logging.error(f"Falha ao extrair stream: {str(e)}")
        logging.debug(traceback.format_exc())
        return None

def download_icon(channel_id):
    """Baixa e processa ícone do canal do YouTube"""
    try:
        logging.info(f"Baixando ícone para {channel_id}")
        icon_dir = "icons"
        os.makedirs(icon_dir, exist_ok=True)
        icon_path = os.path.join(icon_dir, f"{channel_id}.png")
        
        if os.path.exists(icon_path):
            return icon_path
            
        # Tenta obter o ID do vídeo mais recente
        response = requests.get(
            f"https://www.youtube.com/{channel_id}/videos",
            headers={'User-Agent': USER_AGENT},
            timeout=15
        )
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Procura por um link de vídeo
        video_link = soup.find('a', {'id': 'video-title-link'})
        if video_link and 'href' in video_link.attrs:
            video_id = video_link['href'].split('=')[-1]
            icon_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        else:
            # Fallback para thumbnail do canal
            icon_url = f"https://img.youtube.com/vi/{channel_id[1:]}/hqdefault.jpg"
        
        # Baixa o ícone
        response = requests.get(
            icon_url,
            headers={'User-Agent': USER_AGENT},
            stream=True,
            timeout=20
        )
        
        if response.status_code != 200:
            logging.warning(f"Falha ao baixar ícone: status {response.status_code}")
            return None
            
        with open(icon_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Processa a imagem
        try:
            img = Image.open(icon_path)
            img = img.convert("RGBA")
            img.thumbnail((128, 128))
            img.save(icon_path, "PNG")
            return icon_path
        except Exception as e:
            logging.warning(f"Falha ao processar ícone: {str(e)}")
            return icon_path  # Retorna mesmo sem processar
    except Exception as e:
        logging.error(f"Erro ao baixar ícone: {str(e)}")
        logging.debug(traceback.format_exc())
        return None

# ====================== GERADOR DE PLAYLIST ======================
def generate_playlists():
    """Gera playlists M3U organizadas por categoria"""
    try:
        playlists_dir = "playlists"
        os.makedirs(playlists_dir, exist_ok=True)
        
        category_entries = {category: [] for category in CHANNELS.keys()}
        total_streams = 0
        
        for category, channels in CHANNELS.items():
            logging.info(f"\nProcessando categoria: {category}")
            category_streams = 0
            
            for channel in sorted(channels):
                logging.info(f" - Canal: {channel}")
                
                # Passo 1: Obter URL da live
                live_url = get_live_url(channel)
                if not live_url:
                    logging.warning(f"   Nenhuma live ativa encontrada")
                    continue
                
                # Passo 2: Extrair URL do stream
                stream_url = get_stream_url(live_url)
                if not stream_url:
                    logging.warning(f"   Nenhum stream encontrado")
                    continue
                
                # Passo 3: Baixar ícone
                icon_path = download_icon(channel)
                icon_url = f"{BASE_URL}icons/{channel}.png" if icon_path else ""
                
                # Passo 4: Criar entrada M3U
                stream_name = channel[1:]  # Remove '@'
                entry = (
                    f'#EXTINF:-1 tvg-id="{channel}" tvg-name="{stream_name}" '
                    f'tvg-logo="{icon_url}" group-title="{category}",{stream_name}\r\n'
                    f"{stream_url}\r\n"
                )
                category_entries[category].append(entry)
                category_streams += 1
                total_streams += 1
                
                # Delay para evitar bloqueio
                time.sleep(1)
            
            logging.info(f"  Categoria completa: {category_streams} streams")
        
        # Gerar arquivos por categoria
        for category, entries in category_entries.items():
            if not entries:
                continue
                
            playlist_path = os.path.join(playlists_dir, f"{category}.m3u")
            with open(playlist_path, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\r\n")
                sorted_entries = sorted(entries, key=lambda x: x.split(',')[1].lower())
                f.writelines(sorted_entries)
            
            logging.info(f"Playlist gerada: {playlist_path} ({len(entries)} streams)")
        
        return total_streams
    except Exception as e:
        logging.error(f"Erro ao gerar playlists: {str(e)}")
        logging.debug(traceback.format_exc())
        return 0

# ====================== EXECUÇÃO PRINCIPAL ======================
if __name__ == "__main__":
    log_file = setup_logging()
    logging.info("="*60)
    logging.info(f"Iniciando atualização de playlists - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info("="*60)
    
    try:
        start_time = time.time()
        total_streams = generate_playlists()
        elapsed_time = time.time() - start_time
        
        logging.info("\n" + "="*60)
        if total_streams > 0:
            logging.info(f"Atualização concluída com sucesso! {total_streams} streams encontrados")
        else:
            logging.error("ATENÇÃO: Nenhum stream foi encontrado!")
        logging.info(f"Tempo total: {elapsed_time:.2f} segundos")
        logging.info("="*60)
    except Exception as e:
        logging.error("\n" + "="*60)
        logging.error(f"ERRO CRÍTICO: {str(e)}")
        logging.error("="*60)
        logging.error(traceback.format_exc())
    
    logging.info(f"Log completo salvo em: {log_file}")
