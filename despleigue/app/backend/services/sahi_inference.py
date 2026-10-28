"""Sliced inference using the already loaded local Ultralytics model."""
import cv2
from sahi.models.ultralytics import UltralyticsDetectionModel
from sahi.predict import get_sliced_prediction


class ConfiguredUltralyticsModel(UltralyticsDetectionModel):
    """Pass the request's NMS settings to every SAHI slice."""

    def __init__(self, *args, iou, max_det, **kwargs):
        self.iou = iou
        self.max_det = max_det
        super().__init__(*args, **kwargs)

    def perform_batch_inference(self, images):
        images_bgr = [image[:, :, ::-1] for image in images]
        results = self.model.predict(
            images_bgr, verbose=False, conf=self.confidence_threshold,
            iou=self.iou, max_det=self.max_det, device=self.device, imgsz=self.image_size,
        )
        self._original_predictions = self._extract_predictions(results)
        self._original_shapes = [image.shape for image in images]


def predict_sliced(model, image, *, conf, iou, imgsz, max_det, device):
    adapter = ConfiguredUltralyticsModel(
        model=model, confidence_threshold=conf, image_size=imgsz, device=device,
        iou=iou, max_det=max_det,
    )
    result = get_sliced_prediction(
        cv2.cvtColor(image, cv2.COLOR_BGR2RGB), adapter,
        slice_height=768, slice_width=768,
        overlap_height_ratio=0.2, overlap_width_ratio=0.2,
        perform_standard_pred=True, postprocess_type="NMS", postprocess_match_metric="IOU",
        postprocess_match_threshold=iou, postprocess_class_agnostic=False, verbose=0,
    )
    return [
        (item.bbox.to_xyxy(), item.score.value, item.category.name)
        for item in sorted(result.object_prediction_list, key=lambda item: item.score.value, reverse=True)[:max_det]
    ]
