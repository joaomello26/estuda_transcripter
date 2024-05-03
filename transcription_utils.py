import logging
import requests
import re
import whisper
import youtube_dl
import base64
from tqdm import tqdm
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def transcript_audio(filepath):
    model = whisper.load_model('tiny')

    result = model.transcribe(filepath)

    return result['text']

def audio_downloader(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    
    if 'youtube' in domain:
        return youtube_audio_downloader(url)
    elif 'vimeo' in domain:
        return vimeo_audio_downloader(url)
    else:
        logging.error(f'Unknow domain of: {url}')
        return

def youtube_audio_downloader(url):
    video_id = re.search(r'\?v=(.*)', url).group(1)
    filepath = f'audio_files\{video_id}.mp3'

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': filepath
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def get_m3u8_json(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'lxml')

    # Find the <script> tag containing 'window.playerConfig'
    script = soup.find('script', string=re.compile(r'window\.playerConfig'))

    if script:
        script_content = script.string

        # Get master JSON URL of m3u8
        match = re.search(r'"avc_url":"(.*?)"', script_content)
    else:
        logging.warning("Script containing 'window.playerConfig' not found")

    return match.group(1)

def vimeo_audio_downloader(url):
    master_json_url = get_m3u8_json(url)

    m3u8_id = re.search(r'exp=(.*?)~', master_json_url).group(1)
    filepath = f'audio_files\{m3u8_id}.mp3'

    base_url = master_json_url[:master_json_url.rfind('/')].rstrip("/")

    resp = requests.get(master_json_url)
    resp_json = resp.json()

    for item in resp_json["base_url"].split("/"):
        if item == "..":
            base_url = base_url[:base_url.rfind("/")]
        else:
            base_url += "/" + item.rstrip("/")

    base_url = base_url.rstrip("/")

    # Filter videos without audio track
    video_audio_map = {
        video["id"]: {"video": video}
        for video in resp_json["video"]
    }
    for audio in resp_json["audio"]:
        if audio["id"] in video_audio_map:
            video_audio_map[audio["id"]]["audio"] = audio

    # Sort videos by quality
    sorted_video_audio = sorted(
        [
            (video_id, video_audio) for video_id, video_audio in video_audio_map.items()
            if "video" in video_audio and "audio" in video_audio
        ],
        key=lambda video_audio: video_audio[1]["video"]["height"],
        reverse=True,
    )
        
    # Download video with the best quality
    video_audio = sorted_video_audio[-1]
    download_vimeo_audio(video_audio[1]["audio"], base_url, filepath)

    return filepath

def download_vimeo_audio(content, segment_base_url, filepath):
    for url_part in content["base_url"].split("/"):
        if url_part == "..":
            segment_base_url = segment_base_url[:segment_base_url.rfind("/")]
        else:
            segment_base_url += "/" + url_part.rstrip("/")

    with open(filepath, mode="wb") as content_file:
        init_segment = base64.b64decode(content['init_segment'])
        content_file.write(init_segment)

        for segment in tqdm(content['segments']):
            segment_url = segment_base_url + "/" + segment['url']

            while True:
                try:
                    resp = requests.get(segment_url, stream=True)
                    if resp.status_code != 200:
                        logging.warning(f'not 200! {segment_url} - {resp} ')
                        continue
                    for chunk in resp:
                        content_file.write(chunk)
                except requests.exceptions.RequestException:
                    continue
                break

