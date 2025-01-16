# Transformer-chromakey
Model weights, test video dataset and test markup you can download [here]()

# Usage

- Скачайте вышеупомянутые файлы и положите в папку chromakey.

- Находясь в корне репозитория, выполните следующее чтобы запустить скрипт нахождения хромакея в видео:

```
python paper_test.py -w ./last_model_4_seq_frames/best -v ./test_videos -m ./test_markup.txt
```

## Python packages
```
numpy==1.24.3
scipy==1.11.2
torch==1.13.1+cu117
torchvision==0.14.1+cu117
cv2==4.8.0.76
video_transformers==0.0.9
pywt==1.4.1
pytorchvideo==0.1.5
```

