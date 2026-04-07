"""Multi-label food classifier (sigmoid / BCE-style logits)."""

from __future__ import annotations

import logging
import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms

logger = logging.getLogger(__name__)


class MultiLabelFoodClassifier(nn.Module):
    def __init__(self, num_classes: int) -> None:
        super().__init__()
        backbone = models.resnet18(weights=None)
        in_f = backbone.fc.in_features
        backbone.fc = nn.Linear(in_f, num_classes)
        self.backbone = backbone

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.backbone(x)


class ClassifierRuntime:
    """Loads checkpoint if present; otherwise random weights (pipeline smoke test)."""

    def __init__(self, labels: list[str], checkpoint_path: str | None) -> None:
        self.labels = labels
        self.num_classes = len(labels)
        self.model = MultiLabelFoodClassifier(self.num_classes)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.eval()
        if checkpoint_path:
            try:
                state = torch.load(checkpoint_path, map_location=self.device)
                if isinstance(state, dict) and "state_dict" in state:
                    self.model.load_state_dict(state["state_dict"])
                else:
                    self.model.load_state_dict(state)
                logger.info("Loaded classifier from %s", checkpoint_path)
            except Exception as e:
                logger.warning("Could not load checkpoint %s: %s — using random weights", checkpoint_path, e)
        self.transform = transforms.Compose(
            [
                transforms.ToPILImage(),
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ]
        )

    @torch.inference_mode()
    def predict_proba(self, bgr_crop: np.ndarray, threshold: float = 0.5) -> dict[str, float]:
        """Return label -> probability for labels above threshold."""
        rgb = bgr_crop[:, :, ::-1].copy()
        tensor = self.transform(rgb).unsqueeze(0).to(self.device)
        logits = self.model(tensor)
        probs = torch.sigmoid(logits).squeeze(0).detach().cpu().numpy()
        out: dict[str, float] = {}
        for i, name in enumerate(self.labels):
            if i < len(probs) and float(probs[i]) >= threshold:
                out[name] = float(probs[i])
        return out

    @torch.inference_mode()
    def predict_all_proba(self, bgr_crop: np.ndarray) -> dict[str, float]:
        rgb = bgr_crop[:, :, ::-1].copy()
        tensor = self.transform(rgb).unsqueeze(0).to(self.device)
        logits = self.model(tensor)
        probs = torch.sigmoid(logits).squeeze(0).detach().cpu().numpy()
        return {self.labels[i]: float(probs[i]) for i in range(min(len(self.labels), len(probs)))}


def crop_plate(bgr: np.ndarray, xyxy: tuple[float, float, float, float], margin: float = 0.1) -> np.ndarray:
    h, w = bgr.shape[:2]
    x1, y1, x2, y2 = xyxy
    bw, bh = x2 - x1, y2 - y1
    mx, my = bw * margin, bh * margin
    x1 = max(0, int(x1 - mx))
    y1 = max(0, int(y1 - my))
    x2 = min(w, int(x2 + mx))
    y2 = min(h, int(y2 + my))
    if x2 <= x1 or y2 <= y1:
        return bgr[: min(32, h), : min(32, w)]
    return bgr[y1:y2, x1:x2]
