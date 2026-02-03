@echo off

if not exist "env" (
    echo Creating virtual environment...
    py -m venv env
)

call env\Scripts\activate

echo Updating pip
python -m pip install --upgrade pip

echo Installing PyTorch (CUDA 12.1)
python -m pip install torch==2.9.1 torchvision==0.24.1 --index-url https://download.pytorch.org/whl/cu128

if exist "requirements.txt" (
    echo Installing dependencies from requirements.txt...
    pip install -r requirements.txt
)

echo Done!
pause
