# CNN-chromakey
weights - https://drive.google.com/drive/folders/1bWH4DC1T6RkY_wqR2iodjvWXQC6GXMnN

Содержит файлы.
- EfficientNetB0Transfer_pretrained_NonTriplet_Chromakey_14072023_3_epoch=17_best_metric_model.pth
- effnetb4.pth
- yolov8n-face.pt


# Instructions

- Скачайте вышеупомянутые файлы и положите в папку `chromakey`.

- Находясь в корне репозитория, выполните следующее чтобы собрать и запустить докер-образ:
 
**Для устройства с GPU:**
```shell
cd chromakey
docker build -t chromakey .
docker run -d --runtime=nvidia --shm-size=4g --memory=6g --restart=always -p 9022:9022 -t chromakey
```

Вместо `--runtime=nvidia` можно также использовать `--gpus all`, если основной вариант не работает. Тогда команда будет:
```
docker run -d --gpus all --shm-size=4g --memory=6g --restart=always -p 9022:9022 -t chromakey
```

NB:
> убедитесь что у вас установлены все драйвера и `nvidia-container-runtime`, являющийся частью `nvidia-cuda-toolkit` (`$docker info | grep -i runtime`)
> Если нет, см. https://stackoverflow.com/a/59008360/2877029 и https://catalog.ngc.nvidia.com/orgs/nvidia/containers/cuda

Ограничение RAM:
> Флаг `--memory=6g` позволяет ограничить общий объем оператвной памяти, доступной контейнеру указанным числом. При достижении указанного лимита контейнер перезагрузится. Рекомендуется выставлять значения от 6Gb до 16Gb. Данный параметр нужен чтобы ограничить возможные утечки памяти, возникающие от прерваных запросов.

**Для устройства с CPU:**
```shell
cd chromakey
docker build -f DockerfileCPU -t chromakey .
docker run -d --runtime=runc -p 9022:9022 -t chromakey
```
> `runc` - это ваш дефолтный докер рантайм. этот параметр можно опустить.

# Usage
В предпположении что сервис запущен по адресу и порту `localhost:9022`, а вашей текущей папке находится файл `123.mp4`, выполните:

```shell
curl --request POST --url http://localhost:9022/get-chromakey --header 'Content-Type: multipart/form-data' --form videoFile=@123.mp4

```

в ответе будет json следующего вида:
```json
{
  "result": [],
  "success": true
}
```


> Для запросов через графические промошники используйте content-type: multipart и имя параметра `videoFile`.


