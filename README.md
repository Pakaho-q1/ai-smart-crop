# ✂️ AI Smart Crop (Auto Object Detection & Cropping)

An intelligent desktop application for batch processing image crops using AI (YOLOv8). Automatically detect and crop persons, faces, or any custom objects with adjustable aspect ratios and padding.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green.svg)
![YOLOv8](https://img.shields.io/badge/AI-YOLOv8-yellow.svg)

## ✨ Features

* **Drag & Drop Interface:** Easily import multiple images by dragging them into the app.
* **Multi-Model Support:** Switch between different AI models (e.g., General YOLOv8, Face Detection, Hand Detection) via JSON configuration.
* **Custom Detection Target:** Select specific objects to crop (e.g., Person, Car, Face) based on the loaded model's capabilities.
* **Aspect Ratio Control:** Presets for common ratios (1:1, 3:4, 16:9) and a "Free" mode for tight crops.
* **Smart Padding:** Adjust padding percentage to include more context around the detected object.
* **Auto Hardware Acceleration:** Automatically switches to GPU (CUDA) if available; falls back to CPU seamlessly.

## 🛠️ Installation

1.  **Clone the repository**
    ```bash
    git clone [https://github.com/YOUR_USERNAME/ai-smart-crop.git](https://github.com/YOUR_USERNAME/ai-smart-crop.git)
    cd ai-smart-crop
    ```

2.  **Install dependencies**
    It is recommended to use a virtual environment.
    ```bash
    pip install -r requirements.txt
    ```

3.  **Setup Models**
    * Create a folder named `models` in the root directory.
    * Download YOLOv8 weights (e.g., `yolov8n.pt`, `yolov8n-face.pt`) and place them inside.
    * *(Optional)* If you want to use GPU, ensure you have the correct CUDA version installed for PyTorch.

4.  **Check Configuration**
    Ensure `models_list.json` and the `lists/` directory are present for dynamic model loading.

## 📂 File Structure

```text
ai-smart-crop/
├── gui_app.py          # Main GUI application entry point
├── crop_logic.py       # Core AI processing logic (YOLOv8 wrapper)
├── models/             # Directory for storing .pt model files
│   ├── yolov8n.pt
│   └── yolov8n-face.pt
└── config/            
    ├── models_list.json # Configuration file for model selection 
    └── detect_lists/    #JSON lists defining class IDs for each model
        ├── yolov8n_detect.json
        └── yolov11n-face_detect.json

## 🚀 Usage

* 1.Run the application: run.bat
* 2.Drag & Drop images into the left panel.
* 3.Select your desired AI Model and Detect Target (e.g., Person).
* 4.Adjust Aspect Ratio and Padding sliders.
* 5.Select an Output Folder.
* 6.Click Start Process.
