import collections
import os
import time
from uuid import uuid4

import cv2
import numpy as np
import torch
import torchvision.transforms as T
import yaml
from PIL import Image
from flask import Flask, request
from tqdm import tqdm
from ultralytics import YOLO

from df_utils import crop_face, get_transformer, get_extended_bbox
from fornet import EfficientNetB4
from model import EfficientNetB0

# Режим работы с отладкой или без нее, в режиме отладки будут логи и сохранения некоторых важных промежуточных результатов
DEBUG = False
if DEBUG:
    debug_time = time.time()
    print("DEBUG TIME:", debug_time)
    OUT_DEBUG_FOLDER = f'chromakey_server_debug_out_{debug_time}'
    os.makedirs(OUT_DEBUG_FOLDER, exist_ok=True)

UPLOAD_FOLDER = './'

# Считывание из yaml файла, ожидается на вход:
# chromakey_threshold - процент кадров необходимых для того, чтобы считать, что секунда содержит хромакей
# ckpt_path - путь до весов модели
# window_size - сколько секунд подряд мы будем считать хромакеем
# use_deepfake_predictors - режим работы алгоритма, определяет будут ли учитываться результаты модели для дипфейков
with open("config.yaml", 'r') as config:
    data_loaded = yaml.safe_load(config)
    PERCENT = data_loaded['chromakey_threshold']
    CKPT_PATH = data_loaded['ckpt_path']
    WINDOW = data_loaded['window_size']
    USE_DEEPFAKE_PREDICTORS = data_loaded['use_deepfake_predictors']
    BATCH_SIZE = data_loaded['batch_size']
# Размер до которого необходимо ресайзнуть изображения для работы модели
USED_IMG_SIZE = 224

app = Flask(__name__)
app.secret_key = 'super secret key'
app.config['SESSION_TYPE'] = 'filesystem'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")
print("chromakey_threshold:", PERCENT)
print("CKPT_PATH:", CKPT_PATH)
print("WINDOW:", WINDOW)
print("USE_DEEPFAKE_PREDICTORS:", USE_DEEPFAKE_PREDICTORS)
print("BATCH_SIZE:", BATCH_SIZE)
print("USED_IMG_SIZE:", USED_IMG_SIZE)

# Для работы алгоритма определения дипфейков, в качестве модели для детекции лиц используется yolov8
if USE_DEEPFAKE_PREDICTORS:
    print("Creating deepfake predictors...")
    face_detector_model = YOLO('yolov8n-face.pt')
    face_detector_model.to(device)

    deepfake_scorer = EfficientNetB4()
    deepfake_scorer.load_state_dict(torch.load('effnetb4.pth', map_location=device)['net'])
    deepfake_scorer.to(device).eval()
    deepfake_threshold = 0.68
    deepfake_image_size = 380
    df_face_transform = get_transformer('scale', deepfake_image_size, deepfake_scorer.get_normalizer())

# Инициализация модели для распознавания хромакея
chromakey_classifier = EfficientNetB0(num_classes=2, pretrained=False, freeze_layers=True)
chromakey_classifier.load_state_dict(torch.load(CKPT_PATH, map_location=device))
chromakey_classifier.to(device)
chromakey_classifier.eval()

# Вспомогательная функция для преобразования изображения в формате pillow в обычный тензор
def pil_to_tensor(pil_img):
    data_transformation = T.Compose([
        T.Resize((USED_IMG_SIZE, USED_IMG_SIZE)),
        T.ToTensor(),
    ])
    img_transformed = data_transformation(pil_img)
    return img_transformed

# Функция получения разностного кадра
def get_diff_frame(frame_first, frame_second):
    fp = cv2.subtract(frame_first, frame_second)
    fq = cv2.subtract(frame_second, frame_first)
    fd = cv2.add(fp, fq)
    gray_diff = cv2.cvtColor(fd, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray_diff, 100, 200)

    new_edges = edges / 255
    new_gray_diff = new_edges * gray_diff
    return Image.fromarray(new_gray_diff).convert('L')

# Функция для проверки работоспособности сервера
@app.route('/health', methods=['GET'])
def health():
    return {"success": True}

# Основная функция запроса
@app.route('/get-chromakey', methods=['POST'])
def get_chromakey():
    torch.cuda.empty_cache()
    start_time = time.time()
    print("=" * 20)
    print("--- Starting get chromakey method...")
    print("--- Processing video receiving...")
    print(request.files)
    # Получение мета информации о видео
    video_receiving_end_time = time.time()
    video_receiving_time = video_receiving_end_time - start_time
    file = request.files['videoFile']
    filename = file.filename
    print(f'--- Video receiving ended in {video_receiving_time:.5f} seconds')
    print(f'--- Processing input file: `{filename}`...')

    tmp_video_filename = os.path.join('.', uuid4().hex)
    with open(tmp_video_filename, "wb") as out_file:
        out_file.write(file.stream.read())
    input_video_size = os.path.getsize(tmp_video_filename)
    # Используем VideoCapture для разбиения видео пофреймово
    video_cap = cv2.VideoCapture(tmp_video_filename)
    fps = video_cap.get(cv2.CAP_PROP_FPS)
    fps = int(fps)

    method_running_start_time = time.time()
    # Получение интервалов, в котором замечена технология хромакей
    list_intervals, total_frames = get_chromo_intervals(video_cap, PERCENT, fps, start=0, stop=1000)
    os.remove(tmp_video_filename)

    end_time = time.time()
    total_time = end_time - start_time
    # Вывод логов
    print(f'--- Total video size: {input_video_size / 1024:.2f}KB')
    print(f"--- Processed {total_frames} frames "
          f"in {total_time :.5f} seconds "
          f"({total_frames / total_time:.4f} FPS)")
    total_time_without_video_receiving = end_time - method_running_start_time
    print(f"--- Time without video receiving: {total_time_without_video_receiving:.5f} "
          f"({total_frames / total_time_without_video_receiving:.4f} FPS)")
    return {"success": True, 'result': list_intervals}

# Функция для выявления интервалов с хромакеем
def get_chromo_intervals(video_cap, percent, fps, start, stop):
    list_res = []

    faces_step_dilation = 3
    total_frame_ind = 0
    used_frame_ind = 0
    prev_img = None
    cur_boxes_in_diffs_to_remove = []
    triplet_size = 3
    cur_diffs = collections.deque(maxlen=triplet_size)
    print(f"Processing triplets with batch size: {BATCH_SIZE}...")
    progress_bar = tqdm()
    batch_ind = 0
    # Разбиение видео на разностные кадры и формирование батчей для оптимизации кода на гпу
    while True:
        cur_batched_triplet_diffs_images = []
        while len(cur_batched_triplet_diffs_images) < BATCH_SIZE:
            show_dict = {'Batch index': f'{batch_ind}',
                         'Cur frame index': f'{total_frame_ind}',
                         'Used frames': f'{used_frame_ind}'}
            progress_bar.set_postfix(show_dict)
            progress_bar.update(total_frame_ind)

            success, cur_image = video_cap.read()
            if not success:
                break
            # Функция допускает проверку только конкретных временных промежутков на наличие хромакея.
            # На данный момент оценивается все видео
            if start * fps <= total_frame_ind <= stop * fps:
                if prev_img is not None:
                    # Получение разностного кадра
                    diff_frame = get_diff_frame(prev_img, cur_image)
                    diff_frame = np.asarray(diff_frame)
                    # В случае отладки сохраняем разностные кадры
                    if DEBUG:
                        out_dir = f'{OUT_DEBUG_FOLDER}/diff_frames'
                        os.makedirs(out_dir, exist_ok=True)
                        cv2.imwrite(f'{out_dir}/{total_frame_ind}_{used_frame_ind}_orig_diff.jpg', diff_frame)
                    # В случае использования модели для детекции дипфейков, Удаляются все лица,
                    # которые были классифицированы как фейк
                    if USE_DEEPFAKE_PREDICTORS and used_frame_ind % faces_step_dilation == 0:
                        cur_boxes_in_diffs_to_remove = []
                        res = face_detector_model.predict(source=cur_image,
                                                          show=False,
                                                          save=False,
                                                          conf=0.4,
                                                          save_txt=False,
                                                          save_crop=False,
                                                          verbose=False,
                                                          device=device,
                                                          half=True,
                                                          )[0]
                        boxes_cnt = len(res.boxes)
                        for ind in range(boxes_cnt):
                            box_points = res.boxes.xyxy[ind].detach().cpu().numpy().astype(int)
                            landmarks = res.keypoints[ind].data.detach().cpu().numpy()[0][:, :2].astype(int)
                            # remove faces in profile: if nose landmark is to the right or to the left from eyes and lips
                            nose_is_left = (landmarks[2] >= landmarks)[:, 0].sum()
                            nose_is_right = (landmarks[2] <= landmarks)[:, 0].sum()
                            if nose_is_left > 3 or nose_is_right > 3:
                                continue
                            face = crop_face(res.orig_img, box_points)
                            tensor_face = df_face_transform(image=face)['image'][None, :]
                            batch = tensor_face.to(device)
                            score = deepfake_scorer(batch)[0]
                            df_score = torch.sigmoid(score)
                            if DEBUG:
                                out_dir = f'{OUT_DEBUG_FOLDER}/cropped_faces'
                                os.makedirs(out_dir, exist_ok=True)
                                cv2.imwrite(
                                    f'{out_dir}/{total_frame_ind}_{used_frame_ind}_{ind}_{df_score.cpu().item():.4f}.jpg',
                                    face)
                            if df_score > deepfake_threshold:
                                cur_boxes_in_diffs_to_remove.append(box_points)
                    for box_ind, box_points in enumerate(cur_boxes_in_diffs_to_remove):
                        x1, y1, x2, y2 = get_extended_bbox(box_points, 5)
                        cv2.rectangle(diff_frame, (x1, y1), (x2, y2), (0, 0, 0), -1)
                        if DEBUG:
                            out_dir = f'{OUT_DEBUG_FOLDER}/diff_frames'
                            os.makedirs(out_dir, exist_ok=True)
                            cv2.imwrite(f'{out_dir}/{total_frame_ind}_{used_frame_ind}_diff_removed_{box_ind}.jpg',
                                        diff_frame)
                    cur_resized_diff_frame = Image.fromarray(diff_frame).resize((USED_IMG_SIZE, USED_IMG_SIZE))
                    cur_diffs.append(cur_resized_diff_frame)
                    used_frame_ind += 1
                prev_img = cur_image
                # После получения разностных кадров, идет процесс обьединения их в тройки
                if len(cur_diffs) == triplet_size:
                    pil_img = Image.merge('RGB', tuple(cur_diffs))
                    cur_batched_triplet_diffs_images.append(pil_to_tensor(pil_img))
            total_frame_ind += 1
        batch_ind += 1
        if len(cur_batched_triplet_diffs_images) == 0:
            break
        classify_triplet_images(cur_batched_triplet_diffs_images, list_res)
    # Далее идет преобразование получившихся меток в последовательные интервалы
    count_false = 0
    list_counts_ps = []
    for i in range(len(list_res)):
        if not list_res[i]:
            count_false += 1
        if i % fps == 0:
            list_counts_ps.append(count_false)
            count_false = 0
    prev = -1
    cur_sum = 0
    all_count = 0
    answer = []
    list_counts_ps.append(0)
    # На последнем этапе отсеиваются те секунды в которых слишком мало подозрительных кадров,
    # а так же интервалы подозрительных секунд, недостаточной длины
    for i in range(len(list_counts_ps)):
        if list_counts_ps[i] / fps * 100 >= percent:
            cur_sum += list_counts_ps[i]
            all_count += fps
            if prev == -1:
                prev = i
        else:
            if prev != -1:
                if i - prev >= WINDOW:
                    answer.append({'start': start + prev, 'stop': start + i, 'score': (cur_sum / all_count)})
                prev = -1
                cur_sum = 0
                all_count = 0
    # Возвращение результатов
    return answer, total_frame_ind

# Функция классификации батча состоящего из обьединенных разностных кадров
@torch.no_grad()
def classify_triplet_images(cur_batched_triplet_images, list_res):
    batch = torch.stack(cur_batched_triplet_images).to(device)
    results = chromakey_classifier(batch)
    inds = results.argmax(dim=1)
    for ans in inds:
        value = int(ans)
        if value == 0:
            res = False
        else:
            res = True
        list_res.append(res)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9023, debug=False)
