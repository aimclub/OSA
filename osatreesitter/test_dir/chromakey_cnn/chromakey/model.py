from torch import nn
from torchvision.models import efficientnet_b0


class EfficientNetB0(nn.Module):
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

    def forward(self, x):
        return self.model(x)
