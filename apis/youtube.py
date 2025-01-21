import sys
import json
import re
from youtube_search import YoutubeSearch
from pytubefix import YouTube as pytubeYouTube
from exceptions import YoutubeItemNotFound, ConfigVideoMaxLength, ConfigVideoLowViewCount

from dotenv import load_dotenv
import os

class YouTube:
    def __init__(self):
        dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../YOUTUBE_POTOKEN.env")
        
        load_dotenv(dotenv_path=dotenv_path)
        
        self.potoken = os.getenv('YOUTUBE_POTOKEN')
        
        if not self.potoken:
            raise ValueError(
                "YOUTUBE_POTOKEN not found in environment variables. "
                "Please ensure you create a YOUTUBE_POTOKEN.env file in the spotify2mp3 root directory in the following format: YOUTUBE_POTOKEN=POTOKENHERE (replace potokenhere with your potoken)"
            )

    def search(self, search_query, max_length, min_view_count, search_count=1):
        youtube_results = YoutubeSearch(search_query, max_results=search_count).to_json()

        if len(json.loads(youtube_results)['videos']) < 1:
            raise YoutubeItemNotFound('Skipped song -- Could not load from YouTube')

        youtube_videos = json.loads(youtube_results)['videos']
        videos_meta = []

        for video in youtube_videos:
            youtube_video_duration = video['duration'].split(':')
            youtube_video_duration_seconds = int(youtube_video_duration[0]) * 60 + int(youtube_video_duration[1])

            youtube_video_views = re.sub('[^0-9]', '', video['views'])
            youtube_video_viewcount_safe = int(youtube_video_views) if youtube_video_views.isdigit() else 0

            videos_meta.append((video, youtube_video_duration_seconds, youtube_video_viewcount_safe))

        sorted_videos = sorted(videos_meta, key=lambda vid: vid[2], reverse=True)
        chosen_video = sorted_videos[0]

        youtube_video_link = "https://www.youtube.com" + chosen_video[0]['url_suffix']

        if chosen_video[1] >= max_length:
            raise ConfigVideoMaxLength(f'Length {chosen_video[1]}s exceeds MAX_LENGTH value of {max_length}s [{youtube_video_link}]')

        if chosen_video[2] <= min_view_count:
            raise ConfigVideoLowViewCount(f'View count {chosen_video[2]} does not meet MIN_VIEW_COUNT value of {min_view_count} [{youtube_video_link}]')
    
        return youtube_video_link

    def download(self, url, audio_bitrate):
        youtube_video = pytubeYouTube(url)

        if youtube_video.age_restricted:
            youtube_video.bypass_age_gate()

        # Select best audio stream based on the provided bitrate
        audio_streams = youtube_video.streams.filter(only_audio=True).order_by('abr').desc()
        selected_stream = None

        for stream in audio_streams:
            abr_kbps = int(re.sub(r'\D', '', stream.abr))
            if abr_kbps <= audio_bitrate / 1000:
                selected_stream = stream
                break
        if not selected_stream:
            selected_stream = audio_streams.last()  # fallback to last (lowest bitrate if none match)

        yt_tmp_out = selected_stream.download(output_path="./temp/")
        
        return yt_tmp_out, int(selected_stream.abr.rstrip('kbps')) * 1000