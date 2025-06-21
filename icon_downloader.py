import requests
from datetime import datetime

def download_icon(channel_id, size=(128,128)):
    try:
        response = requests.get(
            f"https://img.youtube.com/vi/{channel_id}/maxresdefault.jpg",
            headers={'User-Agent': 'Mozilla/5.0 (Custom IPTV Updater)'}
        )
        if response.status_code == 200:
            with open(f"icons/{channel_id}.jpg", "wb") as f:
                f.write(response.content)
            # Redimensiona para tamanho IPTV
            img = Image.open(f"icons/{channel_id}.jpg")
            img.thumbnail(size)
            img.save(f"icons/{channel_id}.png")
            return f"icons/{channel_id}.png"
    except Exception as e:
        print(f"Falha no ícone {channel_id}: {str(e)}")
    return None
