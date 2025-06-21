import subprocess
import re
from PIL import Image  # Para redimensionar ícones

def fetch_multi_streams(channel_url, max_streams=3):
    try:
        output = subprocess.check_output(
            f"streamlink --stream-url {channel_url}",
            shell=True,
            stderr=subprocess.DEVNULL,
            text=True
        )
        streams = [line.split(" ")[0] for line in output.splitlines() 
                 if re.match(r'^\d+p', line)][:max_streams]
        
        return streams if streams else [output.strip()]
    except Exception:
        return None

# Exemplo de uso:
youtube_url = "https://youtube.com/@CNNbrasil"
stream_urls = fetch_multi_streams(youtube_url)

for i, url in enumerate(stream_urls, 1):
    stream_name = f"CNNbrasil_live{i}" if i > 1 else "CNNbrasil"
    add_to_playlist(url, stream_name, "News")
