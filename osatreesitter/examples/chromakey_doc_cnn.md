# Documentation for client.py

# Documentation for df_utils.py

## Standalone Functions

### Function: get_transformer

# Documentation for `get_transformer` Method

## Method Name
`get_transformer`

## Arguments

1. `face_policy (str)`: This argument determines the policy to apply when loading and transforming face images. It can have two possible values: 'scale' or 'tight'. If 'scale' is passed, the method crops the face isotropically then scales to a square of size `patch_size`. If 'tight' is passed, the method crops the face tightly without any scaling.

2. `patch_size (int)`: This argument determines the size of the square to which the image will be scaled or cropped. It is used in both 'scale' and 'tight' face policies.

3. `net_normalizer (transforms.Normalize)`: This argument is an instance of the `Normalize` class from `torchvision.transforms`. It is used to normalize the image by subtracting the mean and dividing by the standard deviation of the pixel values.

## Return Type
`A.Compose`: The method returns a composition of several transformations that are applied to the images. The transformation pipeline includes loading transformations (which depend on the `face_policy` argument) and common final transformations (normalization and conversion to tensor).

## High-Level Explanation
The `get_transformer` method creates a transformation pipeline to preprocess face images according to a specified policy. Depending on the `face_policy` argument, it applies different loading transformations to the images: isotropic cropping and scaling for 'scale' policy or tight cropping for 'tight' policy. After that, it applies common final transformations to the images: normalization (using the provided `net_normalizer` argument) and conversion to tensor. The transformation pipeline is created using the `Compose` class from the `albumentations` library.

## Source Code
```python
def get_transformer(face_policy: str, patch_size: int, net_normalizer: transforms.Normalize):
    if face_policy == 'scale':
        loading_transformations = [
            A.PadIfNeeded(min_height=patch_size, min_width=patch_size,
                          border_mode=cv2.BORDER_CONSTANT, value=0, always_apply=True),
            A.Resize(height=patch_size, width=patch_size, always_apply=True),
        ]
    elif face_policy == 'tight':
        loading_transformations = [
            A.LongestMaxSize(max_size=patch_size, always_apply=True),
            A.PadIfNeeded(min_height=patch_size, min_width=patch_size,
                          border_mode=cv2.BORDER_CONSTANT, value=0, always_apply=True),
        ]
    else:
        raise ValueError('Unknown value for face_policy: {}'.format(face_policy))

    final_transformations = [A.Normalize(mean=net_normalizer.mean, std=net_normalizer.std), ToTensorV2()]
    transf = A.Compose(loading_transformations + final_transformations)

    return transf
```

## Standalone Functions

### Function: get_extended_bbox

## Documentation

### Method Name
`get_extended_bbox`

### Arguments
- `box`: A list that represents the initial bounding box. The bounding box is specified as a list of four elements: the x-coordinate of the top-left corner, the y-coordinate of the top-left corner, the x-coordinate of the bottom-right corner, and the y-coordinate of the bottom-right corner.
- `extend_coef`: An optional coefficient that will be used to extend the bounding box. The extension is done by dividing the width and height of the bounding box by this coefficient. The default value is `3.8`.

### Return Type
The method returns a tuple of four elements: the x-coordinate of the new top-left corner, the y-coordinate of the new top-left corner, the x-coordinate of the new bottom-right corner, and the y-coordinate of the new bottom-right corner. The purpose of this return value is to provide new coordinates for an extended bounding box.

### High-Level Explanation
The `get_extended_bbox` method is used to extend a given bounding box by a certain coefficient. It calculates the width and height of the original bounding box, applies the extension to both dimensions, and then returns the coordinates of the new, extended bounding box. If the extension would result in negative coordinates, it clamps those to zero to ensure that the bounding box remains valid.

### Source Code
```python
def get_extended_bbox(box, extend_coef=3.8):
    xmin, ymin, xmax, ymax = list(map(int, box))
    w = xmax - xmin
    h = ymax - ymin
    p_w = int(w // extend_coef)
    p_h = int(h // extend_coef)

    ymin, ymax, xmin, xmax = max(ymin - p_h, 0), ymax + p_h, max(xmin - p_w, 0), xmax + p_w
    return xmin, ymin, xmax, ymax
```

## Standalone Functions

### Function: crop_face

# Documentation

## Method Name
crop_face

## Arguments
- `image`: This is the first argument to the `crop_face` function. The purpose of this argument is to provide the image from which a face is to be cropped. This should be provided as a two-dimensional array, typically an image read using image processing libraries such as OpenCV or PIL.

- `box`: This is the second argument to the `crop_face` function. It is used to specify the bounding box within the image from which the face is to be cropped. The `box` is expected to be a list or a tuple of four elements specifying the coordinates of the box - (xmin, ymin, xmax, ymax).

## Return Type
The `crop_face` function returns a two-dimensional array representing the cropped face from the input image. The returned value is of the same type as the input `image`.

## High-level Description
The `crop_face` function is used to crop a face from a given image using the provided bounding box. The function first calls the `get_extended_bbox` function, which is not defined in the provided source code, with the bounding box coordinates. It is assumed that this function transforms the input box coordinates to some form suitable for cropping the face from the image.

The function then uses these transformed coordinates to index into the image array and crop the face. The cropped face is then returned.

## Source Code
```python
def crop_face(image, box):
    xmin, ymin, xmax, ymax = get_extended_bbox(box)
    crop = image[ymin:ymax, xmin:xmax]
    return crop
```

Note: The function `get_extended_bbox` is not defined in the provided source code. It is assumed that this function takes a bounding box as input and returns transformed coordinates.

# Documentation for fornet.py

## Class: FeatureExtractor

"""
    Abstract class to be extended when supporting features extraction.
    It also provides standard normalized and parameters
    """

### Method: features

## Python Method Documentation

### Method Name
`features`

### Arguments
This method takes two arguments:
1. `self`: This is a standard convention in Python. The `self` parameter is a reference to the current instance of the class, and is used to access variables that belong to the class.

2. `x` (`torch.Tensor`): This argument is expected to be a tensor from the PyTorch library. It is the input data for which the features are to be extracted.

### Return Type
`torch.Tensor`: This method is expected to return a tensor from the PyTorch library. This tensor is expected to contain the features extracted from the input tensor `x`.

### High-Level Explanation
The `features` method is designed to extract features from the input data, represented as a tensor. The specifics of how these features are extracted are not implemented in the provided source code, as indicated by the `NotImplementedError` exception. This suggests that this method is intended to be overridden by a subclass.

### Source Code
```python
def features(self, x: torch.Tensor) -> torch.Tensor:
    raise NotImplementedError
```

This is a skeleton method, meant to be overridden in a subclass. If called directly from an instance of this class, it will raise a `NotImplementedError` exception. This is a way in Python to indicate that the method should not be called directly, but needs to be implemented in any subclass that intends to make use of it.

### Method: get_trainable_parameters

# Documentation

## Method Name
get_trainable_parameters

## Source Code
```python
def get_trainable_parameters(self):
    return self.parameters()
```

## Arguments
The `get_trainable_parameters` method only has a single argument:
- `self`: This argument refers to the instance of the object on which this method is called. This is a default argument in Python object methods and does not need to be passed explicitly.

## Return Type
This method does not return None as mentioned earlier. Instead, it appears to return the output of `self.parameters()`. However, without more context, it's hard to determine the exact return type. Typically, the `parameters()` function is used in PyTorch to get a list of all model parameters that are trainable. This list usually contains PyTorch `Parameter` objects, which are a kind of Tensor that is automatically added to the list of parameters when created. 

## High-Level Explanation
The `get_trainable_parameters` method is a simple function that calls and returns the result of the `parameters()` function on the `self` object. Usually, this method would be a part of a larger class that represents a machine learning model in a library like PyTorch. 

The purpose of this method is to get a list of all model parameters that are trainable. These parameters are the ones that the model learns during training, and they are adjusted via backpropagation to reduce the model's error. This list of parameters is often used when setting up an optimizer that will adjust the parameters to train the model. 

The exact behavior of `self.parameters()` is not specified in this code, as it would depend on the definition within the class in which this method is defined.

### Method: get_normalizer

---
## Python Method Documentation: get_normalizer

### Method Name:
get_normalizer

### Arguments:
This method does not take any arguments.

### Return Type:
The method returns an object of type transforms.Normalize from the torchvision.transforms module. This object is useful to normalize an image tensor using the normalized mean and standard deviation of the ImageNet dataset.

### High-Level Explanation:
The `get_normalizer` method is a simple function that returns a torchvision.transforms.Normalize object. This object is often used to normalize the pixel values in an image tensor, which is a common preprocessing step in deep learning. The mean and standard deviation values used here are for the red, green, and blue channels respectively, and they are the normalized mean and standard deviation of the ImageNet dataset. Normalizing image data helps to keep the pixel intensity values in a reasonable range which can make training deep learning models more stable and efficient.

### Source Code:
```python
def get_normalizer():
    return transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
```
This function does not require any parameters and when called, it returns a Normalize transform object that has been initialized with the mean and standard deviation of the ImageNet dataset. This returned object can be used to normalize the pixel values of an image tensor.

Note: The torchvision.transforms module is part of PyTorch's torchvision package, which offers several commonly used transformations and utilities for computer vision tasks.
---

## Class: EfficientNetGen

No docstring provided

### Method: __init__

# Documentation for Python Method: `__init__`

## Method Name:
`__init__`

## Arguments:
This method takes two arguments:
1. `self` - Represents the instance of the class. By using the `self` keyword we can access the attributes and methods of the class in python.
2. `model` - This is a string parameter which specifies the model to be pre-trained using EfficientNet.

## Return Type:
This method does not return anything. In Python, the constructor (`__init__`) method is not supposed to return anything.

## High-Level Explanation:
The `__init__` method is a special method in Python classes, known as a constructor. This method is automatically called when an object of the class is created.

In the context of this class, the `__init__` method is used to initialize the EfficientNet model with a pre-trained model specified by the `model` argument. It also sets up the classifier with a linear layer, where the input features are the output channels of the convolution head of the EfficientNet model, and the output features are 1. This suggests that the model is used for binary classification. The fully connected layer (`_fc`) of the EfficientNet model is deleted as it is not required.

## Source Code:
```python
def __init__(self, model: str):
    super(EfficientNetGen, self).__init__()

    self.efficientnet = EfficientNet.from_pretrained(model)
    self.classifier = nn.Linear(self.efficientnet._conv_head.out_channels, 1)
    del self.efficientnet._fc
```

### Method: features

# Documentation for `features` Method

## Method Name
`features`

## Arguments
The method takes the following arguments:
- `self`: This argument is a mandatory argument in all instance methods. It is a reference to the instance of the class that is used to access the properties and methods of the class.
- `x`: A `torch.Tensor` object. It represents the input tensor that the features will be extracted from.

## Return Type
This method returns a `torch.Tensor` object. The purpose of this tensor is to provide a flattened version of the input tensor `x` after extracting features and performing average pooling operations on it.

## High-Level Explanation
The `features` method is used to extract features from a given tensor using the EfficientNet model, then perform average pooling on these features. After these operations, the tensor is then flattened from the first dimension onwards. 

The method is particularly useful in creating a more manageable and simplified representation of the input tensor, which can be used for further processing or analysis.

## Source Code
Below is the source code for the method:

```python
def features(self, x: torch.Tensor) -> torch.Tensor:
    x = self.efficientnet.extract_features(x)
    x = self.efficientnet._avg_pooling(x)
    x = x.flatten(start_dim=1)
    return x
```

Here's a step-by-step explanation of what the code does:
- `x = self.efficientnet.extract_features(x)`: This line uses the EfficientNet model to extract features from the input tensor `x`.
- `x = self.efficientnet._avg_pooling(x)`: This line performs average pooling on the features extracted in the previous step.
- `x = x.flatten(start_dim=1)`: This line flattens the tensor from the first dimension onwards, simplifying its structure for further use.
- `return x`: The flattened tensor is then returned by the method.

### Method: forward

## Documentation

### Method Name
`forward`

### Arguments

The method takes two arguments:

1. `self`: This argument is a standard convention in Python and represents the instance of the object of the class. This argument is automatically passed by Python and does not need to be provided by the user. It is used to access the attributes or methods of the class within the method.

2. `x`: This argument should be the input data that needs to be processed. It is expected to be in a format that is compatible with the `features`, `efficientnet._dropout`, and `classifier` methods of the class.

### Return Type
The return type of the `forward` method is `None`. This indicates that the method does not return any value. Note that while the method does not explicitly return a value, it does modify the `x` argument in place, altering the state of this variable in the larger program context.

### High-Level Explanation 
The `forward` method is a part of a class that seems to be a machine learning model, likely a neural network of some kind.

The method performs forward propagation on the input `x`. It passes `x` through three stages:

1. The `features` method, which likely extracts or computes some features from the input data.

2. The `efficientnet._dropout` method, which seems to apply dropout regularization to the features. Dropout is a technique for preventing overfitting in neural networks by randomly setting some features to zero during training.

3. Finally, the `classifier` method is applied to the processed data. This method likely classifies the data into categories or computes some final output values.

### Source Code
The source code for the method is:

```python
def forward(self, x):
    x = self.features(x)
    x = self.efficientnet._dropout(x)
    x = self.classifier(x)
    return x
```

## Class: EfficientNetB4

No docstring provided

### Method: __init__

### Python Method Documentation

#### Method Name:
`__init__`

#### Arguments:

- `self`: This is a conventional instance reference in python. It is used to access variables that belongs to the instance of the class.

#### Return Type:
None. This is a special type in python that represents the absence of a value or a null value. It is an indication that this method does not return any value.

#### High-Level Explanation:
The `__init__` method is a special method in python classes, known as a constructor. It is automatically called when an object of the class is instantiated. The purpose of this method is to set up a new object using the parameters provided. 

In the context of this code, the `__init__` method is initializing a class that is a subclass of the `EfficientNetB4` class, passing a model name 'efficientnet-b4' to the parent class during initialization. 

#### Source Code:
```python
def __init__(self):
    super(EfficientNetB4, self).__init__(model='efficientnet-b4')
```

In the source code above, the `super` function is used to call a method from the parent class (in this case, `EfficientNetB4`). This line of code is calling the `__init__` method of the parent class and passing 'efficientnet-b4' as the model name. This is typically done when you want to add some functionality to the inherited method without overriding the behavior of the original method in the parent class.

# Documentation for model.py

## Class: EfficientNetB0

No docstring provided

### Method: __init__

# Documentation

## Method Name: 
`__init__`

## Arguments: 

- `self`: The instance of the class `EfficientNetB0`. This is a standard convention among Python methods.
- `num_classes` (Default: 2): An integer that represents the number of classification groups the model should be predicting.
- `pretrained` (Default: True): A boolean that indicates whether to use a pretrained instance of the model. If `True`, the model starts with weights learned from a previous training session. If `False`, the model starts with random weights.
- `freeze_layers` (Default: False): A boolean that indicates whether the layers of the model should be frozen. If `True`, the parameters of the model will not be updated during training. If `False`, the parameters of the model are updated during training.

## Return Type:
The method does not return a value. It initializes an instance of the `EfficientNetB0` class.

## High-Level Explanation:
The `__init__` method initializes an instance of the `EfficientNetB0` class. 

It starts by calling the superclass's initialization function. Then it creates a model with a base architecture of `efficientnet_b0`, using pre-trained weights if `pretrained` is set to `True`.

If `freeze_layers` is set to `True`, the model's parameters are frozen to prevent them from being updated during training.

Finally, it replaces the classifier of the model with a new one. This new classifier is a sequence of a dropout layer (with dropout probability of 0.1) and a linear layer. The linear layer's input features are set to 1280, and output features are set to the number of classes specified by `num_classes`.

## Source Code:

```python
def __init__(self, num_classes=2, pretrained=True, freeze_layers=False):
    super(EfficientNetB0, self).__init__()
    self.model = efficientnet_b0(pretrained=pretrained)
    if freeze_layers:
        for param in self.model.parameters():
            param.requires_grad = False
    self.model.classifier = nn.Sequential(
        nn.Dropout(p=0.1, inplace=True),
        nn.Linear(in_features=1280, out_features=num_classes)
    )
```

### Method: forward

# Documentation for Python Method: forward

## Method Name: 
`forward`

## Arguments:
This method accepts two arguments:
1. `self`: This argument refers to the instance of the class where this method is called. It is a convention in Python and it is automatically passed when we call a method on an object.
2. `x`: This is the input data that needs to be passed through the model. The data type and structure of `x` would depend upon the requirements of the model.

## Return Type:
This method does not return anything (`None`). The purpose of this method is to pass the given input `x` through the model and execute the model's processing on it. The output is not returned but used internally within the model.

## High-Level Explanation:
The `forward` method is typically used in the context of neural networks and models in machine learning. It represents the forward pass of the model, where the input data `x` is passed through the model for processing. This method does not return the output; instead, it applies the model to the input data `x`. The result of this computation is often stored internally within the model instance (`self.model`), to be used in subsequent steps of the model's operation.

## Source Code:

```python
def forward(self, x):
    return self.model(x)
```

# Documentation for server.py

## Standalone Functions

### Function: pil_to_tensor

The provided Python method details seem to be incorrect or incomplete. The given "pil_to_tensor" method is not available in the provided source code. However, I'll document the "health" method that is present in the provided code.

---

## Python Method: health

### Source Code:

```python
@app.route('/health', methods=['GET'])
def health():
    return {"success": True}
```

### Method Name: 
`health`

### Arguments: 
This method does not take any arguments.

### Return Type: 
Dictionary - The purpose of the return type is to send a response back to the client. In this case, it is a success message indicating that the server is running fine.

### High-level Explanation:
This method is a route in a web application, possibly using Flask, that responds to HTTP GET requests made to the '/health' endpoint. 

When a GET request is made to this endpoint, the `health` method is called. This method does not take any parameters and simply returns a dictionary with a key "success" and a value of True. 

This is a typical pattern used in web services to provide a simple 'health check' endpoint that other services (like load balancers, monitoring tools, etc.) can call to verify that the service is up and running properly. If the service is running properly, it returns a success message, otherwise, it could return a failure message or not respond at all.

## Standalone Functions

### Function: get_diff_frame

# Documentation

## Method name
```python
get_diff_frame(frame_first, frame_second)
```

## Arguments
This method takes two arguments:
1. `frame_first`: This argument is expected to be a frame of a video or an image. 
2. `frame_second`: This argument is also expected to be a frame of a video or an image. 

The purpose of these arguments is to provide two frames that the method can process and compare.

## Return type
This method does not return any value (`None`).

## High-level explanation
This method is designed to calculate and display the difference between two frames, `frame_first` and `frame_second`. The method first frees any unused GPU memory to ensure maximum availability. It then sets a timer and prints out a few debugging messages. 

The method then calculates the time it took to receive the video and prints out the received video files. It appears that the method is intended to extract a video file from the received files, but the code is incomplete. 

Please note that the provided source code is incomplete and may not perform as expected.

## Source code
```python
def get_diff_frame(frame_first, frame_second):
    torch.cuda.empty_cache()

    start_time = time.time()
    print("=" * 20)
    print("--- Starting get chromakey method...")
    print("--- Processing video receiving...")
    print(request.files)

    video_receiving_end_time = time.time()
    video_receiving_time = video_receiving_end_time - start_time
    file = request.files['videoFile']
    filename
```

Please note that the source code provided is incomplete and does not directly relate to the method name or the provided method details.

## Standalone Functions

### Function: get_chromo_intervals

# Documentation for Python Method - get_chromo_intervals

### Method Name: 
get_chromo_intervals

### Arguments:
- `video_cap`: A video capture object used to read frames from the video.
- `percent`: The percentage of suspicious frames in a second of video that will trigger the method to consider the second as containing chroma key.
- `fps`: Frames per second of the video.
- `start`: The start time (in seconds) for the video analysis.
- `stop`: The stop time (in seconds) for the video analysis.

### Return Type:
Returns a tuple containing two elements. The first element is a list of dictionaries, each containing the start and stop times and score of the suspicious intervals. The second element is the total index of frames.

### High-Level Explanation:
The `get_chromo_intervals` method is designed to analyze a video for intervals that contain chroma key. It achieves this by reading frames from the video, generating difference frames, and checking if these frames exceed a certain threshold of suspicious content. If a second's worth of frames exceeds the specified percentage of suspicious frames, it identifies the second as containing chroma key. It further groups these suspicious seconds into intervals and returns these intervals along with their scores.

### Source Code:
```python
def get_chromo_intervals(video_cap, percent, fps, start, stop):
    ...
    return answer, total_frame_ind

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
...
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9023, debug=False)
```

### Note:
The function `classify_triplet_images` is a helper function that takes a batch of difference frames and classifies them using a chroma key classifier. The result is appended to a list which is used in the main `get_chromo_intervals` to identify suspicious intervals.

