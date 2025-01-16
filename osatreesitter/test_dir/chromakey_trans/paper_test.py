from video_transformers import VideoModel
import cv2
import numpy as np
import os
from scipy import signal
import re
import pywt
import torch
import argparse
from pytorchvideo.transforms import (
    ApplyTransformToKey,
    Normalize,
    ShortSideScale,
    UniformTemporalSubsample,
)
from torch.utils.data import DataLoader
from torchvision.transforms import CenterCrop, Compose, Lambda

def normalize_func(x):
    '''
    Convert uint8 images to float32 images.
    '''
    return x / 255.0
    
def get_test_transforms(num_timesteps = 32,
                      mean = [0.485, 0.456, 0.406],
                      std = [0.229, 0.224, 0.225],
                      input_size=224,
                      min_short_side=256):

    '''
    Apply the neccessary transformations to images.
    '''

    
    test_video_transform = Compose(
        [
            UniformTemporalSubsample(num_timesteps),
            Lambda(normalize_func),
            Normalize(mean, std),
            ShortSideScale(min_short_side),
            CenterCrop(input_size),
        ]
    )
    test_transform = ApplyTransformToKey(key="video", transform=test_video_transform)
    return test_transform

def MAD(img, kernel = 8, sf = 1.4826):
    '''
    Calculate block-wise Median Absolute Deviation of diagonal component of 2d
    discrete wavelet trasnform divided on blocks.
    '''

    H, _ = img.shape
    blocked_img = (img.reshape(H//kernel, kernel, -1, kernel).swapaxes(1,2).reshape(-1, kernel, kernel))
    median = np.median(blocked_img, axis=(2,1))
    return blocked_img, sf * median
    
def envelope(img_block):
    '''
    Calculate the lower and upper envelope.
    '''

    mean_val = img_block.mean()
    img_block_centered = img_block - mean_val
    hilbert_filt = np.abs(signal.hilbert(img_block_centered, axis=1))
    return hilbert_filt+mean_val, hilbert_filt-mean_val

def pre_processing(img, wr = 0.299, wb = 0.114):
    '''
    Convert image from RGB color space to YCbCr color space.
    '''

    B, G, R = cv2.split(img)
    Y = wr*R + (1 - wb - wr)*G + wb*B
    return Y

def noise_estimation(preprocessed_img):
    '''
    Apply 2d discrete wavelet trasnform to image,
    calculate median absolute deviation for its 
    diagonal component and lower envelope for each
    of block of resulted image. Then, subtract lower envelope
    and mad to reduce the noise impact of complex contours.
    '''

    coeffs2 = pywt.dwt2(preprocessed_img, 'db4')
    _, (_, _, D) = coeffs2
    
    blocked_img, mad = MAD(D)
    
    for idx, block in enumerate(blocked_img):
        _, LE = envelope(block)
        blocked_img[idx] = LE - mad[idx]

    return blocked_img

def get_img_from_blocks(blocked_img, res=256, kernel = 8):
    '''
    Merge blocks to create image.
    '''

    blocked_img = np.reshape(blocked_img,(res//kernel,res//kernel,kernel,kernel))
    blocked_img = np.transpose(blocked_img,(1,0,2,3))
    blocked_img = np.concatenate(blocked_img,axis=1)
    blocked_img = np.transpose(blocked_img,(0,2,1))
    blocked_img = np.concatenate(blocked_img, axis=0)
    return (blocked_img*255).astype(np.uint8)

def extract_markup(file_name):
    '''
    Extract test markup from .txt file.
    '''

    markup = []
    with open(file_name,'r') as f:
        for line in f.readlines():
            markup.append(line.strip().split(" ", 1)[1])

    return markup

def get_true_markup_in_seconds(our_markup):
    '''
    Markup conversion into second ranges
    '''

    ranges = []
    for video_markup in our_markup:
        our_labels = video_markup.replace(" ", "").split(",")
        for label in our_labels:
            range = []
            label = label.split("-")
            for i in label:
                seconds = 60 * int(i[0]) + 10 * int(i[2]) + int(i[3])
                range.append(seconds)
            ranges.append(range)

    return ranges

def median(int_seq):
    '''
    Calculate median of array.
    '''

    int_seq.sort()
    if len(int_seq) % 2 != 0:
        return int_seq[len(int_seq) // 2]
    else:
        return sum(int_seq) / 2

def generate_ranges(model, videos_path, markup_path, seq_len, batch_size):
    '''
    Process input videos, look for chromakey and generate ranges.
    '''

    video_list = sorted(os.listdir(videos_path), key=lambda s: int(re.search(r'\d+', s).group()))
    test_markup = extract_markup(markup_path)
    test_transforms = get_test_transforms(num_timesteps=seq_len)
    TP = 0
    FP = 0
    TN_plus_TP = 0

    for idx, video_name in enumerate(video_list):
        video_capture = cv2.VideoCapture(videos_path+"/"+video_name)
        input_fps = int(video_capture.get(cv2.CAP_PROP_FPS))
        fps_ration = seq_len / input_fps
        video_frames = []
        test_dataset = []
        true_markup_in_seconds = get_true_markup_in_seconds([test_markup[idx]])
        TN_plus_TP += sum([int(i[1])-int(i[0]) for i in true_markup_in_seconds])
        our_markup = []

        while True:
            ret, frame = video_capture.read()
            if not ret: 
                video_capture.release()
                break

            frame = frame.astype(np.float32)/255
            frame = cv2.resize(frame, (506,506))
            frame = pre_processing(frame)
            frame = noise_estimation(frame)
            frame = get_img_from_blocks(frame)
            frame = cv2.normalize(frame, None, 255, 0, cv2.NORM_MINMAX, cv2.CV_8U)
            frame = cv2.applyColorMap(frame, cv2.COLORMAP_TURBO)
            frame = cv2.resize(frame,(320, 240))
            video_frames.append(frame)

        if len(video_frames)%seq_len!=0:
            add_arrs = np.zeros((seq_len-len(video_frames)%seq_len, 240, 320, 3)).astype(np.uint8)
            video_frames = np.concatenate((video_frames,add_arrs), axis=0).astype(np.uint8)

        test_samples = np.array(np.split(np.array(video_frames), len(video_frames)//seq_len))
        for i in range(len(test_samples)):
            test_dataset.append(test_transforms({"video": torch.tensor(test_samples[i]).permute(3,0,1,2)}))

        test_dataset = DataLoader(test_dataset, batch_size=batch_size, num_workers=0, drop_last=False)
        res = []
        for i in test_dataset:
            output = model(i["video"].to(device))
            output = torch.nn.functional.softmax(output, dim=1).argmax(dim=-1)
            for j in range(len(output)):
                res.append(output[j].item())

        i = 0
        while i<len(res):
            if res[i]!=0:
                j = i
                while j<len(res) and res[j]==res[i]:
                    j+=1
                
                if res[i]==1:
                    our_markup.append([int(fps_ration*i), int(fps_ration*j)])
                i = j
            else:
                i+=1

        for i in range(len(our_markup)):
            our_markup_sample = our_markup[i]
            for j in range(len(true_markup_in_seconds)):
                true_markup_in_seconds_sample = true_markup_in_seconds[j]
                if (our_markup_sample[0] <= true_markup_in_seconds_sample[1]) and (our_markup_sample[1] >= true_markup_in_seconds_sample[0]):
                    intersection = median([true_markup_in_seconds_sample[0], true_markup_in_seconds_sample[1] + 1, our_markup_sample[1] + 1]) - \
                            median([true_markup_in_seconds_sample[0], true_markup_in_seconds_sample[1] + 1, our_markup_sample[0]]) - 1
                    
                    TP += intersection
                    FP += (int(our_markup_sample[1])-int(our_markup_sample[0])) - intersection
                    break

    print("------------------------")
    print("TP: ",TP)
    print("FP: ",FP)
    print("TN_plus_TP: ",TN_plus_TP)

    precision = TP / (TP + FP)
    recall = TP / TN_plus_TP
    f1 = 2 * precision * recall / (precision + recall)

    print("precision: ",precision)
    print("recall: ",recall)
    print("f1: ",f1)


if __name__ == "__main__":
    # parse arguments 
    parser = argparse.ArgumentParser()
    parser.add_argument("-w", dest = "model_weights", help = "path to model weights", required = True, type = str)
    parser.add_argument("-v", dest = "test_videos", help = "path to test videos", required = True, type = str)
    parser.add_argument("-m", dest = "test_markup", help = "path to test markup", required = True, type = str)
    parser.add_argument("-l", dest = "seq_len", help = "sequence length", default = 4, type = int)
    parser.add_argument("-b", dest = "bs", help = "batch size", default = 128, type = int)
    args = parser.parse_args()

    # initialize device and model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = VideoModel.from_pretrained(args.model_weights).eval().to(device)

    # run function, which creates ranges
    generate_ranges(model, args.test_videos, args.test_markup, args.seq_len, args.bs)