import sys
import os
import cv2
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QListWidget, 
                             QListWidgetItem, QLineEdit, QFileDialog, QComboBox, 
                             QSlider, QProgressBar, QSplitter, QFrame, QMessageBox, QDialog) # <--- เพิ่ม QSlider ตรงนี้แล้ว
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QSettings
from PyQt6.QtGui import QIcon, QPixmap, QImage
import json
# Import Logic ที่แยกไว้ (ต้องมีไฟล์ crop_logic.py อยู่ที่เดียวกัน)
from crop_logic import AICropper

# ==========================================
# Worker Thread
# ==========================================
class WorkerThread(QThread):
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(str, str)
    log_signal = pyqtSignal(str)
    finished = pyqtSignal()

    # --- [แก้ไขจุดที่ 1] รับตัวแปรเพิ่มให้ครบ ---
    def __init__(self, file_paths, output_dir, ratio, padding, model_path, target_class_id):
        super().__init__()
        self.file_paths = file_paths
        self.output_dir = output_dir
        self.ratio = ratio
        self.padding = padding
        
        # เก็บค่าใหม่ไว้ใช้งาน
        self.model_path = model_path
        self.target_class_id = target_class_id
        
        self.is_running = True

    def run(self):
        # --- [แก้ไขจุดที่ 2] ส่ง path โมเดลไปให้ Logic ---
        cropper = AICropper(self.model_path)
        
        total = len(self.file_paths)
        
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        for i, file_path in enumerate(self.file_paths):
            if not self.is_running: break
            
            filename = os.path.basename(file_path)
            self.log_signal.emit(f"Processing: {filename}...")
            
            # --- [แก้ไขจุดที่ 3] ส่ง ID ของสิ่งที่อยาก Detect ไปให้ฟังก์ชัน crop ---
            cropped_img, status = cropper.crop_image(file_path, self.ratio, self.padding, self.target_class_id)
            
            if cropped_img is not None:
                save_path = os.path.join(self.output_dir, filename)
                cv2.imwrite(save_path, cropped_img)
                self.finished_signal.emit(save_path, "OK")
            else:
                self.finished_signal.emit("", f"Failed: {status}")

            progress = int(((i + 1) / total) * 100)
            self.progress_signal.emit(progress)
            
        self.finished.emit()

    def stop(self):
        self.is_running = False

# ==========================================
# Image Viewer Dialog
# ==========================================
class ImageViewer(QDialog):
    def __init__(self, image_path):
        super().__init__()
        self.setWindowTitle("Preview")
        self.resize(600, 800)
        layout = QVBoxLayout()
        
        label = QLabel()
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
             pixmap = pixmap.scaled(580, 780, Qt.AspectRatioMode.KeepAspectRatio)
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(label)
        self.setLayout(layout)

# ==========================================
# Drag & Drop List Widget
# ==========================================
class FileListWidget(QListWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setIconSize(QSize(80, 80))
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.setStyleSheet("QListWidget { border: 2px dashed #aaa; border-radius: 5px; background: #f9f9f9; }")             
        self.setViewMode(QListWidget.ViewMode.IconMode)# --- [เพิ่มบรรทัดนี้] เพื่อให้แสดงผลแบบ Icon Mode (เรียงเป็นตาราง) ---        
        self.setResizeMode(QListWidget.ResizeMode.Adjust)# --- [เพิ่มบรรทัดนี้] เพื่อให้จัดเรียงใหม่อัตโนมัติเวลาขยายหน้าต่าง ---
        self.setSpacing(10)# --- [เพิ่มบรรทัดนี้] เว้นระยะห่างระหว่างรูปไม่ให้เบียดกัน ---
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for f in files:
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp')):
                self.add_image_item(f)

    def add_image_item(self, file_path):
        # --- [แก้ไขจุดที่ 1] เปลี่ยนจากใส่ชื่อไฟล์ เป็นใส่ข้อความว่าง "" ---
        item = QListWidgetItem("") 
        
        # --- [เพิ่มจุดที่ 2] เอาชื่อไฟล์ไปซ่อนไว้ใน Tooltip แทน (เผื่อคนใช้อยากรู้ชื่อ) ---
        item.setToolTip(os.path.basename(file_path))
        
        item.setData(Qt.ItemDataRole.UserRole, file_path)
        
        img = cv2.imread(file_path)
        if img is not None:
            # Resize ให้พอดีกับ icon size
            img = cv2.resize(img, (80, 80)) 
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w, ch = img.shape
            qimg = QImage(img.data, w, h, ch * w, QImage.Format.Format_RGB888)
            item.setIcon(QIcon(QPixmap.fromImage(qimg)))
        
        self.addItem(item)

# ==========================================
# Main Application
# ==========================================
class AppWindow(QMainWindow):
    # Dictionary เก็บค่าสัดส่วน
    RATIO_MAP = {
        "Free (No Ratio)": None,
        "1:1 (Square)": 1 / 1,
        "4:5 (IG Portrait)": 4 / 5,
        "3:4 (Portrait)": 3 / 4,
        "2:3 (Classic 35mm)": 2 / 3,
        "3:2 (Landscape)": 3 / 2,
        "4:3 (Monitor)": 4 / 3,
        "5:4 (Monitor)": 5 / 4,
        "7:5": 7 / 5,
        "9:16 (Story/TikTok)": 9 / 16,
        "16:9 (Youtube)": 16 / 9,
        "21:9 (Cinema)": 21 / 9,
        "2:1": 2 / 1,
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Smart Crop")
        self.resize(1000, 700)
        self.initUI()
        # ---(เก็บเป็นไฟล์ตั้งค่าล่าสุด .ini ข้างๆ ไฟล์โปรแกรม) ---
        import os
        config_path = os.path.join(os.getcwd(), "settings.ini")
        self.settings = QSettings(config_path, QSettings.Format.IniFormat)
        
        self.initUI()
        self.load_settings()
        
    def initUI(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)

        # --- Left Panel ---
        input_layout = QVBoxLayout()
        input_label = QLabel("📥 Input Images (Drag & Drop Here)")
        input_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.input_list = FileListWidget()
        clear_btn = QPushButton("Clear List")
        clear_btn.clicked.connect(self.input_list.clear)

        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_list)
        input_layout.addWidget(clear_btn)

        # --- Middle Panel (Settings) ---
        settings_frame = QFrame()
        settings_frame.setFrameShape(QFrame.Shape.StyledPanel)
        settings_frame.setFixedWidth(280)
        settings_layout = QVBoxLayout()
        settings_frame.setLayout(settings_layout)
        
        # ==========================================
        # [ใหม่] ส่วน Model Selection
        # ==========================================
        settings_layout.addWidget(QLabel("🧠 AI Model:"))
        self.combo_model = QComboBox()
        # เมื่อเลือกเปลี่ยนโมเดล -> ให้ไปเรียกฟังก์ชันอัปเดตรายการ
        self.combo_model.currentIndexChanged.connect(self.on_model_changed) 
        settings_layout.addWidget(self.combo_model)
        
        settings_layout.addSpacing(10)

        # ==========================================
        # [ใหม่] ส่วน Detection Class Selection
        # ==========================================
        settings_layout.addWidget(QLabel("🎯 Detect Target:"))
        self.combo_class = QComboBox()
        # (ไม่ต้องเรียก load_detect_list_json() ตรงนี้แล้ว เพราะจะถูกเรียกอัตโนมัติเมื่อโหลดโมเดลเสร็จ)
        settings_layout.addWidget(self.combo_class)

        settings_layout.addSpacing(10)
        self.load_models_json()
        # Ratio Dropdown
        settings_layout.addWidget(QLabel("📏 Aspect Ratio:"))
        self.combo_ratio = QComboBox()
        self.combo_ratio.addItems(self.RATIO_MAP.keys()) # ดึง Key จาก Dict
        
        # ตั้ง Default เป็น 3:4 ถ้ามี
        default_idx = self.combo_ratio.findText("3:4 (Portrait)")
        if default_idx >= 0:
            self.combo_ratio.setCurrentIndex(default_idx)
            
        settings_layout.addWidget(self.combo_ratio)

        settings_layout.addSpacing(10)

        # Padding Slider (แก้ใหม่)
        settings_layout.addWidget(QLabel("↔️ Padding (%):"))
        slider_layout = QHBoxLayout()
        
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 50)
        self.slider.setValue(15)
        
        self.lbl_padding_value = QLabel("15%")
        self.lbl_padding_value.setFixedWidth(40)
        
        # Connect Signal (จุดที่เคย Error)
        self.slider.valueChanged.connect(self.update_padding_label)
        
        slider_layout.addWidget(self.slider)
        slider_layout.addWidget(self.lbl_padding_value)
        settings_layout.addLayout(slider_layout)

        settings_layout.addSpacing(20)

        # Output Path
        settings_layout.addWidget(QLabel("📂 Output Folder:"))
        self.txt_output = QLineEdit(os.path.join(os.getcwd(), "output"))
        
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self.browse_output)
        
        btn_open = QPushButton("📂 Open Folder")
        btn_open.clicked.connect(self.open_output_folder)

        settings_layout.addWidget(self.txt_output)
        settings_layout.addWidget(btn_browse)
        settings_layout.addWidget(btn_open)

        settings_layout.addStretch()

        # Start Button
        self.btn_start = QPushButton("🚀 Start Process")
        self.btn_start.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        self.btn_start.clicked.connect(self.start_processing)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        settings_layout.addWidget(self.lbl_status)
        settings_layout.addWidget(self.progress_bar)
        settings_layout.addWidget(self.btn_start)

        # --- Right Panel ---
        output_layout = QVBoxLayout()
        output_label = QLabel("📤 Output Preview")
        output_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.output_list = FileListWidget()
        self.output_list.setStyleSheet("QListWidget { border: 2px solid #4CAF50; border-radius: 5px; }")
        self.output_list.itemDoubleClicked.connect(self.view_large_image)

        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_list)

        # Add to main
        main_layout.addLayout(input_layout, 2)
        main_layout.addWidget(settings_frame)
        main_layout.addLayout(output_layout, 2)

    # ฟังก์ชันที่เชื่อมกับ Slider (ต้องชื่อตรงกับที่ connect)
    def update_padding_label(self, value):
        self.lbl_padding_value.setText(f"{value}%")

    def browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.txt_output.setText(folder)

    def open_output_folder(self):
        path = self.txt_output.text()
        if os.path.exists(path):
            os.startfile(path)
        else:
            QMessageBox.warning(self, "Error", "Output folder does not exist.")

    def get_ratio_value(self):
        selected = self.combo_ratio.currentText()
        # ดึงค่าจาก Dict (จะได้ None ถ้าเลือก Free)
        return self.RATIO_MAP.get(selected)
        
    # ฟังก์ชันโหลด Model List
    def load_models_json(self):
        self.combo_model.clear()
        
        # หาทีอยู่จริงของไฟล์ gui_app.py
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, 'config/models_list.json')

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                models = json.load(f)
                for m in models:
                    user_data = {
                        "model_path": m['path'],
                        "list_path": m.get('detect_list', 'lists/coco_80.json')
                    }
                    self.combo_model.addItem(m['name'], user_data)
        except Exception as e:
            self.combo_model.addItem(f"Error (models): {e}")
            # print เพื่อดู error ในจอดำ
            print(f"Error loading models from {json_path}: {e}")

    # [ฟังก์ชันใหม่] ทำงานเมื่อเปลี่ยนโมเดล
    def on_model_changed(self, index):
        # ดึงข้อมูล Dictionary ที่เราฝังไว้
        data = self.combo_model.itemData(index)
        if data:
            list_file = data.get("list_path")
            # โหลดรายการใหม่ทันที
            self.load_detect_list_json(list_file)

    # [แก้ใหม่] รับชื่อไฟล์เป็น Parameter
    def load_detect_list_json(self, relative_path):
        self.combo_class.clear()
        
        # หาทีอยู่จริงของไฟล์ gui_app.py แล้วต่อด้วย path ของ json
        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_dir, relative_path)
        
        if not os.path.exists(full_path):
            self.combo_class.addItem(f"List not found", 0)
            return

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                labels = data.get("id2label", {})
                
                if not labels:
                    self.combo_class.addItem("No classes found", 0)
                    return

                for key_id in sorted(labels.keys(), key=int):
                    name = labels[key_id]
                    self.combo_class.addItem(f"{key_id}: {name.capitalize()}", int(key_id))
                    
        except Exception as e:
            self.combo_class.addItem(f"Error: {e}", 0)

    def start_processing(self):
        files = []
        for i in range(self.input_list.count()):
            item = self.input_list.item(i)
            files.append(item.data(Qt.ItemDataRole.UserRole))

        if not files:
            QMessageBox.warning(self, "Warning", "Please add images first!")
            return

        output_dir = self.txt_output.text()
        ratio = self.get_ratio_value()
        padding = self.slider.value()
        
        # [แก้ใหม่] ดึง path โมเดล จาก Dictionary
        current_data = self.combo_model.currentData()
        if isinstance(current_data, dict):
            model_path = current_data.get("model_path")
        else:
            model_path = "models/yolov8n.pt" # Default

        target_class_id = self.combo_class.currentData()
        if target_class_id is None: target_class_id = 0
        
        # ป้องกันค่า None (กรณีโหลด JSON พัง)
        if model_path is None: model_path = "models/yolov8n.pt"
        if target_class_id is None: target_class_id = 0

        self.btn_start.setEnabled(False)
        self.output_list.clear()
        self.progress_bar.setValue(0)

        # ส่งค่าทั้งหมดไปให้ Worker
        self.worker = WorkerThread(files, output_dir, ratio, padding, model_path, target_class_id)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_image_finished)
        self.worker.log_signal.connect(self.update_status)
        self.worker.finished.connect(self.on_process_complete)
        self.worker.start()

    def update_progress(self, val):
        self.progress_bar.setValue(val)

    def update_status(self, text):
        self.lbl_status.setText(text)

    def on_image_finished(self, path, status):
        if status == "OK":
            self.output_list.add_image_item(path)

    def on_process_complete(self):
        self.btn_start.setEnabled(True)
        self.lbl_status.setText("Done!")
        QMessageBox.information(self, "Success", "Processing Complete!")

    def view_large_image(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        viewer = ImageViewer(path)
        viewer.exec()
        
    # ==========================================
    # [ส่วนใหม่] ฟังก์ชันจัดการ Settings
    # ==========================================
    def load_settings(self):
        """อ่านค่าจาก Memory มาใส่ในช่องต่างๆ"""
        # 1. Output Folder (ค่า Default คือโฟลเดอร์ output ปัจจุบัน)
        default_path = os.path.join(os.getcwd(), "output")
        saved_path = self.settings.value("output_dir", default_path)
        self.txt_output.setText(str(saved_path))

        # 2. Padding (ต้องแปลงเป็น int เพราะค่าที่อ่านมาอาจเป็น string)
        saved_padding = self.settings.value("padding", 15) # Default 15
        self.slider.setValue(int(saved_padding))

        # 3. Aspect Ratio (จำชื่อที่เลือกไว้ล่าสุด)
        saved_ratio = self.settings.value("ratio_text", "3:4 (Portrait)")
        index = self.combo_ratio.findText(str(saved_ratio))
        if index >= 0:
            self.combo_ratio.setCurrentIndex(index)

    def save_settings(self):
        """บันทึกค่าปัจจุบันลง Memory"""
        self.settings.setValue("output_dir", self.txt_output.text())
        self.settings.setValue("padding", self.slider.value())
        self.settings.setValue("ratio_text", self.combo_ratio.currentText())

    def closeEvent(self, event):
        """ทำงานอัตโนมัติเมื่อกดปิดโปรแกรม (กากบาท)"""
        self.save_settings() # สั่งบันทึกก่อนปิด
        super().closeEvent(event) # ปิดโปรแกรมตามปกติ

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AppWindow()
    window.show()
    sys.exit(app.exec())