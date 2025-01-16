import os

import requests

# Пример клиента вместе с запросом

root = 'croma_val' # Путь до папки с тестовыми видео в формате mp4


video_names = os.listdir(root)
for video_name in sorted(video_names):
    print(video_name)
    # Запрос
    res = requests.post(
        "http://109.188.135.85:9022/get-chromakey",
        files={'videoFile': open(f'{root}/{video_name}', 'rb')},
        # data=open(f'{root}/{video_name}', 'rb').read(),
    )
    print(res.text)
    print("=" * 20)
