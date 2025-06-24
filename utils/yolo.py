from ultralytics import YOLO
import torch

class YoloDetector:
    def __init__(self, model_path, conf_threshold=0.5):
        self.model = YOLO(model_path)
        self.conf_thres = conf_threshold
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model.to(self.device)
        self.class_names = self.model.names

    def detect(self, frame):
        results = self.model.predict(
            source=frame,
            conf=self.conf_thres,
            stream=False,
            verbose=False
        )
        return results[0].boxes if results else None
