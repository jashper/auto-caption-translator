# 安裝指南

## 目錄
- [快速開始](#快速開始)
- [詳細安裝步驟](#詳細安裝步驟)
- [依賴版本](#依賴版本)
- [試錯過程記錄](#試錯過程記錄)
- [常見問題](#常見問題)

---

## 快速開始

```bash
# 1. 克隆專案
git clone <your-repo-url>
cd video-subtitle-translator

# 2. 創建虛擬環境
python -m venv venv

# Windows
.\venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 配置環境變量
copy .env.example .env
# 編輯 .env 設置你的配置

# 5. 啟動服務器
# Windows
START.bat

# Linux/Mac
./start-server.sh
```

訪問 http://localhost:8000 開始使用！

---

## 詳細安裝步驟

### 1. 系統要求

- Python 3.8+
- ffmpeg（用於音訊處理）
- 至少 4GB RAM
- 至少 2GB 磁碟空間（用於模型緩存）

### 2. 安裝 ffmpeg

**Windows:**
```bash
# 使用 Chocolatey
choco install ffmpeg

# 或從官網下載：https://ffmpeg.org/download.html
```

**Linux:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Mac:**
```bash
brew install ffmpeg
```

### 3. 創建 Python 虛擬環境

```bash
python -m venv venv
```

**啟動虛擬環境：**

Windows:
```bash
.\venv\Scripts\activate
```

Linux/Mac:
```bash
source venv/bin/activate
```

### 4. 安裝 Python 依賴

```bash
pip install -r requirements.txt
```

這會安裝所有必要的套件，包括：
- FastAPI 和 Uvicorn（Web 框架）
- WhisperX（語音轉錄）
- PyTorch 和 torchaudio（深度學習框架）
- deep-translator（翻譯服務）
- 其他輔助套件

### 5. 配置環境變量

```bash
copy .env.example .env
```

編輯 `.env` 文件：

```env
# Whisper 模型大小（tiny, base, small, medium, large）
WHISPER_MODEL_SIZE=base

# 並發處理任務數量
MAX_CONCURRENT_JOBS=2

# 檔案保留時間（小時）
FILE_RETENTION_HOURS=24

# 最大檔案大小（MB）
MAX_FILE_SIZE_MB=500

# 最大影片時長（秒）
MAX_VIDEO_DURATION_SECONDS=3600
```

### 6. 首次運行

```bash
# Windows
START.bat

# Linux/Mac
./start-server.sh
```

首次運行時，系統會自動下載：
1. **Whisper 模型**（base 模型約 150MB）
2. **對齊模型**（wav2vec2 模型約 360MB）

下載完成後會自動緩存，之後不需要重新下載。

### 7. 驗證安裝

訪問 http://localhost:8000，你應該看到上傳介面。

上傳一個測試影片，確認：
- ✅ 影片上傳成功
- ✅ 轉錄進度正常顯示
- ✅ 字幕生成成功
- ✅ 可以預覽和下載字幕

---

## 依賴版本

### 核心依賴（經過測試的穩定版本）

```
whisperx==3.7.2
torch==2.8.0
torchaudio==2.8.0
```

### 完整依賴列表

參見 `requirements.txt`：

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
python-multipart==0.0.20
aiofiles==24.1.0
whisperx==3.7.2
torch==2.8.0
torchaudio==2.8.0
deep-translator==1.11.4
python-dotenv==1.0.1
```

### 為什麼選擇這些版本？

- **WhisperX 3.7.2**：最新穩定版本，提供最佳的時間戳對齊
- **PyTorch 2.8.0**：與 WhisperX 3.7.2 兼容，解決了 weights_only 問題
- **torchaudio 2.8.0**：必須與 PyTorch 版本匹配

---

## 試錯過程記錄

在升級到 WhisperX 的過程中，我們遇到了一些挑戰。以下記錄了完整的試錯過程，供其他開發者參考。

### 問題 1：WhisperX 版本選擇

**嘗試 1：WhisperX 3.1.1**
```bash
pip install whisperx==3.1.1
```

**結果：** ❌ 失敗
- 錯誤：`ERROR: whisperx 3.1.1 has been yanked`
- 原因：該版本已被標記為不穩定

**解決方案：** 升級到 WhisperX 3.7.2（最新穩定版本）

---

### 問題 2：PyTorch 版本衝突

**嘗試 1：PyTorch 2.10.0 + torchaudio 2.10.0**
```bash
pip install torch==2.10.0 torchaudio==2.10.0
```

**結果：** ❌ 失敗
- 錯誤：`AttributeError: 'AudioMetaData' object has no attribute 'sample_rate'`
- 原因：torchaudio 2.10.0 的 API 變更，與 WhisperX 不兼容

**嘗試 2：PyTorch 2.0.0 + torchaudio 2.0.0**
```bash
pip install torch==2.0.0 torchaudio==2.0.0
```

**結果：** ❌ 失敗
- 錯誤：`whisperx requires torch>=2.7.1`
- 原因：版本太舊，不滿足 WhisperX 3.7.2 的最低要求

**嘗試 3：PyTorch 2.8.0 + torchaudio 2.8.0** ✅
```bash
pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cpu
```

**結果：** ✅ 成功
- 滿足 WhisperX 3.7.2 的版本要求（torch>=2.7.1）
- torchaudio API 與 WhisperX 兼容
- 這是 WhisperX 3.7.4 推薦的版本組合

---

### 問題 3：PyTorch 2.8.0 的 weights_only 安全限制

**背景：** PyTorch 2.6+ 將 `torch.load()` 的默認 `weights_only` 參數從 `False` 改為 `True`，以提高安全性。但這導致載入某些舊模型時失敗。

**嘗試 1：全局 monkey patch**

在 `main.py` 中添加：
```python
import torch
original_load = torch.load
def patched_load(*args, **kwargs):
    kwargs.setdefault('weights_only', False)
    return original_load(*args, **kwargs)
torch.load = patched_load
```

**結果：** ❌ 部分成功
- WhisperX 模型可以載入
- 但對齊模型仍然失敗，要求添加更多類到 safe_globals

**嘗試 2：添加 safe_globals**

```python
from torch.serialization import add_safe_globals
from omegaconf import DictConfig, ListConfig
add_safe_globals([DictConfig, ListConfig])
```

**結果：** ❌ 失敗
- 每次都要求新的類（ContainerMetadata → typing.Any → list → ...）
- 無法窮盡所有需要的類

**嘗試 3：局部強制 weights_only=False** ✅

在 `transcription_service.py` 的 `_load_model()` 方法中：
```python
def _load_model(self):
    # 臨時替換 torch.load 以強制 weights_only=False
    original_load = torch.load
    def force_weights_only_false(*args, **kwargs):
        kwargs['weights_only'] = False
        return original_load(*args, **kwargs)
    
    torch.load = force_weights_only_false
    
    try:
        self.model = whisperx.load_model(
            self.model_size,
            device=self.device,
            compute_type=self.compute_type,
            language="en"
        )
        logger.info(f"WhisperX 模型載入成功: {self.model_size}")
    finally:
        # 恢復原始函數
        torch.load = original_load
```

**結果：** ✅ 成功
- 只在需要的地方臨時修改行為
- 載入完成後立即恢復原始函數
- 不影響其他代碼的安全性

---

### 問題 4：模型載入時機

**嘗試 1：在 `__init__` 中載入模型**

```python
def __init__(self):
    self.model = whisperx.load_model(...)
```

**結果：** ❌ 失敗
- 應用啟動時就會載入模型
- 如果載入失敗，整個應用無法啟動

**嘗試 2：延遲載入（Lazy Loading）** ✅

```python
def __init__(self):
    self.model = None  # 延遲載入

def transcribe(self, video_path: str) -> List[SubtitleSegment]:
    if self.model is None:
        self._load_model()  # 第一次調用時才載入
    # ...
```

**結果：** ✅ 成功
- 應用啟動快速
- 只在實際需要時才載入模型
- 錯誤處理更靈活

---

## 常見問題

### Q1: 安裝時出現權限錯誤

```
ERROR: Could not install packages due to an OSError: [WinError 5] Access is denied
```

**解決方案：**
```bash
pip install --user -r requirements.txt
```

### Q2: 找不到 ffmpeg

```
FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'
```

**解決方案：** 安裝 ffmpeg 並確保在 PATH 中（參見上方安裝步驟）

### Q3: 記憶體不足

```
RuntimeError: CUDA out of memory
```

**解決方案：** 使用較小的模型
```env
# 在 .env 中設置
WHISPER_MODEL_SIZE=tiny  # 或 base
```

### Q4: 端口 8000 已被占用

```
ERROR: [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000)
```

**解決方案：**
```bash
# 方法 1：關閉占用端口的程序
# 查找占用端口的進程
netstat -ano | findstr :8000
# 終止進程（替換 <PID> 為實際進程 ID）
taskkill /PID <PID> /F

# 方法 2：使用不同端口
# 編輯 START.bat，將 8000 改為其他端口（如 8001）
uvicorn src.main:app --host 127.0.0.1 --port 8001 --reload
```

### Q5: 模型下載速度慢

**解決方案：** 
- 首次運行需要下載約 500MB 的模型文件
- 請耐心等待，下載完成後會自動緩存
- 如果網路不穩定，可以使用代理或 VPN

### Q6: 字幕質量不佳

**解決方案：** 使用更大的模型
```env
# 在 .env 中設置
WHISPER_MODEL_SIZE=small  # 或 medium（需要更多記憶體）
```

---

## 升級現有安裝

如果你已經安裝了舊版本（使用 openai-whisper），請參考 [UPGRADE_WHISPERX.md](UPGRADE_WHISPERX.md) 進行升級。

---

## 開發環境設置

如果你想參與開發：

```bash
# 安裝開發依賴
pip install -r requirements-test.txt

# 運行測試
pytest

# 運行代碼檢查
flake8 src/
black src/
```

---

## 技術支持

如果遇到其他問題：
1. 檢查 `logs/app.log` 查看詳細錯誤信息
2. 參考 [UPGRADE_WHISPERX.md](UPGRADE_WHISPERX.md) 的試錯記錄
3. 提交 GitHub Issue

---

## 授權

本專案使用 MIT 授權。
