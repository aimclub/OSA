# Documentation for cnn+transformer.py

# Documentation for focal_loss.py

## Class: FocalLoss

""" Focal Loss, as described in https://arxiv.org/abs/1708.02002.

    It is essentially an enhancement to cross entropy loss and is
    useful for classification tasks when there is a large class imbalance.
    x is expected to contain raw, unnormalized scores for each class.
    y is expected to contain class labels.

    Shape:
        - x: (batch_size, C) or (batch_size, C, d1, d2, ..., dK), K > 0.
        - y: (batch_size,) or (batch_size, d1, d2, ..., dK), K > 0.
    """

### Method: __init__

Error generating documentation: Connection error.

### Method: __repr__

## Documentation

### Method Name: 
`__repr__`

### Arguments: 

- `self`: This is the standard instance object that is automatically passed in as the first argument when you call a method on an object.

### Return Type: 
`String`: This method returns a string representation of the object that can ideally be used to recreate the object using the `eval()` function. 

### High-Level Explanation: 

The `__repr__` method is a built-in Python method that is used to specify a string representation of an object. This method is automatically called by built-in functions and operators that require a string for the object. In this case, the `__repr__` method is returning a string that represents the state of the object, with the object's class name and the values of its 'alpha', 'gamma', 'ignore_index', and 'reduction' attributes.

### Source Code:

```python
def __repr__(self):
    arg_keys = ['alpha', 'gamma', 'ignore_index', 'reduction']
    arg_vals = [self.__dict__[k] for k in arg_keys]
    arg_strs = [f'{k}={v!r}' for k, v in zip(arg_keys, arg_vals)]
    arg_str = ', '.join(arg_strs)
    return f'{type(self).__name__}({arg_str})'
```

In the source code:

1. `arg_keys` is a list of the keys that we want to include in the string representation.
2. `arg_vals` is a list comprehension that gets the values of the keys in `arg_keys` from the object's dictionary (`__dict__`).
3. `arg_strs` is another list comprehension that creates a list of strings, with each string being a key-value pair in the format 'key=value'.
4. `arg_str` is a string that joins all the strings in `arg_strs` together, separated by commas.
5. Finally, the method returns a string that includes the object's class name and the `arg_str`, all enclosed in parentheses. The `!r` format specifier is used in the string format method to get the `__repr__` of `v` (the value of each argument).

### Method: forward

# Documentation for Python Method - `forward`

## Method Name: 
`forward`

## Arguments:

- `self`: This is a conventional argument in Python which refers to the instance of the class where this method is being called.

- `x` (Tensor): A multidimensional array (Tensor) which contains the input data. The dimensions can be more than 2.

- `y` (Tensor): A multidimensional array (Tensor) which contains the target data. The dimensions of this tensor should match with `x`.

## Return Type:

- `Tensor`: This method returns a Tensor which represents the computed loss. The purpose of this loss tensor is to provide a scalar quantity that the model's optimizer can use to update the model's parameters. The loss tensor can be a single scalar (if reduction is 'mean' or 'sum') or a tensor of losses for each input (if reduction is 'none').

## High-Level Explanation:

The `forward` method computes the weighted focal loss for input tensors `x` and `y`. 

First, the method reshapes the input tensors if they have more than 2 dimensions. Then it identifies and removes ignored indexes in `y` (and corresponding entries in `x`). 

Next, it computes the log softmax of `x` and uses it to compute the weighted cross entropy term. It then computes the true class log probability and uses it to compute the focal term and the full loss. 

Finally, it applies reduction to the loss if specified (mean or sum) and returns the loss.

## Source Code:

```python
def forward(self, x: Tensor, y: Tensor) -> Tensor:
    if x.ndim > 2:
        # (N, C, d1, d2, ..., dK) --> (N * d1 * ... * dK, C)
        c = x.shape[1]
        x = x.permute(0, *range(2, x.ndim), 1).reshape(-1, c)
        # (N, d1, d2, ..., dK) --> (N * d1 * ... * dK,)
        y = y.view(-1)

    unignored_mask = y != self.ignore_index
    y = y[unignored_mask]
    if len(y) == 0:
        return torch.tensor(0.)
    x = x[unignored_mask]

    # compute weighted cross entropy term: -alpha * log(pt)
    # (alpha is already part of self.nll_loss)
    log_p = F.log_softmax(x, dim=-1)
    ce = self.nll_loss(log_p, y)

    # get true class column from each row
    all_rows = torch.arange(len(x))
    log_pt = log_p[all_rows, y]

    # compute focal term: (1 - pt)^gamma
    pt = log_pt.exp()
    focal_term = (1 - pt)**self.gamma

    # the full loss: -alpha * ((1 - pt)^gamma) * log(pt)
    loss = focal_term * ce

    if self.reduction == 'mean':
        loss = loss.mean()
    elif self.reduction == 'sum':
        loss = loss.sum()

    return loss
```


# Documentation for paper_test.py

## Standalone Functions

### Function: normalize_func

# Documentation for the Python method `normalize_func`

## Method Name

`normalize_func`

## Arguments

This method accepts a single argument:

- `x`: It represents the image data that needs to be normalized. This input is expected to be in the uint8 format, which means the pixel values of the image are between 0 and 255.

## Return Type

The return type of this function is `float32`. 

## Purpose of the Return Type

This return type is chosen because the purpose of this function is to normalize the uint8 image data (where the pixel values range from 0 to 255) to a float32 format where the pixel values range from 0.0 to 1.0. Using float32 allows us to preserve the decimal values resulting from the division operation in the function, which is important for maintaining the detail of the image.

## High-Level Explanation

The `normalize_func` method is used to normalize image data. Normalizing image data is a common preprocessing step in many image processing tasks and machine learning algorithms. It helps to reduce the range of pixel values, which can improve computational efficiency and the performance of certain algorithms.

In this case, the method is specifically designed to normalize images that are in the uint8 format. The uint8 format is a common format for images, where each pixel value is an 8-bit integer between 0 (black) and 255 (white). The method converts these pixel values to a float32 format, where the values are floating point numbers between 0.0 and 1.0.

## Source Code

```python
def normalize_func(x):
    '''
    Convert uint8 images to float32 images.
    '''
    return x / 255.0
```

In the source code, the normalization is done by dividing the input `x` by 255.0. This operation is vectorized, meaning it can be applied to an entire numpy array at once, so `x` can represent a whole image or even a batch of images. The division by 255.0 scales the pixel values down to the range [0.0, 1.0], effectively converting the image data to float32 format.

## Standalone Functions

### Function: get_test_transforms

## Python Method Documentation: `get_test_transforms`

### Method Name
`get_test_transforms`

### Arguments
This method takes the following arguments:
1. `num_timesteps`: This argument defaults to `32` and determines the number of uniform timesteps to which the video will be subsampled.
2. `mean`: A list of three float values, defaulting to `[0.485, 0.456, 0.406]`. It represents the mean values used for the normalization of the images.
3. `std`: A list of three float values, defaulting to `[0.229, 0.224, 0.225]`. It represents the standard deviation values used for the normalization of the images.
4. `input_size`: An integer that defaults to `224` and represents the size to which the image will be cropped.
5. `min_short_side`: An integer that defaults to `256` and determines the minimum short side of the image.

### Return Type
This method returns a `test_transform` object. This object is used to apply the specified transformations to the videos.

### High-Level Explanation
The `get_test_transforms` method applies a series of transformations to videos. These transformations include uniform temporal subsampling, normalization, scaling of the short side of the image, and center cropping. The method creates a `test_transform` object by applying the transformations to a key named "video". The returned `test_transform` object can then be used to apply these transformations to other videos.

### Source Code
```python
def get_test_transforms(num_timesteps = 32,
                      mean = [0.485, 0.456, 0.406],
                      std = [0.229, 0.224, 0.225],
                      input_size=224,
                      min_short_side=256):

    '''
    Apply the necessary transformations to images.
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
```

## Standalone Functions

### Function: MAD

## Documentation

### Method Name
`MAD`

### Arguments
- `img`: An input image for which the block-wise Median Absolute Deviation of the diagonal component of the 2D discrete wavelet transform divided on blocks will be calculated. It should be a 2D array-like object.
- `kernel`: An optional argument, default value is 8. It defines the size of the block for which the computation is performed.
- `sf`: An optional argument, default value is 1.4826. It is a scaling factor, used to scale the computed median.

### Return Type
This method returns a tuple of two numpy arrays. The first numpy array is the blocked image, reshaped according to the kernel size, and the second numpy array is a scaled median value of each block.

### Method Description
The `MAD` method calculates the block-wise Median Absolute Deviation of the diagonal component of a 2D discrete wavelet transform divided on blocks. In the first step, the method reshapes the input image into blocks of size defined by the `kernel` argument. Then, it calculates the median of each block. The median is then scaled by the `sf` argument value. The method returns the blocked image and the scaled median.

### Source Code

```python
def MAD(img, kernel = 8, sf = 1.4826):
    '''
    Calculate block-wise Median Absolute Deviation of diagonal component of 2d
    discrete wavelet trasnform divided on blocks.
    '''

    H, _ = img.shape
    blocked_img = (img.reshape(H//kernel, kernel, -1, kernel).swapaxes(1,2).reshape(-1, kernel, kernel))
    median = np.median(blocked_img, axis=(2,1))
    return blocked_img, sf * median
```


## Standalone Functions

### Function: envelope

# Documentation

## Method Name:
`envelope`

## Arguments:
`img_block`: This is the only argument to the `envelope` function. It is expected to be a two-dimensional numpy array representing an image block.

## Return Type:
The `envelope` function returns a tuple of two numpy arrays. These arrays are the calculated lower and upper envelopes of the input image block.

## High-Level Explanation:
The `envelope` function calculates the lower and upper envelope of a given image block. 

The process follows these steps:
1. It first calculates the mean of the image block array.
2. Then it subtracts the calculated mean value from the image block to center the values around zero. This centered image block is subsequently used for the Hilbert transformation.
3. The Hilbert transform is then applied to the centered image block array. The absolute values of the Hilbert transform output are computed to create the Hilbert envelope.
4. Finally, the function returns a tuple of two arrays: the upper envelope (calculated as the Hilbert envelope plus the mean value) and the lower envelope (calculated as the Hilbert envelope minus the mean value).

## Source Code:
```python
def envelope(img_block):
    '''
    Calculate the lower and upper envelope.
    '''

    mean_val = img_block.mean()
    img_block_centered = img_block - mean_val
    hilbert_filt = np.abs(signal.hilbert(img_block_centered, axis=1))
    return hilbert_filt+mean_val, hilbert_filt-mean_val
```

## Note:
This function uses the `numpy` library for array operations and the `scipy.signal` library for the Hilbert transformation. Please ensure these libraries are installed and properly imported before using this function.

## Standalone Functions

### Function: pre_processing

# Method Documentation

## Method Name
`pre_processing`

## Arguments

- `img` : This is an image that needs to be converted from RGB color space to YCbCr color space. This is a required argument.
- `wr` : This is a constant used in the conversion formula. Its default value is `0.299`.
- `wb` : This is also a constant used in the conversion formula. Its default value is `0.114`.

## Return Type
The return type of this method is a `numpy array` which represents the image in Y channel of YCbCr color space.

## Purpose of Return Type
The purpose of the return type is to provide the converted image after the conversion from RGB to YCbCr.

## High-Level Explanation
This method performs color space conversion for an image. It takes an image in RGB color space as input and converts it to the YCbCr color space. The conversion is performed using the specified constants `wr` and `wb`. The Y channel of the YCbCr color space is then returned.

## Source Code

```python
def pre_processing(img, wr = 0.299, wb = 0.114):
    '''
    Convert image from RGB color space to YCbCr color space.
    '''

    B, G, R = cv2.split(img)
    Y = wr*R + (1 - wb - wr)*G + wb*B
    return Y
```

In the above source code, cv2.split function splits the image into three channels Blue, Green, and Red. These channels are then used in the YCbCr conversion formula to find the Y channel. This Y channel is then returned by the function.

## Standalone Functions

### Function: noise_estimation

# Documentation

## Method Name: `noise_estimation`

### Arguments:

- `preprocessed_img`: This is the only argument to this method. It should be a preprocessed image.

### Return Type: 

- This method returns a processed image after applying noise estimation techniques. The return type is an array equivalent to the processed image. 

### High-Level Explanation:

The `noise_estimation` method applies a 2D discrete wavelet transform to a preprocessed image. It calculates the median absolute deviation (MAD) for the diagonal component of the image and finds the lower envelope for each block of the image resulting from the transform.

The method then subtracts the lower envelope and MAD from each block to reduce the noise impact of complex contours on the image. This process can help in enhancing the quality of the image by reducing noise.

### Source Code:

```python
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
```

Please note that this method relies on external functions like `MAD` and `envelope` which are not defined in this snippet. Make sure these functions are correctly defined and imported in your script where you plan to use this method.

## Standalone Functions

### Function: get_img_from_blocks

## Documentation for `get_img_from_blocks` Python Method

### Method Name
`get_img_from_blocks`

### Arguments
This method accepts two arguments:

1. `blocked_img` - This is a numpy array. It represents the image that needs to be unblocked or reshaped. The method assumes that the incoming image is blocked or divided into smaller parts, and this argument serves the purpose of supplying that blocked image data.

2. `res` - This is an optional integer argument with a default value of 256. It represents the resolution of the resulting image after unblocking.

3. `kernel` - This is another optional integer argument with a default value of 8, which represents the size of the blocks in the blocked image.

### Return Type
This method returns a numpy array of type `np.uint8`. The returned array is an unblocked or reshaped version of the input blocked image, where the pixel values have been scaled up by a factor of 255.

### High-Level Explanation
This method essentially reverses the process of blocking an image. It takes a blocked image as input, reshapes it back to its original form, and returns the resulting image. The method utilizes numpy functions such as `reshape`, `transpose`, and `concatenate` to perform this operation. 

### Source Code
```python
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
```
This method first reshapes the blocked image based on the provided resolution and kernel size, then transposes and concatenates the reshaped blocks to create the final unblocked image. The pixel values are then scaled up by a factor of 255 and converted to `np.uint8` type before returning.

## Standalone Functions

### Function: extract_markup

## Documentation for `extract_markup` method

### Method Name
`extract_markup`

### Arguments
This method accepts one argument: 

- `file_name` (str): The name of the .txt file from which the markup needs to be extracted.

### Return Type
The return type of this method is a list (`list`). 

This method returns a list of strings (`markup`). Each string in this list represents a line from the input file, stripped of leading and trailing whitespace, and split into individual words based on the space delimiter. The method returns only the second part of each split line (index 1 if we consider the line as a list of two parts). 

If there are no spaces in a line, or if the line only contains one word, an `IndexError` might be raised, as the method tries to access the second part of the split line.

### High-Level Explanation
The `extract_markup` method is designed to read a .txt file line by line, process each line to remove the leading and trailing white spaces, split it into parts based on the space delimiter, and store the second part of each line in a list. 

This method is particularly useful when you need to extract a certain part of each line in a text file, provided the part you need is always in the same position after splitting the line.

### Source Code
```python
def extract_markup(file_name):
    '''
    Extract test markup from .txt file.
    '''

    markup = []
    with open(file_name,'r') as f:
        for line in f.readlines():
            markup.append(line.strip().split(" ", 1)[1])

    return markup
```

## Standalone Functions

### Function: get_true_markup_in_seconds

# Documentation

## Method Name: get_true_markup_in_seconds

### Arguments:

- `our_markup`: This is a list containing video markup data. Each entry in the list represents a video's markup, which is a string where different time ranges are separated by commas and time points are separated by a dash. The time format is MM:SS (Minutes:Seconds).

### Return Type: 

- This method returns a list of lists, where each sub-list represents a time range in seconds. 

### High-Level Explanation:

This method is responsible for converting video markup data into a more usable format. The input is a list of strings where each string represents a video's markup. The method processes each video's markup by splitting it into individual time ranges, then further breaking down each time range into start and end points. These points, initially in the format of MM:SS (Minutes:Seconds), are then converted into seconds for easier future processing. The resulting data structure is a list of lists, where each sub-list represents a time range in seconds.

### Source Code:

```python
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
```

This method begins by initializing an empty list `ranges` to store all the converted time ranges. It then iterates over each video's markup in `our_markup`, removing any spaces and splitting the markup into individual time ranges.

For each time range, it initializes an empty list and splits the time range into start and end points. It then converts each point from the MM:SS format into seconds by multiplying the minute part by 60 and adding it to the seconds part. This value is then appended to the current time range.

Finally, after all time points in the current time range have been converted, the time range is appended to `ranges`. The process is repeated for all time ranges in all video markups. The method then returns `ranges`, now filled with the converted time ranges.

## Standalone Functions

### Function: median

# Method Documentation

## Method Name: median

This method is used to calculate the median of an array of integers.

### Arguments

This method accepts one argument:

1. `int_seq` (list): This is a list of integers for which the median is to be calculated.

### Return Type

The return type of this method is an integer or float.

The purpose of the return value is to provide the median of the array of integers passed as an argument. If the length of the array is even, the method will return the mean of the two middle numbers. If the length is odd, it will return the middle number.

### High-Level Explanation

This method calculates the median of an array of integers. 

The method first sorts the array in ascending order. It then checks if the length of the array is odd or even.

- If the length is odd, it returns the number at the middle index of the array. 
- If the length is even, it calculates and returns the average of the two middle numbers.

### Source Code

```python
def median(int_seq):
    '''
    Calculate median of array.
    '''

    int_seq.sort()
    if len(int_seq) % 2 != 0:
        return int_seq[len(int_seq) // 2]
    else:
        return sum(int_seq) / 2
```

In the source code, `int_seq.sort()` is used to sort the array in ascending order. `len(int_seq) % 2 != 0` checks if the length of the array is odd. `int_seq[len(int_seq) // 2]` returns the number at the middle index of the array. `sum(int_seq) / 2` calculates and returns the average of the two middle numbers.

## Standalone Functions

### Function: generate_ranges

Error generating documentation: Connection error.

