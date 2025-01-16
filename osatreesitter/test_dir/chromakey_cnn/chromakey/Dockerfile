FROM nvidia/cuda:12.2.0-base-ubuntu20.04

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update -y
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y git python3-pip cmake

RUN pip3 install torch==1.12.1+cu113 torchvision==0.13.1+cu113 torchaudio==0.12.1 --extra-index-url https://download.pytorch.org/whl/cu113

COPY . /

WORKDIR .
RUN pip3 install -r ./requirements.txt
RUN pip3 uninstall -y opencv-contrib-python-headless opencv-python-headless opencv-python
RUN pip3 install opencv-python-headless

CMD ["python3", "./server.py"]
