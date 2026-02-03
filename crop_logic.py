import cv2
import numpy as np
import torch
from ultralytics import YOLO
import json

# แก้ปัญหา PyTorch 2.4+
try:
    from ultralytics.nn.tasks import DetectionModel
    torch.serialization.add_safe_globals([DetectionModel])
except ImportError:
    pass

class AICropper:
    # รับ model_path มาจากข้างนอก (GUI ส่งมา)
    def __init__(self, model_path): 
        print(f"Loading Model: {model_path}")
        self.model = YOLO(model_path) 
        
        if torch.cuda.is_available():
            self.model.to('cuda')
            print(f"✅ Using GPU: {torch.cuda.get_device_name(0)}")
        else:
            self.model.to('cpu')
            print(f"⚠️ Using CPU")

    # เพิ่ม parameter 'target_class_ids' (รับเป็น list เผื่ออนาคตอยากหาหลายอย่างพร้อมกัน)
    def crop_image(self, image_path, target_ratio, padding_percent, target_class_id):
        try:
            pad_factor = padding_percent / 100.0
            
            img = cv2.imread(image_path)
            if img is None: return None, "Error: Cannot read image"
            h_img, w_img, _ = img.shape
            
            results = self.model.predict(img, verbose=False)
            
            if len(results[0].boxes) == 0:
                return None, "No object detected"

            boxes = results[0].boxes.xyxy.cpu().numpy()
            classes = results[0].boxes.cls.cpu().numpy()
            
            # --- Logic กรอง Class ตามที่เลือกจาก Dropdown ---
            target_boxes = []
            for box, cls in zip(boxes, classes):
                # เช็คว่า Class ตรงกับที่เลือกไหม (เช่น เลือก 0=Person, 2=Car)
                if int(cls) == int(target_class_id): 
                    target_boxes.append(box)

            if not target_boxes:
                return None, f"Target class {target_class_id} not found"

            # --- Logic หาตัวใหญ่สุด (เหมือนเดิม) ---
            best_box = None
            max_area = 0
            for box in target_boxes:
                x1, y1, x2, y2 = box
                area = (x2 - x1) * (y2 - y1)
                if area > max_area:
                    max_area = area
                    best_box = box

            if best_box is None: return None, "Detection failed"

            min_x, min_y, max_x, max_y = best_box
            box_w = max_x - min_x
            box_h = max_y - min_y
            
            pad_x = box_w * pad_factor
            pad_y = box_h * pad_factor

            base_x1 = max(0, min_x - pad_x)
            base_y1 = max(0, min_y - pad_y)
            base_x2 = min(w_img, max_x + pad_x)
            base_y2 = min(h_img, max_y + pad_y)

            if target_ratio is None:
                crop_x1, crop_y1, crop_x2, crop_y2 = base_x1, base_y1, base_x2, base_y2
            else:
                current_w = base_x2 - base_x1
                current_h = base_y2 - base_y1
                current_ratio = current_w / current_h
                
                center_x = base_x1 + (current_w / 2)
                center_y = base_y1 + (current_h / 2)

                new_w, new_h = 0, 0
                if current_ratio > target_ratio:
                    new_w = current_w
                    new_h = current_w / target_ratio
                else:
                    new_h = current_h
                    new_w = current_h * target_ratio

                crop_x1 = center_x - (new_w / 2)
                crop_y1 = center_y - (new_h / 2)
                crop_x2 = center_x + (new_w / 2)
                crop_y2 = center_y + (new_h / 2)

            final_x1 = int(max(0, crop_x1))
            final_y1 = int(max(0, crop_y1))
            final_x2 = int(min(w_img, crop_x2))
            final_y2 = int(min(h_img, crop_y2))

            if final_x2 <= final_x1 or final_y2 <= final_y1:
                return None, "Crop area too small"

            cropped_img = img[final_y1:final_y2, final_x1:final_x2]
            return cropped_img, "Success"

        except Exception as e:
            return None, str(e)