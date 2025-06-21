#!/usr/bin/env python3
import os
import re
import subprocess
import requests
from bs4 import BeautifulSoup
from datetime import datetime
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

# ====================== LISTA DE CANAIS ======================
CHANNELS = {
    "News": [
        "@ABCNews",
        "@AlJazeera",
        "@AlJazeeraEnglish",
        "@CNNbrasil",
        "@France24_en",
        "@Reuters"
    ],
    "Synthwave": [
        "@LofiGirl"
    ]
}

# ====================== FUNÇÕES ATUALIZADAS ======================
def get_live_url(channel_id):
    """Obtém URL de live ativa usando a nova estrutura do YouTube"""
    try:
        url = f"https://www.youtube.com/{channel_id}/live"
        logging.info(f"Analisando: {url}")
        
        response = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Método 1: Via elemento do player (100% confiável)
        player = soup.select_one('ytd-watch-flexy[video-id]')
        if player:
            video_id = player['video-id']
            live_url = f"https://www.youtube.com/watch?v={video_id}"
            logging.info(f"Live encontrada via player: {live_url}")
            return live_url
        
        # Método 2: Via dados embedados (fallback)
        script = soup.find('script', string=re.compile('var ytInitialPlayerResponse'))
        if script:
            match = re.search(r'"videoId"\s*:\s*"([^"]+)"', script.string)
            if match:
                video_id = match.group(1)
                live_url = f"https://www.youtube.com/watch?v={video_id}"
                logging.info(f"Live encontrada via script: {live_url}")
                return live_url
        
        logging.warning("Nenhum ID de vídeo encontrado")
        return None
    except Exception as e:
        logging.error(f"Falha ao obter live: {str(e)}")
        logging.debug(traceback.format_exc())
        return None

def get_stream_url(youtube_url):
    """Extrai URL de stream usando yt-dlp"""
    try:
        logging.info(f"Extraindo stream: {youtube_url}")
        result = subprocess.run(
            ["yt-dlp", "-g", "--format", "best", youtube_url],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            stream_url = result.stdout.strip()
            logging.info(f"Stream obtido: {stream_url[:60]}...")
            return stream_url
        
        logging.warning("yt-dlp retornou erro")
        return None
    except Exception as e:
        logging.error(f"Falha no yt-dlp: {str(e)}")
        return None

# ====================== EXECUÇÃO PRINCIPAL ======================
if __name__ == "__main__":
    log_file = setup_logging()
    logging.info("="*60)
    logging.info("INÍCIO DA EXECUÇÃO")
    logging.info("="*60)
    
    try:
        # Teste com canal conhecido (LofiGirl)
        test_channel = "@LofiGirl"
        logging.info(f"\nTESTE COM {test_channel}:")
        
        live_url = get_live_url(test_channel)
        if live_url:
            stream_url = get_stream_url(live_url)
            logging.info(f"RESULTADO TESTE: {'SUCESSO' if stream_url else 'FALHA'}")
        else:
            logging.error("LIVE NÃO ENCONTRADA NO TESTE")
        
        logging.info("\n" + "="*60)
        logging.info("TESTE COMPLETO")
        logging.info("="*60)
        
    except Exception as e:
        logging.error("\n" + "="*60)
        logging.error(f"ERRO NO TESTE: {str(e)}")
        logging.error("="*60)
        logging.error(traceback.format_exc())
    
    logging.info(f"Log salvo em: {log_file}")
