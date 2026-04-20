# 專案結構

## 目錄結構

```
video-subtitle-translator/
├── .git/                    # Git 版本控制
├── .vscode/                 # VS Code 設置
├── docs/                    # 開發文檔
│   ├── DEPENDENCY_CLEANUP.md
│   ├── FUTURE_FEATURES.md
│   ├── README.md
│   └── WHISPERX_SEGMENTATION.md
├── logs/                    # 應用日誌
│   └── app.log
├── src/                     # 後端源代碼
│   ├── models/              # 數據模型
│   ├── routes/              # API 路由
│   ├── services/            # 業務邏輯
│   └── utils/               # 工具函數
├── static/                  # 前端資源
│   ├── css/                 # 樣式文件
│   ├── js/                  # JavaScript 文件
│   └── index.html           # 主頁面
├── storage/                 # 舊存儲目錄（已棄用，檔案改存至外部路徑）
│   └── jobs/                # 僅保留舊任務狀態（新任務存至 BASE_STORAGE_PATH）
├── tests/                   # 測試文件
│   ├── diagnose.html        # 診斷工具
│   ├── simple_test.html     # 簡單測試
│   ├── test_keyboard.html   # 鍵盤測試
│   ├── test_speed_control.html  # 速度控制測試
│   ├── integration/         # 集成測試
│   ├── property/            # 屬性測試
│   └── unit/                # 單元測試
├── tools/                   # 工具腳本
│   ├── CLEAN_STORAGE.ps1    # 清理存儲空間腳本
│   ├── check_versions.py    # 版本檢查工具
│   ├── README.txt           # 工具說明
│   └── 如何清理存儲空間.txt  # 清理指南
├── venv/                    # Python 虛擬環境
├── .env                     # 環境變數（不提交）
├── .env.example             # 環境變數範例
├── .gitignore               # Git 忽略規則
├── CHANGELOG.md             # 版本更新日誌
├── check_versions.py        # 版本檢查工具
├── DESIGN.md                # 技術設計文檔
├── GIT_COMMIT_GUIDE.md      # Git 提交指南
├── INSTALLATION.md          # 安裝指南
├── MAINTENANCE.md           # 維護指南
├── OPTIMIZATION_NOTES.md    # 優化記錄
├── PROJECT_STRUCTURE.md     # 專案結構（本文件）
├── README.md                # 專案說明
├── requirements.txt         # Python 依賴
├── requirements-frozen.txt  # 凍結的依賴版本
├── requirements-locked.txt  # 鎖定的依賴版本
├── START.bat                # 啟動腳本
├── 清理存儲空間.bat          # 清理存儲空間快捷方式
├── UPGRADE_WHISPERX.md      # WhisperX 升級記錄
├── VERSION_TAG.md           # 版本標籤指南
└── 使用說明.txt             # 中文使用說明
```

## 核心文件說明

### 配置文件
- `.env` - 環境變數（包含敏感信息，不提交到 Git）
- `.env.example` - 環境變數範例
- `.gitignore` - Git 忽略規則
- `requirements.txt` - Python 依賴列表

### 文檔文件
- `README.md` - 專案主要說明文檔
- `CHANGELOG.md` - 版本更新日誌
- `INSTALLATION.md` - 詳細安裝指南
- `MAINTENANCE.md` - 維護和故障排除
- `DESIGN.md` - 技術設計和架構
- `OPTIMIZATION_NOTES.md` - 性能優化記錄
- `UPGRADE_WHISPERX.md` - WhisperX 升級過程

### 指南文件
- `GIT_COMMIT_GUIDE.md` - Git 提交指南
- `VERSION_TAG.md` - 版本標籤使用指南
- `PROJECT_STRUCTURE.md` - 專案結構說明（本文件）

### 啟動和工具文件
- `START.bat` - Windows 啟動腳本
- `清理存儲空間.bat` - 清理存儲空間快捷方式（調用 tools/CLEAN_STORAGE.ps1）

### 工具文件夾
- `tools/` - 包含各種工具腳本
  - `CLEAN_STORAGE.ps1` - 清理存儲空間腳本
  - `check_versions.py` - 版本檢查工具
  - `README.txt` - 工具說明

## storage/ 目錄說明

`storage/` 是系統運行時的數據存儲目錄，會隨著使用累積大量文件：

### storage/uploads/
存放用戶上傳的視頻文件（.mp4, .avi, .mov, .mkv 等）
- 每個視頻以 UUID 命名
- 可能佔用大量磁盤空間
- 可以安全刪除（需要時重新上傳）

### storage/subtitles/
存放生成的字幕文件（.vtt, .srt）
- 每個任務有獨立的子文件夾（以 UUID 命名）
- 包含原始英文字幕和翻譯後的字幕
- 可以安全刪除（需要時重新生成）

### storage/jobs/
存放任務狀態信息（.json）
- 記錄每個任務的處理狀態和進度
- 用於恢復中斷的任務
- 可以安全刪除舊任務記錄

### 清理建議
- 定期清理以釋放磁盤空間
- 使用 `CLEAN_STORAGE.bat` 快速清理
- 或參考 `如何清理存儲空間.txt` 手動清理
- 系統有自動清理功能（預設保留 24 小時）

## 重要目錄說明

### src/ - 後端源代碼
包含所有 Python 後端代碼：
- `models/` - 數據模型定義
- `routes/` - FastAPI 路由處理
- `services/` - 核心業務邏輯（轉錄、翻譯）
- `utils/` - 工具函數

### static/ - 前端資源
包含所有前端文件：
- `index.html` - 主頁面
- `css/style.css` - 樣式文件
- `js/app.js` - 主要 JavaScript 邏輯

### storage/ - 存儲目錄
運行時生成的文件：
- `uploads/` - 用戶上傳的視頻
- `subtitles/` - 生成的字幕文件
- `jobs/` - 任務狀態和元數據

### tests/ - 測試文件
包含各種測試文件：
- HTML 測試頁面（用於前端功能測試）
- 單元測試、集成測試、屬性測試

### docs/ - 開發文檔
包含開發相關的詳細文檔

## 版本控制

### Git 標籤
專案使用 Git 標籤標記版本：
- `v1.0.0` - 初始版本
- `v2.0.0` - 視頻播放器和編輯器
- `v2.1.0` - WhisperX 升級
- `v2.2.0` - 單語/雙語模式
- `v2.3.0` - 播放速度控制（當前版本）

### 查看版本
```bash
# 列出所有版本
git tag -l

# 切換到特定版本
git checkout v2.3.0

# 返回最新版本
git checkout master
```

## 依賴管理

### Python 依賴
- `requirements.txt` - 主要依賴列表
- `requirements-frozen.txt` - 凍結版本（pip freeze 輸出）
- `requirements-locked.txt` - 鎖定版本（手動維護）

### 安裝依賴
```bash
pip install -r requirements.txt
```

## 開發工作流

1. 修改代碼
2. 測試功能
3. 更新文檔
4. 提交更改
5. 創建版本標籤
6. 推送到遠程倉庫

詳細步驟請參考 `GIT_COMMIT_GUIDE.md`

## 清理規則

### 自動忽略（.gitignore）
- Python 緩存文件（`__pycache__/`, `*.pyc`）
- 虛擬環境（`venv/`）
- 環境變數（`.env`）
- 日誌文件（`logs/`, `*.log`）
- 存儲文件（`storage/`）
- 臨時文件（`*.tmp`, `*.bak`）
- 臨時調試文檔（`*_FIX.md`, `*_DEBUG.txt` 等）

### 手動清理
定期清理 `storage/` 目錄中的舊文件

## 維護建議

1. 定期更新依賴版本（謹慎測試）
2. 定期清理存儲文件
3. 定期備份重要數據
4. 保持文檔更新
5. 記錄重要變更

詳細維護指南請參考 `MAINTENANCE.md`
