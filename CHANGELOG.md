# 更新日誌

所有版本變更記錄。每個版本都有對應的 git 標籤，方便查看和切換。

## 如何查看不同版本

```bash
# 查看所有版本標籤
git tag -l

# 查看特定版本的詳細變更
git show v2.4.0

# 切換到特定版本（查看該版本的代碼）
git checkout v2.4.0

# 返回最新版本
git checkout master

# 比較兩個版本的差異
git diff v2.3.0..v2.4.0
```

---

## [v2.5.0] - 2026-04-20

**Git Tag:** `v2.5.0`

### 新功能 🚀

#### 1. 支援自訂 HuggingFace 模型
- `WHISPER_MODEL_SIZE` 現在可填入 HuggingFace repo ID（例如 `MediaTek-Research/Breeze-ASR-26`）
- 支援社群 fine-tuned 模型，大幅提升特定語言（台語、粵語等）的辨識品質
- 自動偵測自訂模型的快取狀態

#### 2. GPU 自動偵測
- 新增 `DEVICE` 環境變數（`auto`/`cpu`/`cuda`）
- `auto` 模式下自動偵測 CUDA GPU，有 GPU 時使用 float16 加速
- 有 GPU 環境轉錄速度提升 **5-10 倍**

#### 3. 翻譯批量化
- 重寫翻譯服務，將多句字幕用 `\n` 合併為單次 Google Translate API 請求
- 100 句字幕從 ~60-90 秒降至 ~5-10 秒（API 呼叫從 100 次降為 2-3 次）
- 批量翻譯失敗時自動降級為逐句翻譯，確保不丟資料

#### 4. 多段語言偵測
- 取音訊的開頭、中間、結尾各 30 秒做語言偵測
- 使用多數決投票確定語言，避免片頭音樂或不同語言段落導致誤判
- 短於 60 秒的音訊維持原有行為

#### 5. ASS 字幕格式支援
- 新增 ASS（Advanced SubStation Alpha）格式導出
- 支援字體樣式、大小、顏色設定（預設 Arial 56pt 白字黑底）
- 前端下載選單新增 ASS 選項
- 新增 API 路由 `/download/{job_id}/{language}/ass`

### 修改的檔案
- `src/config.py` — 新增 `DEVICE` 配置
- `src/services/transcription_service.py` — GPU 偵測、自訂模型、多段語言偵測
- `src/services/translation_service.py` — 完全重寫為批量合併翻譯
- `src/services/subtitle_generator.py` — 新增 `generate_ass_content()`
- `src/main.py` — 新增 ASS 下載路由
- `static/js/app.js` — 前端新增 ASS 格式選項
- `.env` — 新增 `DEVICE=auto` 和自訂模型說明

---

## [v2.4.2] - 2024-03-23

**Git Tag:** `v2.4.2`

### 重要修復 🔥

#### 修復語言選擇被忽略的問題
- **問題**：用戶勾選特定語言（如簡體中文+馬來文），系統仍然翻譯成所有語言（包括繁體中文）
- **根本原因**：`JobManager.process_job()` 忽略用戶選擇，使用自動檢測邏輯決定翻譯語言
- **影響**：浪費處理時間和資源，處理不需要的語言

#### 修復內容
1. **JobManager.process_job()**：
   - 優先使用用戶選擇的 `target_languages`
   - 如果沒有選擇，才使用自動檢測邏輯（向後兼容）
   - 添加日誌記錄使用的語言來源

2. **前端默認狀態**：
   - 移除三個語言的默認勾選（`checked` 屬性）
   - 用戶必須手動選擇需要的語言
   - 避免無意中處理不需要的語言

### 優化改進 ⚡

#### Whisper 模型配置優化
- **問題**：中文和馬來文影片的句子分段質量比英文差
- **原因**：
  - 訓練數據不平衡（英文 70%，中文 5-10%，馬來文 <1%）
  - 語言特性差異（中文無詞間空格，馬來文訓練數據少）
  - 對齊模型影響（部分語言沒有對齊模型）

#### 配置改進
- 將默認模型從 `base` 改為 `small`
- 添加詳細的模型選擇註釋
- 說明不同模型對中文/馬來文分段質量的影響

**模型對比**：
| 模型 | 大小 | 中文/馬來文分段質量 | 處理速度 |
|------|------|-------------------|---------|
| base | 74M | ⭐⭐ 一般 | 快 |
| small | 244M | ⭐⭐⭐ 良好 | 中等 |
| medium | 769M | ⭐⭐⭐⭐ 優秀 | 慢 |
| large | 1550M | ⭐⭐⭐⭐⭐ 極佳 | 很慢 |

### 用戶體驗改進 🎨

- 用戶現在完全控制翻譯語言
- 只處理需要的語言，節省時間
- 更清晰的模型配置說明
- 更好的中文/馬來文分段質量（使用 small 模型）

### 技術細節 🔧

**修改的文件**：
- `src/managers/job_manager.py` - 優先使用用戶選擇的語言
- `static/index.html` - 移除默認勾選
- `.env` - 升級默認模型為 small，添加詳細註釋

**向後兼容**：
- 如果沒有指定 `target_languages`，仍使用自動檢測邏輯
- 不影響現有 API 調用

### 部署步驟 📦

1. 停止服務（Ctrl+C）
2. 重新啟動服務：
   ```bash
   cd video-subtitle-translator
   python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
   ```
3. 首次使用 small 模型會自動下載（~244MB）

### 相關文檔 📚

- [多語言檢測功能](docs/MULTILINGUAL_DETECTION.md)
- [環境配置](.env)

---

## [v2.4.1] - 2024-03-23

**Git Tag:** `v2.4.1`

### 緊急修復 🔥

#### 修復中文影片處理失敗問題
- **問題**：v2.4.0 發布後，中文影片處理失敗並顯示「不支援的語言: zh」
- **根本原因**：
  1. `SubtitleSegment` 模型驗證不接受 `zh` 語言代碼
  2. `TranslationService` 沒有初始化 `zh` 語言的翻譯器
  3. 部分語言（如馬來文）沒有 WhisperX 對齊模型導致處理中斷

#### 修復內容
1. **SubtitleSegment 模型**：添加 `zh` 到支援的語言列表
2. **TranslationService**：
   - 添加 `zh -> en`, `zh -> ms` 等翻譯器
   - 使用 `zh-CN` 作為 `zh` 的源語言（Google Translate 兼容）
3. **TranscriptionService**：
   - 對齊步驟失敗時不中斷處理
   - 使用原始時間戳繼續（記錄警告）

### 技術改進 🔧

- 容錯處理：對齊模型不存在時使用原始時間戳
- 語言映射：`zh` 自動映射到 `zh-CN` 進行翻譯
- 錯誤處理：改進錯誤訊息和日誌記錄

### 測試結果 ✅

- ✅ 中文影片：正常處理，生成 zh-TW.vtt, en.vtt, ms.vtt
- ✅ 英文影片：正常處理，生成 en.vtt, zh-TW.vtt, zh-CN.vtt, ms.vtt
- ✅ 馬來文影片：正常處理（對齊失敗但繼續），生成 ms.vtt, en.vtt, zh-TW.vtt, zh-CN.vtt

### 已知限制 ⚠️

- 混合語言影片（如馬來西亞新聞）：系統檢測主要語言，翻譯可能不完美但可接受
- 部分語言沒有精確對齊模型：使用原始時間戳（準確度略低但可用）

### 相關文檔 📚

- [緊急修復說明](HOTFIX_v2.4.1.md)
- [多語言檢測功能](docs/MULTILINGUAL_DETECTION.md)

---

## [v2.4.0] - 2024-03-23

**Git Tag:** `v2.4.0`

### 重大更新 🎉

#### 多語言影片自動檢測與智能翻譯
- **自動語言檢測**：使用 WhisperX 自動檢測影片語言（支援 99 種語言）
- **智能翻譯邏輯**：根據檢測到的原語言自動選擇翻譯目標語言
  * 英文影片 → 翻譯成：繁中、簡中、馬來文
  * 中文影片 → 翻譯成：英文、馬來文
  * 馬來文影片 → 翻譯成：英文、繁中、簡中
  * 其他語言 → 翻譯成：英文、繁中、馬來文
- **中文簡繁體處理**：中文影片預設生成繁體中文字幕（zh-TW）
- **前端顯示**：結果頁面顯示檢測到的語言信息

### 修復問題 🐛

#### 語言檢測錯誤
- 修復硬編碼 `language="en"` 導致所有字幕被錯誤標記為英文的問題
- 現在正確保留 WhisperX 檢測到的語言代碼
- 中文影片現在會生成中文字幕（而非錯誤的英文標籤）

### 技術改進 🔧

#### TranscriptionService
- 修改 `transcribe()` 方法返回 `(字幕片段列表, 檢測到的語言代碼)`
- 移除硬編碼的 `language="en"`
- 使用 `result["language"]` 獲取檢測到的語言

#### TranslationService
- 新增 `get_target_languages(source_lang)` 靜態方法
- 修改 `translate_segments()` 接受 `source_lang` 參數
- 支援所有語言對的翻譯（en, zh, zh-TW, zh-CN, ms）

#### JobState 資料模型
- 新增 `detected_language` 欄位
- 更新 `to_dict()` 和 `from_dict()` 方法

#### API 變更
- `JobStatusResponse` 新增 `detected_language` 欄位
- `/status/{job_id}` 端點返回檢測到的語言

### 文檔更新 📚

- 新增 `docs/MULTILINGUAL_DETECTION.md`（多語言檢測功能說明）
- 更新 spec 文件（requirements.md, design.md, tasks.md）

### 重要說明 ⚠️

**音訊保持不變**：
- ✅ 系統只提取臨時音訊用於分析
- ✅ 原始影片完全不動
- ✅ 臨時音訊處理後自動刪除
- ✅ 只輸出字幕文件（VTT）
- ❌ 不進行語音合成、配音或音訊替換

---

## [v2.3.0] - 2026-03-22

**Git Tag:** `v2.3.0`

### 新增功能 🚀

#### 播放速度控制
- 新增視頻播放速度控制功能（0.5×、0.75×、1×、1.25×、1.5×、2×、3×）
- 使用下拉選單設計，位於視頻右上角
- 預設速度為 1× 正常播放
- 速度設置會在畫中畫模式下同步

#### 畫中畫模式改進
- 修復畫中畫模式下播放速度不同步的問題
- 畫中畫視頻會自動繼承主視頻的播放速度
- 速度選單改變時會同步更新畫中畫速度

#### 鍵盤快捷鍵優化
- 修復畫中畫模式下鍵盤快捷鍵失效的問題
- 空格鍵、左右方向鍵現在可以正確控制畫中畫視頻
- 根據 `pipActive` 狀態動態選擇控制對象（主視頻或畫中畫視頻）

#### 字幕時間跳轉改進
- 修復畫中畫模式下點擊字幕時間無法控制子畫面的問題
- 點擊字幕時間現在會正確控制畫中畫視頻跳轉並播放
- 同時保持主視頻時間同步

### Bug 修復 🐛

- 修復速度選單事件綁定時機錯誤（元素不存在時綁定失敗）
- 修復全局 `videoPlayer` 變數在頁面加載時為 `null` 的問題
- 修復多處 `videoPlayer is not defined` 錯誤
- 修復瀏覽器記住速度選擇的問題（添加 `autocomplete="off"`）

### 技術改進 ⚙️

#### 前端架構優化
- 移除全局 `videoPlayer` 聲明，改為動態獲取元素
- 在 `showResults()` 函數中綁定速度選單事件（元素顯示後）
- 所有函數改為動態獲取 `videoPlayer` 元素
- 改進 `seekToTime()` 函數支持畫中畫模式
- 改進 `activatePiP()` 函數同步播放速度

#### 緩存控制
- 使用版本號（?v=20260322-003）強制瀏覽器重新加載 JavaScript
- 解決瀏覽器緩存導致更新不生效的問題

### 用戶體驗改進 🎨

- 速度選單位置優化，避免與 PiP 提示重疊
- 添加詳細的控制台日誌，方便調試
- 強制重置速度為 1× 避免混淆

### 測試文件 🧪

- 創建 `tests/` 文件夾存放測試文件
- 移動測試文件到 `tests/` 目錄：
  - `test_keyboard.html` - 鍵盤快捷鍵測試
  - `test_speed_control.html` - 速度控制測試
  - `diagnose.html` - 診斷工具
  - `simple_test.html` - 簡單測試

### 文檔清理 📚

- 移除所有臨時調試和修復文檔
- 保持專案乾淨整潔
- 只保留必要的文檔和測試文件

### 技術細節 🔧

**關鍵技術解決方案：**
1. 事件綁定時機：在 `showResults()` 中綁定，而不是 `setupEventListeners()`
2. 動態獲取元素：不使用全局變數，在需要時動態獲取
3. 畫中畫控制：根據 `pipActive` 狀態選擇控制對象
4. 緩存解決：使用版本號（?v=20260322-003）強制更新

**修改的文件：**
- `static/js/app.js` - 主要邏輯改進（版本：20260322-003）
- `static/index.html` - 添加速度選單和版本號
- `static/css/style.css` - 速度選單樣式

---

## [v2.2.0] - 2026-03-22

**Git Tag:** `v2.2.0`

### 重大功能 🚀

#### 單語/雙語字幕模式
- 新增單語模式：使用原生 HTML5 track，支持全屏播放和 CC 按鈕控制
- 新增雙語模式：自定義渲染，支持主語言+副語言同時顯示
- 用戶可在預覽時自由切換模式
- 雙語模式會提示用戶不支援全屏字幕顯示

#### CC 按鈕與頁面選擇器雙向同步
- 頁面下拉選單選擇語言 → CC 按鈕自動同步
- CC 按鈕選擇語言（全屏時）→ 頁面下拉選單自動更新
- 無論在哪個模式下操作，都會保持同步
- 從雙語模式切換回單語模式時，會記住 CC 按鈕的選擇

#### 字幕編輯改進
- 自動 trim 空白格：編輯時和儲存時都會自動清理多餘空白
- 重置功能改進：永遠回到最初版本，而不是上次儲存的版本
- 儲存後強制刷新預覽：解決瀏覽器緩存導致預覽不更新的問題
- 後端模型層也會自動 trim 文字

### Bug 修復 🐛

#### 字幕顯示問題
- 修復雙語模式下 textTracks 設為 disabled 導致 CC 按鈕無法使用的問題
- 改用 hidden 模式，保持 CC 按鈕可用性
- 修復切換模式時字幕殘留的問題

#### 儲存和重置問題
- 修復儲存後預覽不更新的問題（緩存問題）
- 修復重置功能時好時壞的問題
- 新增 initialSubtitlesCache 來保存每個語言的初始版本

### 技術改進 ⚙️

#### 前端架構
- 新增 `initializeAllTracks()` 函數：統一管理所有語言的 track 元素
- 新增 `setupTextTrackSync()` 函數：監聽 textTracks 變化並同步到頁面
- 改進 `handleSubtitleModeChange()` 函數：切換模式時同步 CC 狀態
- 改進 `loadVideoSubtitle()` 函數：區分單語和雙語的 track 處理邏輯

#### 後端改進
- `SubtitleSegment` 模型在 `__post_init__` 時自動 trim 文字
- 確保所有字幕文字都沒有多餘空白

### 用戶體驗改進 🎨

- 單語模式提示：「💡 單語模式支持全屏播放和 CC 按鈕控制」
- 雙語模式警告：「⚠️ 雙語模式不支援全屏播放，如需全屏請切換為單語模式」
- 重置確認訊息更清楚：「確定要重置到最初版本嗎？所有修改都會遺失。」
- 儲存成功後自動刷新預覽，無需手動切換語言

### 文檔更新 📚

- 新增 `QUICKSTART_v2.2.md` - 快速開始指南
- 新增 `docs/DEPENDENCY_CLEANUP.md` - 依賴清理記錄
- 更新 `docs/README.md` - 文檔索引

### 技術細節 🔧

**關鍵技術解決方案：**
1. 使用 `hidden` 而非 `disabled` 來隱藏 textTracks（保持 CC 按鈕可用）
2. 使用 `initialSubtitlesCache` 物件緩存每個語言的初始版本
3. 儲存後使用 `?t=${Date.now()}` 時間戳避免緩存
4. 監聽 `textTracks.change` 事件實現雙向同步

**修改的文件：**
- `static/js/app.js` - 主要邏輯改進
- `static/css/style.css` - 樣式調整
- `static/index.html` - UI 結構優化
- `src/models/subtitle.py` - 自動 trim 功能
- `docs/README.md` - 文檔更新

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
