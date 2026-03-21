# 更新日誌

所有版本變更記錄。每個版本都有對應的 git 標籤，方便查看和切換。

## 如何查看不同版本

```bash
# 查看所有版本標籤
git tag -l

# 查看特定版本的詳細變更
git show v2.1.0

# 切換到特定版本（查看該版本的代碼）
git checkout v2.1.0

# 返回最新版本
git checkout master

# 比較兩個版本的差異
git diff v2.0.0..v2.1.0
```

---

## [v2.1.0] - 2026-03-21

**Git Tag:** `v2.1.0` | **Commit:** `edfc4e6`

### 重大升級 🚀

#### 升級到 WhisperX 3.7.2
- 從 OpenAI Whisper 升級到 WhisperX，字幕質量顯著提升
- 使用 forced alignment 技術，提供更精確的時間戳
- 句子分段更自然完整，不再斷斷續續
- 詳細升級過程請參考 [UPGRADE_WHISPERX.md](UPGRADE_WHISPERX.md)

#### 技術改進
- 升級到 PyTorch 2.8.0 + torchaudio 2.8.0
- 實現模型延遲載入機制（應用啟動更快）
- 解決 PyTorch 2.8.0 的 weights_only 安全限制問題
- 完整的試錯過程記錄在 [INSTALLATION.md](INSTALLATION.md)

### Bug 修復 🐛

#### 字幕顯示問題
- 修復單語模式下副字幕（小黑框）仍然顯示的問題
- 現在只有在選擇「雙語」模式時才會顯示副字幕
- 改善觀看體驗，避免不必要的字幕干擾
- 相關文件：`static/js/app.js` - `updateCustomSubtitles()` 函數

### 文檔更新 📚

- 新增 [INSTALLATION.md](INSTALLATION.md) - 完整安裝指南，包含：
  - 快速開始指南
  - 詳細安裝步驟
  - 依賴版本列表（經過測試的穩定版本）
  - 完整的試錯過程記錄（4 個主要問題及解決方案）
  - 常見問題 FAQ
- 更新 [UPGRADE_WHISPERX.md](UPGRADE_WHISPERX.md) - 詳細試錯過程，包含：
  - WhisperX 版本選擇問題
  - PyTorch 版本兼容性問題（3 次嘗試）
  - weights_only 安全限制問題（3 次嘗試）
  - 模型載入時機優化
- 更新 README.md 添加文檔索引和 WhisperX 優勢說明
- 更新 design.md 和 tasks.md 反映技術棧變更

### 技術細節 🔧

**依賴版本（經過驗證的穩定組合）：**
```
whisperx==3.7.2
torch==2.8.0
torchaudio==2.8.0
```

**關鍵技術解決方案：**
1. 局部 torch.load monkey patch（解決 weights_only 問題）
2. 延遲載入模型機制（改善啟動速度）
3. 模式檢查邏輯（修復字幕顯示 bug）

---

## [v2.0.0] - 2026-03-20

**Git Tag:** `v2.0.0` | **Commit:** `845c5a9`

### 新增功能 ✨

#### 影片播放器
- 在結果頁面直接播放上傳的影片
- HTML5 video player，支持所有主流瀏覽器
- 響應式設計，自動適應螢幕大小

#### 字幕編輯器
- 直接在頁面上編輯字幕內容
- 點擊字幕文字即可編輯
- 支持多語言切換編輯
- 即時預覽編輯效果

#### 字幕同步功能
- 影片播放時自動高亮當前字幕
- 自動滾動到當前播放位置的字幕
- 點擊字幕時間可跳轉影片到該位置
- 完美的影片與字幕同步體驗

#### 批量下載
- 一鍵下載所有生成的字幕文件
- 可選擇是否包含影片文件
- 自動打包成 ZIP 文件
- 使用原始影片名稱命名

#### SRT 格式支持
- 除了 VTT 格式，現在也支持 SRT 格式
- SRT 格式更通用，兼容更多播放器
- 每個語言都提供 VTT 和 SRT 兩種格式

#### 字幕儲存功能
- 編輯後可儲存到服務器
- 支持重置到原始翻譯版本
- 避免刷新頁面丟失編輯內容

### 後端 API 擴展 🔧

- `GET /video/{job_id}` - 獲取影片文件用於播放
- `PUT /subtitle/{job_id}/{language}` - 更新編輯後的字幕
- `GET /download-all/{job_id}` - 批量下載所有字幕（ZIP）
- `GET /download/{job_id}/{language}/srt` - 下載 SRT 格式字幕

### 用戶界面改進 🎨

- 全新的結果頁面佈局
- 影片播放器置頂，方便觀看
- 字幕編輯器支持實時編輯
- 改進的下載按鈕佈局
- 更好的響應式設計

### 技術改進 ⚙️

- 添加 SRT 格式生成器
- 優化字幕解析邏輯
- 改進錯誤處理
- 添加成功提示訊息

---

## [v1.0.0] - 2026-03-20

**Git Tag:** `v1.0.0` | **Commit:** `2eab8cc`

### 初始版本 🎉

#### 核心功能
- 使用 WhisperX 自動轉錄影片為英文字幕（提供精確時間戳和完整句子）
- 支持選擇性翻譯（繁體中文、簡體中文、馬來文）
- Web 界面上傳和下載
- 字幕預覽功能
- 本地處理，無需上傳雲端

#### 技術棧
- 後端：FastAPI + Whisper + deep-translator
- 前端：HTML + CSS + JavaScript
- 字幕格式：VTT

#### 支持格式
- 影片：MP4, AVI, MOV, MKV
- 最大文件：5GB
- 最長時長：2 小時
