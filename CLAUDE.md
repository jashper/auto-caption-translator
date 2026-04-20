# Claude AI 助手指南

這份文件是給 AI 助手（如 Claude）的專案指引，幫助更好地理解和協助開發此專案。

## 專案概述

**Video Subtitle Translator** 是一個自動影片字幕生成和翻譯系統，使用 WhisperX 進行語音識別，並支援多語言翻譯。

### 核心技術棧
- **後端**: FastAPI + Uvicorn
- **語音識別**: WhisperX 3.7.2（增強版 Whisper，提供更精確的時間戳對齊）
- **自訂模型**: 支援 HuggingFace repo ID（如 MediaTek-Research/Breeze-ASR-26）
- **裝置**: 自動偵測 GPU (CUDA)，支援 auto/cpu/cuda
- **深度學習**: PyTorch 2.8.0 + torchaudio 2.8.0
- **翻譯**: deep-translator（Google Translate，批量合併翻譯）
- **前端**: 原生 HTML/CSS/JavaScript（無框架）

### 當前版本
- **最新版本**: v2.5.0
- **Python**: 3.10+
- **平台**: Windows（主要開發環境）

---

## 專案結構

```
video-subtitle-translator/
├── src/              # 後端源代碼（Python）
│   ├── models/       # 數據模型
│   ├── routes/       # FastAPI 路由
│   ├── services/     # 核心業務邏輯（轉錄、翻譯）
│   └── utils/        # 工具函數
├── static/           # 前端資源
│   ├── css/          # 樣式文件
│   ├── js/           # JavaScript 文件
│   └── index.html    # 主頁面
├── storage/          # 運行時數據（不提交到 Git）
│   ├── uploads/      # 上傳的影片
│   ├── subtitles/    # 生成的字幕
│   └── jobs/         # 任務狀態
├── tests/            # 測試文件
├── tools/            # 工具腳本
├── docs/             # 開發文檔
└── logs/             # 應用日誌
```

---

## 開發規範

### 1. 代碼風格

#### Python
- 遵循 PEP 8 規範
- 使用 4 空格縮排
- 函數和變數使用 snake_case
- 類名使用 PascalCase
- 添加類型提示（Type Hints）
- 寫清晰的 docstrings

#### JavaScript
- 使用現代 ES6+ 語法
- 使用 camelCase 命名
- 避免使用框架（保持原生）
- 優先使用 const/let，避免 var
- 添加註釋說明複雜邏輯

#### CSS
- 使用 CSS Variables 管理主題
- 遵循 BEM 命名規範（可選）
- 移動優先的響應式設計
- 保持極簡主義風格

### 2. 設計理念

專案採用**極簡主義設計**，靈感來自 Linear、Stripe、Vercel：
- **Less is More**: 只保留必要元素
- **內容優先**: 功能和內容是焦點
- **清晰層次**: 通過留白和字體建立視覺層次
- **一致性**: 統一的間距、顏色、字體系統

詳細設計規範請參考 `DESIGN.md`。

### 3. Git 提交規範

#### 提交訊息格式
```
<type>: <subject>

<body>

<footer>
```

#### Type 類型
- `feat`: 新功能
- `fix`: Bug 修復
- `docs`: 文檔更新
- `style`: 代碼格式（不影響功能）
- `refactor`: 重構
- `test`: 測試相關
- `chore`: 構建/工具相關

#### 範例
```bash
git commit -m "feat: Add playback speed control

- Added speed selector (0.5x-3x)
- Fixed PiP mode speed synchronization
- Updated UI with speed control button"
```

詳細指南請參考 `GIT_COMMIT_GUIDE.md`。

### 4. 版本管理

使用 Git 標籤標記版本：
```bash
# 創建標籤
git tag -a v2.4.2 -m "Version 2.4.2 - Bug fixes"

# 推送標籤
git push origin v2.4.2
```

版本號遵循語義化版本（Semantic Versioning）：
- **主版本號**: 重大變更（不向後兼容）
- **次版本號**: 新功能（向後兼容）
- **修訂號**: Bug 修復

詳細指南請參考 `VERSION_TAG.md`。

---

## 重要文檔

### 用戶文檔
- `README.md` - 專案說明和快速開始
- `INSTALLATION.md` - 完整安裝指南
- `MAINTENANCE.md` - 維護和故障排除
- `CHANGELOG.md` - 版本更新日誌

### 開發文檔
- `DESIGN.md` - 技術設計和架構
- `PROJECT_STRUCTURE.md` - 專案結構說明
- `GIT_COMMIT_GUIDE.md` - Git 提交指南
- `VERSION_TAG.md` - 版本標籤指南
- `UPGRADE_WHISPERX.md` - WhisperX 升級記錄
- `OPTIMIZATION_NOTES.md` - 性能優化記錄

### 開發文檔（docs/）
- `docs/MULTILINGUAL_DETECTION.md` - 多語言檢測實現
- `docs/PROCESSING_PIPELINE.md` - 處理流程說明
- `docs/WHISPERX_SEGMENTATION.md` - WhisperX 分段說明

---

## 常見任務

### 啟動開發伺服器
```bash
# Windows
START.bat

# 或手動啟動
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 安裝依賴
```bash
pip install -r requirements.txt
```

### 清理存儲空間
```bash
# Windows
清理存儲空間.bat

# 或使用 PowerShell
powershell -ExecutionPolicy Bypass -File tools/CLEAN_STORAGE.ps1
```

### 檢查版本
```bash
python tools/check_versions.py
```

---

## 開發注意事項

### 1. 依賴管理
- **謹慎升級依賴**: WhisperX 和 PyTorch 版本需要仔細測試
- **使用虛擬環境**: 避免污染全局 Python 環境
- **鎖定版本**: 重要依賴使用固定版本號

### 2. 性能考量
- **大文件處理**: 影片最大 5GB，時長最大 2 小時
- **記憶體管理**: WhisperX 需要足夠的 RAM（建議 8GB+）
- **GPU 加速**: 支援 CUDA（透過 `DEVICE=auto` 自動偵測，顯著提升速度 5-10x）
- **翻譯批量化**: 多句合併為單次 Google Translate 請求，速度提升 ~10x
- **自訂模型**: 支援 HuggingFace fine-tuned 模型，針對特定語言大幅提升辨識品質

### 3. 錯誤處理
- **詳細日誌**: 使用 Python logging 模組記錄錯誤
- **用戶友好**: 前端顯示清晰的錯誤訊息
- **優雅降級**: 處理各種邊緣情況

### 4. 安全性
- **本地處理**: 所有處理在本地完成，不上傳雲端
- **文件驗證**: 檢查上傳文件類型和大小
- **路徑安全**: 防止路徑遍歷攻擊

### 5. 測試
- **手動測試**: 使用 tests/ 目錄中的 HTML 測試頁面
- **功能測試**: 測試完整的上傳→處理→下載流程
- **邊緣情況**: 測試大文件、長影片、特殊字符等

---

## 文件命名規範

### 避免創建的文件
專案使用 `.gitignore` 自動忽略以下臨時文件：
- `*_FIX.md`
- `*_DEBUG.txt`
- `*_TEMP.md`
- `*_OLD.md`
- `*_BACKUP.md`
- `TEMP_*.md`
- `DEBUG_*.txt`

### 推薦的文件命名
- 文檔: 使用大寫 + 底線（如 `DESIGN.md`）
- 代碼: 使用小寫 + 底線（如 `translation_service.py`）
- 測試: 使用 `test_` 前綴（如 `test_keyboard.html`）

---

## AI 助手協作建議

### 當協助此專案時，請：

1. **閱讀相關文檔**: 先查看 README.md、DESIGN.md 等文檔
2. **遵循現有風格**: 保持代碼和設計的一致性
3. **更新文檔**: 修改功能時同步更新相關文檔
4. **測試變更**: 確保修改不會破壞現有功能
5. **清晰註釋**: 添加清晰的代碼註釋和 commit 訊息
6. **避免過度設計**: 保持簡單和實用
7. **考慮用戶體驗**: 優先考慮易用性和性能

### 不要：

1. **不要引入新框架**: 保持原生 JavaScript
2. **不要過度優化**: 除非有明確的性能問題
3. **不要創建臨時文件**: 避免 `*_FIX.md` 等臨時文件
4. **不要忽略文檔**: 代碼變更必須更新文檔
5. **不要破壞向後兼容**: 謹慎處理 API 變更

---

## 常見問題

### Q: 為什麼使用 WhisperX 而不是標準 Whisper？
A: WhisperX 提供更精確的時間戳對齊和更好的句子分段，提升字幕質量。

### Q: 為什麼不使用前端框架（React/Vue）？
A: 保持簡單和輕量，避免不必要的複雜性。原生 JavaScript 足以滿足需求。

### Q: 如何處理大文件？
A: 系統限制 5GB 和 2 小時，超過建議分段處理。

### Q: 支援哪些語言？
A: 語音識別支援多種語言（由 Whisper 決定），翻譯目前支援繁中、簡中、馬來語。

---

## 聯絡和支援

- **文檔**: 查看專案根目錄的 Markdown 文件
- **問題**: 檢查 `MAINTENANCE.md` 的故障排除章節
- **更新**: 查看 `CHANGELOG.md` 了解最新變更

---

## 版本歷史

- `v1.0.0` - 初始版本，基本字幕生成
- `v2.0.0` - 添加影片播放器和字幕編輯器
- `v2.1.0` - 升級到 WhisperX，提升字幕質量
- `v2.2.0` - 單語/雙語模式和 CC 按鈕同步
- `v2.3.0` - 播放速度控制和 PiP 改進
- `v2.4.0` - 多語言自動檢測和智能翻譯
- `v2.4.1` - 修復中文影片處理問題
- `v2.4.2` - 修復語言選擇問題和模型優化
- `v2.5.0` - 自訂 HuggingFace 模型、GPU 自動偵測、批量翻譯、ASS 格式（當前版本）

詳細變更請參考 `CHANGELOG.md`。

---

**最後更新**: 2026-04-20
**維護者**: 專案開發團隊
