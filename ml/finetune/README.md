# Face Detector Fine-Tuning Guide (WIDER FACE + YOLOv8-face)

This guide documents the fine-tuning workflow for adapting YOLOv8 to detect faces in classroom settings using the WIDER FACE benchmark dataset.

---

## 1. Environment Setup

Run this exercise in a GPU environment (Google Colab or Kaggle with an NVIDIA T4 GPU).

```bash
pip install ultralytics==8.3.0 datasets pillow gdown onnx onnxruntime
```

Mount Google Drive in Colab to preserve model checkpoints across sessions:
```python
from google.colab import drive
drive.mount('/content/drive')
```

---

## 2. Obtain Dataset and Base Model

### 2.1 Dataset (WIDER FACE)
Download the official WIDER FACE dataset:
- `WIDER_train.zip`
- `WIDER_val.zip`
- `wider_face_split.zip`

Extract files to `/content/widerface_raw/`.

### 2.2 Base Checkpoint
Download a face-pretrained YOLOv8 checkpoint:
- Recommended: `yolov8n-face.pt`
- Fallback: standard `yolov8n.pt` from Ultralytics

---

## 3. Dataset Conversion to YOLO Format

Convert the bounding boxes and create a reproducible 3,000-image training subset:

```bash
# Convert training split (subsampled to 3,000 images)
python convert_wider_to_yolo.py \
  --images-dir /content/widerface_raw/WIDER_train/images \
  --annotations /content/widerface_raw/wider_face_split/wider_face_train_bbx_gt.txt \
  --split train \
  --limit 3000 \
  --seed 42 \
  --out /content/datasets/widerface

# Convert full validation split
python convert_wider_to_yolo.py \
  --images-dir /content/widerface_raw/WIDER_val/images \
  --annotations /content/widerface_raw/wider_face_split/wider_face_val_bbx_gt.txt \
  --split val \
  --out /content/datasets/widerface
```

Check the generated check images in `/content/datasets/widerface/check/` to verify bounding boxes align with faces.

---

## 4. Training (Capability-Preserving Schedule)

### Stage A: Head Adaptation (Backbone Frozen)
Freeze the first 10 layers (backbone) to retain pretrained representations:

```bash
yolo detect train \
  model=yolov8n-face.pt \
  data=widerface.yaml \
  imgsz=640 \
  epochs=15 \
  batch=16 \
  freeze=10 \
  lr0=0.0005 \
  lrf=0.1 \
  optimizer=AdamW \
  warmup_epochs=2 \
  patience=5 \
  mosaic=1.0 \
  close_mosaic=3 \
  hsv_v=0.4 \
  mixup=0.0 \
  project=runs \
  name=face_ft
```

### Stage B: Gentle Unfrozen Fine-Tuning (Optional)
If Stage A is stable and mAP is climbing:

```bash
yolo detect train \
  model=runs/face_ft/weights/best.pt \
  data=widerface.yaml \
  imgsz=640 \
  epochs=8 \
  freeze=0 \
  lr0=0.0001 \
  name=face_ft_stage2
```

---

## 5. Validation and Health Check

1. Inspect `runs/face_ft/results.csv`: verify that `metrics/mAP50(B)` and `metrics/mAP50-95(B)` stay flat or rise across epochs.
2. Run visual validation on frontal face photos:
   ```bash
   yolo predict model=runs/face_ft/weights/best.pt source=test_photo.jpg conf=0.4
   ```
3. Save training curves:
   ```bash
   cp runs/face_ft/results.png ml/finetune/results/
   cp runs/face_ft/results.csv ml/finetune/results/
   ```

---

## 6. Model Export and Application Integration

Export the fine-tuned model to ONNX format:

```bash
# Rename best weights
cp runs/face_ft/weights/best.pt face_ft_best.pt

# Export ONNX
yolo export model=face_ft_best.pt format=onnx imgsz=640
```

### Deploying to AttendX:
Copy `face_ft_best.onnx` to the `attendance-app/models/` folder:
```bash
cp face_ft_best.onnx /path/to/attendance-app/models/face_ft_best.onnx
```

Update your `.env` file:
```env
DETECTOR=finetuned
FINETUNED_MODEL_PATH=models/face_ft_best.onnx
```

Start AttendX — the application will automatically load the fine-tuned detector for face localization, while using ArcFace for face identity recognition.
