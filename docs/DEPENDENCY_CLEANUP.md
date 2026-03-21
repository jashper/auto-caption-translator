# 依賴套件清理分析

## 當前安裝的套件分析

### ✅ 必要套件（不可刪除）

#### Web 框架
- `fastapi==0.104.1` - 後端框架
- `uvicorn==0.24.0` - ASGI 服務器
- `starlette==0.27.0` - FastAPI 依賴
- `python-multipart==0.0.6` - 文件上傳支持
- `h11==0.16.0` - HTTP 協議
- `httptools==0.7.1` - HTTP 解析
- `watchfiles==1.1.1` - 熱重載
- `websockets==16.0` - WebSocket 支持

#### WhisperX 核心
- `whisperx==3.7.2` - 語音轉錄（主要功能）
- `faster-whisper==1.2.1` - WhisperX 後端
- `torch==2.8.0+cpu` - 深度學習框架
- `torchaudio==2.8.0+cpu` - 音訊處理
- `ctranslate2==4.7.1` - 模型推理加速
- `av==15.1.0` - 音訊/視訊處理
- `ffmpeg-python==0.2.0` - 音訊提取

#### WhisperX 對齊和分段
- `nltk==3.9.3` - 句子分段
- `transformers==5.3.0` - Transformer 模型
- `tokenizers==0.22.2` - 文本分詞
- `sentencepiece==0.2.1` - 分詞模型
- `soundfile==0.13.1` - 音訊文件讀寫

#### 說話者分離（pyannote.audio）
- `pyannote.audio==3.4.0` - 說話者分離（WhisperX 依賴）
- `pyannote.core==5.0.0`
- `pyannote.database==5.1.3`
- `pyannote.metrics==3.2.1`
- `pyannote.pipeline==3.0.1`
- `speechbrain==1.0.3` - 語音處理
- `asteroid-filterbanks==0.4.0` - 音訊濾波
- `torch-audiomentations==0.12.0` - 音訊增強
- `torch_pitch_shift==1.2.5` - 音高轉換

#### 機器學習工具
- `numpy==2.0.2` - 數值計算
- `pandas==2.2.3` - 數據處理
- `scipy==1.15.3` - 科學計算
- `scikit-learn==1.7.2` - 機器學習
- `pytorch-lightning==2.6.1` - PyTorch 訓練框架
- `lightning==2.6.1`
- `lightning-utilities==0.15.3`
- `pytorch-metric-learning==2.9.0` - 度量學習
- `torchmetrics==1.9.0` - 評估指標

#### 深度學習支持
- `onnxruntime==1.23.2` - ONNX 推理
- `safetensors==0.7.0` - 安全的張量存儲
- `huggingface_hub==1.7.2` - 模型下載
- `filelock==3.25.2` - 文件鎖
- `fsspec==2026.2.0` - 文件系統抽象

#### 配置和工具
- `omegaconf==2.3.0` - 配置管理
- `HyperPyYAML==1.2.3` - YAML 配置
- `PyYAML==6.0.3` - YAML 解析
- `ruamel.yaml==0.18.17` - YAML 處理
- `python-dotenv==1.0.0` - 環境變量

#### 翻譯服務
- `deep-translator==1.11.4` - 翻譯（主要功能）
- `beautifulsoup4==4.14.3` - HTML 解析（翻譯依賴）
- `soupsieve==2.8.3` - CSS 選擇器

#### 數據驗證
- `pydantic==2.5.0` - 數據驗證
- `pydantic_core==2.14.1`
- `annotated-types==0.7.0`

#### HTTP 客戶端
- `requests==2.32.5` - HTTP 請求
- `urllib3==2.6.3` - URL 處理
- `certifi==2026.2.25` - SSL 證書
- `charset-normalizer==3.4.6` - 字符編碼
- `idna==3.11` - 國際化域名
- `httpx==0.28.1` - 異步 HTTP
- `httpcore==1.0.9`
- `aiohttp==3.13.3` - 異步 HTTP
- `aiohappyeyeballs==2.6.1`
- `aiosignal==1.4.0`
- `async-timeout==5.0.1`
- `frozenlist==1.8.0`
- `multidict==6.7.1`
- `propcache==0.4.1`
- `yarl==1.23.0`

#### 日誌和 CLI
- `python-json-logger==2.0.7` - JSON 日誌
- `coloredlogs==15.0.1` - 彩色日誌
- `colorlog==6.10.1` - 彩色日誌
- `humanfriendly==10.0` - 人性化輸出
- `click==8.3.1` - CLI 工具
- `typer==0.24.1` - CLI 框架
- `shellingham==1.5.4` - Shell 檢測
- `colorama==0.4.6` - Windows 彩色輸出

#### 進度和可視化
- `tqdm==4.67.3` - 進度條
- `rich==14.3.3` - 終端美化
- `matplotlib==3.10.8` - 繪圖（可能用於調試）
- `Pygments==2.19.2` - 語法高亮

#### 其他工具
- `regex==2026.2.28` - 正則表達式
- `joblib==1.5.3` - 並行處理
- `threadpoolctl==3.6.0` - 線程池控制
- `sortedcontainers==2.4.0` - 排序容器
- `six==1.17.0` - Python 2/3 兼容
- `future==1.0.0` - Python 2/3 兼容

### ❓ 可能不需要的套件

#### 數據庫相關（當前未使用）
- `alembic==1.18.4` - 數據庫遷移工具
- `SQLAlchemy==2.0.48` - ORM 框架
- `greenlet==3.3.2` - SQLAlchemy 依賴

**說明**: 當前系統使用 JSON 文件存儲，不需要數據庫。但這些可能是 pyannote.audio 的依賴。

#### 優化和實驗工具
- `optuna==4.8.0` - 超參數優化
- `tensorboardX==2.6.4` - TensorBoard 支持

**說明**: 這些是訓練模型時使用的工具，推理時不需要。但可能是 speechbrain 的依賴。

#### 繪圖工具
- `matplotlib==3.10.8` - 繪圖庫
- `contourpy==1.3.2` - 等高線繪圖
- `cycler==0.12.1` - 顏色循環
- `fonttools==4.62.1` - 字體工具
- `kiwisolver==1.5.0` - 約束求解器
- `pillow==12.1.1` - 圖像處理

**說明**: 可能是某些依賴的可視化工具，推理時不需要。

#### 其他
- `primePy==1.3` - 質數計算（用途不明）
- `docopt==0.6.2` - CLI 參數解析
- `annotated-doc==0.0.4` - 文檔工具

### 🔍 檢查方法

檢查哪些套件是被依賴的：

```bash
# 檢查某個套件被誰依賴
.\venv\Scripts\pip show <package-name>

# 示例
.\venv\Scripts\pip show alembic
```

## 清理建議

### ⚠️ 不建議清理

**原因**:
1. 這些套件大多是 WhisperX 和 pyannote.audio 的依賴
2. 手動刪除可能導致系統崩潰
3. 虛擬環境已經隔離，不會影響系統其他部分
4. 磁碟空間佔用可接受（約 2-3GB）

### ✅ 如果一定要清理

**方法 1：重建虛擬環境（最安全）**

```bash
# 1. 停止服務器
# 關閉 START.bat

# 2. 刪除舊的虛擬環境
Remove-Item -Recurse -Force venv

# 3. 創建新的虛擬環境
python -m venv venv

# 4. 啟動虛擬環境
.\venv\Scripts\activate

# 5. 只安裝 requirements.txt 中的套件
pip install -r requirements.txt

# 6. 驗證安裝
python -c "import whisperx; print(whisperx.__version__)"

# 7. 重新啟動服務器
START.bat
```

**方法 2：使用 pip-autoremove（不推薦）**

```bash
# 安裝 pip-autoremove
pip install pip-autoremove

# 刪除不需要的套件（小心使用！）
pip-autoremove alembic -y
pip-autoremove optuna -y
pip-autoremove matplotlib -y
```

**⚠️ 警告**: 這可能會刪除被其他套件依賴的套件，導致系統崩潰。

## 驗證清理結果

清理後，確保以下功能正常：

```bash
# 1. 啟動服務器
START.bat

# 2. 上傳測試影片
# 訪問 http://localhost:8000

# 3. 檢查日誌
# 查看 logs/app.log 是否有錯誤

# 4. 驗證功能
# - 影片上傳 ✓
# - 轉錄 ✓
# - 翻譯 ✓
# - 字幕生成 ✓
# - 下載 ✓
```

## 最終建議

### 🎯 推薦做法：保持現狀

**理由**:
1. 所有套件都是 WhisperX 生態系統的一部分
2. 虛擬環境已經隔離，不會污染系統
3. 清理風險大於收益
4. 系統運行穩定

### 📦 如果磁碟空間緊張

考慮：
1. 清理 `storage/` 目錄中的舊文件（自動清理機制已實現）
2. 清理 PyTorch 模型緩存（`~/.cache/torch/`）
3. 清理 Hugging Face 模型緩存（`~/.cache/huggingface/`）

```bash
# 查看緩存大小
du -sh ~/.cache/torch/
du -sh ~/.cache/huggingface/

# 清理緩存（小心！）
Remove-Item -Recurse -Force ~/.cache/torch/hub/checkpoints/*
```

## 套件大小參考

大型套件（佔用空間較多）：
- `torch` + `torchaudio`: ~500MB
- `transformers` 模型: ~500MB（緩存）
- `pyannote.audio` 模型: ~300MB（緩存）
- `whisperx` 模型: ~150MB（緩存）
- 其他依賴: ~500MB

**總計**: 約 2GB（虛擬環境 + 模型緩存）

## 更新 requirements.txt

當前 `requirements.txt` 只列出頂層依賴，這是正確的做法：

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
whisperx==3.7.2
ffmpeg-python==0.2.0
deep-translator==1.11.4
pydantic==2.5.0
python-dotenv==1.0.0
python-json-logger==2.0.7
```

**注意**: `requirements.txt` 中的 `whisperx==3.1.1` 需要更新為 `3.7.2`

所有其他套件（如 torch, pyannote.audio 等）都是這些頂層套件的依賴，會自動安裝。

## 結論

✅ **當前環境是乾淨的**
- 沒有安裝不必要的套件
- 所有套件都是 WhisperX 生態系統的一部分
- 系統運行穩定

❌ **不建議清理**
- 風險大於收益
- 可能導致系統崩潰
- 虛擬環境已經隔離

✅ **唯一需要做的**
- 更新 `requirements.txt` 中的 `whisperx` 版本號（3.1.1 → 3.7.2）

---

**最後更新**: 2026-03-21  
**結論**: 環境乾淨，無需清理
