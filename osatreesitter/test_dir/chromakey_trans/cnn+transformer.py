import torch
from torch.optim import AdamW
from video_transformers import TimeDistributed, VideoModel
from video_transformers.backbones.transformers import TransformersBackbone
from video_transformers.data import VideoDataModule
from video_transformers.heads import LinearHead
from video_transformers.necks import TransformerNeck
from video_transformers.trainer import trainer_factory
from focal_loss import FocalLoss
import warnings
warnings.filterwarnings("ignore")

backbone = TransformersBackbone("facebook/convnext-tiny-224", num_unfrozen_stages=1)
backbone = TimeDistributed(backbone)
neck = TransformerNeck(
    num_features=backbone.num_features,
    num_timesteps=4,
    transformer_enc_num_heads=4,
    transformer_enc_num_layers=2,
    dropout_p=0.1,
)

datamodule = VideoDataModule(
    train_root="dataset/train",
    val_root="dataset/val",
    batch_size=128,
    num_workers=0,
    num_timesteps=4,
    preprocess_input_size=224,
    preprocess_clip_duration=1,
    preprocess_means=backbone.mean,           
    preprocess_stds=backbone.std,
    preprocess_min_short_side=256,
    preprocess_max_short_side=320,
    preprocess_horizontal_flip_p=0.5,
)

head = LinearHead(hidden_size=neck.num_features, num_classes=datamodule.num_classes)
model = VideoModel(backbone, head, neck)

optimizer = AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4) 

print("cnn_transformer")
Trainer = trainer_factory("single_label_classification")
trainer = Trainer(
    datamodule,
    model,
    optimizer=optimizer,
    max_epochs = 40,
    loss_function = FocalLoss(gamma = 2, alpha=torch.tensor([1.0, 0.7]).to("cuda")) 
)
trainer.fit()

