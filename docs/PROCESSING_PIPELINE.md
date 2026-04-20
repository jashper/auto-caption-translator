# 系統處理流程完整說明

## 概述

本文檔詳細說明從影片上傳到字幕下載的完整處理流程，包括每個步驟的技術實現和負責模組。

## 完整 Pipeline 流程圖

```
用戶上傳影片 + 選擇語言
         ↓
    [前端 JavaScript]
         ↓
    POST /upload (FastAPI)
         ↓
    [後端：JobManager]
         ↓
┌────────────────────────────────────┐
│  步驟 1：音訊提取                    │
│  負責：TranscriptionService         │
│  工具：FFmpeg                       │
│  輸出：臨時 WAV 音訊檔案              │
└────────────────────────────────────┘
         ↓
┌────────────────────────────────────┐
│  步驟 2：語音辨識 + 語言檢測          │
│  負責：TranscriptionService         │
│  模型：WhisperX (Whisper + 對齊)    │
│  輸出：原語言字幕片段 + 檢測語言      │
└────────────────────────────────────┘
         ↓
┌────────────────────────────────────┐
│  步驟 3：決定翻譯目標語言             │
│  負責：JobManager                   │
│  邏輯：優先使用用戶選擇               │
│  輸出：目標語言列表                  │
└────────────────────────────────────┘
         ↓
┌────────────────────────────────────┐
│  步驟 4：翻譯字幕                    │
│  負責：TranslationService           │
│  工具：Google Translate API         │
│  輸出：每種語言的翻譯字幕片段         │
└────────────────────────────────────┘
         ↓
┌────────────────────────────────────┐
│  步驟 5：生成字幕檔案                │
│  負責：SubtitleGenerator            │
│  格式：VTT (主要格式)               │
│  輸出：每種語言的 .vtt 檔案          │
└────────────────────────────────────┘
         ↓
    任務完成，返回結果
         ↓
    [前端顯示結果]
         ↓
    用戶下載字幕
         ↓
┌────────────────────────────────────┐
│  下載時格式轉換（按需）               │
│  VTT → SRT/ASS 轉換                    │
│  負責：SubtitleGenerator (後端)     │
│  觸發：用戶點擊 SRT/ASS 下載按鈕       │
└────────────────────────────────────┘
```

---

## 詳細流程說明

### 步驟 1：用戶上傳與語言選擇

**負責模組**：前端 JavaScript (`static/js/app.js`)

**流程**：

1. 用戶選擇影片檔案
2. 用戶勾選需要的翻譯語言（繁中、簡中、馬來文）
3. 點擊「開始處理」按鈕

**代碼位置**：
```javascript
// static/js/app.js - uploadFile()
const checkboxes = document.querySelectorAll('input[name="target-language"]:checked');
const targetLanguages = Array.from(checkboxes).map(cb => cb.value);

const formData = new FormData();
formData.append('file', selectedFile);
formData.append('target_languages', targetLanguages.join(','));

const response = await fetch('/upload', {
    method: 'POST',
    body: formData
});
```

**輸出**：
- 影片檔案
- 目標語言列表（例如：`"zh-TW,zh-CN,ms"`）

---

### 步驟 2：後端接收與任務創建

**負責模組**：FastAPI 主應用 (`src/main.py`)

**流程**：
1. 接收上傳的影片和語言選擇
2. 驗證檔案格式和大小
3. 創建任務並保存影片
4. 將任務加入處理佇列

**代碼位置**：
```python
# src/main.py - upload_video()
@app.post("/upload")
async def upload_video(file: UploadFile, target_languages: str):
    # 解析目標語言
    languages = [lang.strip() for lang in target_languages.split(',')]
    
    # 創建任務
    job_id = job_manager.create_job(file.filename, "", languages)
    
    # 保存影片
    video_path = await file_storage.save_uploaded_file(file, job_id)
    
    # 加入處理佇列
    await task_queue.enqueue(job_id, job_manager.process_job, job_id)
```

**輸出**：
- 任務 ID (job_id)
- 任務狀態：queued

---

### 步驟 3：音訊提取

**負責模組**：TranscriptionService (`src/services/transcription_service.py`)

**使用工具**：FFmpeg

**流程**：
1. 從影片中提取音訊
2. 轉換為 16kHz 單聲道 WAV 格式
3. 保存為臨時檔案

**代碼位置**：
```python
# src/services/transcription_service.py - extract_audio()
def extract_audio(self, video_path: str) -> str:
    audio_path = video_path.rsplit('.', 1)[0] + '_audio.wav'
    
    ffmpeg.input(video_path) \
        .output(audio_path, acodec='pcm_s16le', ac=1, ar='16k') \
        .overwrite_output() \
        .run(quiet=True)
    
    return audio_path
```

**輸出**：
- 臨時音訊檔案（WAV 格式）
- 處理完成後會自動刪除

---

### 步驟 4：語音辨識與語言檢測

**負責模組**：TranscriptionService (`src/services/transcription_service.py`)

**使用模型**：WhisperX（基於 OpenAI Whisper）

**流程**：
1. 載入 WhisperX 模型（small/medium/large）
2. 自動檢測語言（99 種語言支援）
3. 轉錄為原語言文字
4. 使用對齊模型精確時間戳（如果可用）
5. 生成字幕片段（包含時間軸和文字）

**代碼位置**：
```python
# src/services/transcription_service.py - transcribe()
async def transcribe(self, video_path: str) -> tuple[List[SubtitleSegment], str]:
    # 提取音訊
    audio_path = self.extract_audio(video_path)
    audio = whisperx.load_audio(audio_path)
    
    # 步驟 4.1：轉錄 + 語言檢測
    result = self.model.transcribe(audio, batch_size=16)
    detected_language = result.get("language", "en")  # 例如：'en', 'zh', 'ms'
    
    # 步驟 4.2：精確對齊（如果支援）
    try:
        align_model, metadata = whisperx.load_align_model(
            language_code=detected_language, 
            device=self.device
        )
        result = whisperx.align(result["segments"], align_model, metadata, audio, self.device)
    except Exception as e:
        # 對齊失敗時使用原始時間戳
        logger.warning(f"對齊失敗，使用原始時間戳: {e}")
    
    # 步驟 4.3：轉換為 SubtitleSegment 對象
    segments = []
    for idx, segment in enumerate(result['segments'], start=1):
        subtitle_segment = SubtitleSegment(
            index=idx,
            start_time=segment['start'],
            end_time=segment['end'],
            text=segment['text'].strip(),
            language=detected_language
        )
        segments.append(subtitle_segment)
    
    return segments, detected_language
```

**輸出**：
- 原語言字幕片段列表（SubtitleSegment 對象）
- 檢測到的語言代碼（例如：'en', 'zh', 'ms'）

**示例輸出**：
```python
segments = [
    SubtitleSegment(index=1, start_time=0.0, end_time=2.5, text="Hello world", language="en"),
    SubtitleSegment(index=2, start_time=2.5, end_time=5.0, text="How are you", language="en"),
]
detected_language = "en"
```

---

### 步驟 5：決定翻譯目標語言

**負責模組**：JobManager (`src/managers/job_manager.py`)

**邏輯**：v2.4.2 版本更新

**流程**：


**情況 1：用戶有選擇語言（v2.4.2 優先）**
```python
# src/managers/job_manager.py - process_job()
if state.target_languages:
    # 使用用戶選擇的語言
    target_languages = state.target_languages  # 例如：['zh-CN', 'ms']
    logger.info(f"使用用戶選擇的語言: {', '.join(target_languages)}")
```

**情況 2：用戶沒有選擇（自動檢測，向後兼容）**
```python
else:
    # 根據檢測到的語言自動決定
    target_languages = TranslationService.get_target_languages(detected_language)
    logger.info(f"自動選擇翻譯語言: {', '.join(target_languages)}")
```

**自動檢測邏輯**：
```python
# src/services/translation_service.py - get_target_languages()
@staticmethod
def get_target_languages(source_lang: str) -> List[str]:
    if source_lang == 'en':
        return ['zh-TW', 'zh-CN', 'ms']  # 英文 → 繁中、簡中、馬來文
    elif source_lang == 'zh':
        return ['en', 'ms']  # 中文 → 英文、馬來文
    elif source_lang == 'ms':
        return ['en', 'zh-TW', 'zh-CN']  # 馬來文 → 英文、繁中、簡中
    else:
        return ['en', 'zh-TW', 'ms']  # 其他 → 英文、繁中、馬來文
```

**輸出**：
- 目標語言列表（例如：`['zh-TW', 'zh-CN', 'ms']`）

**示例場景**：

| 檢測語言 | 用戶選擇 | 最終翻譯目標 |
|---------|---------|------------|
| en | zh-CN, ms | zh-CN, ms（用戶選擇優先）|
| en | 無 | zh-TW, zh-CN, ms（自動）|
| zh | zh-CN | zh-CN（用戶選擇優先）|
| zh | 無 | en, ms（自動）|

---

### 步驟 6：翻譯字幕

**負責模組**：TranslationService (`src/services/translation_service.py`)

**使用工具**：Google Translate API（通過 deep-translator）

**流程**：
1. 為每種目標語言創建翻譯器
2. 批次翻譯字幕片段（每批 20 個）
3. 添加隨機延遲避免速率限制
4. 保留原始時間軸，只翻譯文字

**代碼位置**：
```python
# src/services/translation_service.py - translate_segments()
async def translate_segments(
    self,
    segments: List[SubtitleSegment],
    source_lang: str,  # 例如：'en'
    target_lang: str   # 例如：'zh-TW'
) -> List[SubtitleSegment]:
    
    translator_key = f"{source_lang}->{target_lang}"
    translator = self.translators[translator_key]
    
    translated_segments = []
    
    # 批次翻譯
    for batch_idx in range(0, len(segments), self.BATCH_SIZE):
        batch = segments[batch_idx:batch_idx + self.BATCH_SIZE]
        
        for segment in batch:
            # 翻譯文字
            translated_text = await self._translate_text(
                segment.text,
                source_lang,
                target_lang,
                translator
            )
            
            # 創建翻譯後的片段（保留時間軸）
            translated_segment = SubtitleSegment(
                index=segment.index,
                start_time=segment.start_time,  # 保留原始時間
                end_time=segment.end_time,      # 保留原始時間
                text=translated_text,           # 翻譯後的文字
                language=target_lang
            )
            translated_segments.append(translated_segment)
            
            # 隨機延遲避免速率限制
            await asyncio.sleep(random.uniform(0.3, 0.8))
        
        # 批次間延遲
        await asyncio.sleep(2.0)
    
    return translated_segments
```

**輸出**：
- 每種目標語言的翻譯字幕片段列表

**示例**：
```python
# 原始英文字幕
en_segments = [
    SubtitleSegment(index=1, start_time=0.0, end_time=2.5, text="Hello world", language="en"),
]

# 翻譯成繁體中文
zh_tw_segments = [
    SubtitleSegment(index=1, start_time=0.0, end_time=2.5, text="你好世界", language="zh-TW"),
]

# 翻譯成馬來文
ms_segments = [
    SubtitleSegment(index=1, start_time=0.0, end_time=2.5, text="Halo dunia", language="ms"),
]
```

---

### 步驟 7：生成 VTT 字幕檔案

**負責模組**：SubtitleGenerator (`src/services/subtitle_generator.py`)

**格式**：VTT（WebVTT）- 主要格式

**流程**：
1. 為每種語言生成 VTT 檔案
2. 包含原語言字幕
3. 包含所有翻譯語言字幕

**代碼位置**：
```python
# src/managers/job_manager.py - process_job()
subtitle_files = {}

# 原語言字幕
source_lang_code = detected_language
if source_lang_code == 'zh':
    source_lang_code = 'zh-TW'  # 中文使用繁體

source_path = self.file_storage.get_subtitle_path(job_id, source_lang_code)
self.subtitle_generator.generate_vtt(source_segments, source_path, source_lang_code)
subtitle_files[source_lang_code] = source_path

# 翻譯後的字幕
for lang, segments in translations.items():
    lang_path = self.file_storage.get_subtitle_path(job_id, lang)
    self.subtitle_generator.generate_vtt(segments, lang_path, lang)
    subtitle_files[lang] = lang_path
```

**VTT 生成邏輯**：
```python
# src/services/subtitle_generator.py - generate_vtt()
def generate_vtt(self, segments: List[SubtitleSegment], output_path: str, language: str):
    with open(output_path, 'w', encoding='utf-8') as f:
        # VTT 標頭
        f.write('WEBVTT\n\n')
        
        # 寫入每個字幕片段
        for segment in segments:
            start = segment.format_vtt_timestamp(segment.start_time)
            end = segment.format_vtt_timestamp(segment.end_time)
            f.write(f'{segment.index}\n')
            f.write(f'{start} --> {end}\n')
            f.write(f'{segment.text}\n\n')
```

**輸出檔案**：
```
storage/jobs/{job_id}/subtitles/
├── en.vtt          # 英文原字幕
├── zh-TW.vtt       # 繁體中文翻譯
├── zh-CN.vtt       # 簡體中文翻譯
└── ms.vtt          # 馬來文翻譯
```

**VTT 檔案內容示例**：
```
WEBVTT

1
00:00:00.000 --> 00:00:02.500
你好世界

2
00:00:02.500 --> 00:00:05.000
你好嗎
```

---

### 步驟 8：任務完成與結果返回

**負責模組**：JobManager + FastAPI

**流程**：


1. 標記任務為完成
2. 保存字幕檔案路徑
3. 前端輪詢獲取結果

**代碼位置**：
```python
# src/managers/job_manager.py - process_job()
self.mark_job_completed(job_id, subtitle_files)

# src/main.py - get_job_status()
@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    state = job_manager.get_job_status(job_id)
    return JobStatusResponse(
        job_id=state.job_id,
        status=state.status.value,  # "completed"
        progress=state.progress,     # 100
        detected_language=state.detected_language,
        subtitle_files=state.subtitle_files  # 字幕檔案路徑
    )
```

**前端輪詢**：
```javascript
// static/js/app.js - checkStatus()
async function checkStatus() {
    const response = await fetch(`/status/${currentJobId}`);
    const data = await response.json();
    
    if (data.status === 'completed') {
        stopPolling();
        showResults(data.subtitle_files, data.detected_language);
    }
}
```

---

### 步驟 9：前端顯示結果

**負責模組**：前端 JavaScript (`static/js/app.js`)

**流程**：
1. 顯示檢測到的語言
2. 載入影片播放器
3. 生成下載按鈕列表
4. 初始化字幕選擇器

**代碼位置**：
```javascript
// static/js/app.js - showResults()
function showResults(subtitleFiles, detectedLanguage) {
    // 顯示檢測語言
    languageInfo.innerHTML = `檢測到的語言：${detectedLangName} (${detectedLanguage})`;
    
    // 設定影片播放器
    videoPlayer.src = `/video/${currentJobId}`;
    
    // 生成下載列表
    for (const lang of Object.keys(subtitleFiles)) {
        // 創建下載按鈕（VTT 和 SRT）
        const row = document.createElement('div');
        row.innerHTML = `
            <select class="format-select-compact">
                <option value="vtt">VTT</option>
                <option value="srt">SRT</option>
            </select>
            <button class="btn">下載</button>
        `;
        downloadList.appendChild(row);
    }
}
```

---

### 步驟 10：用戶下載字幕（VTT 或 SRT）

**重要**：這是回答你問題的關鍵部分！

#### 10.1 下載 VTT 格式（直接下載）

**負責模組**：後端 FastAPI (`src/main.py`)

**流程**：
- 直接返回已生成的 VTT 檔案
- 不需要轉換

**代碼位置**：
```python
# src/main.py - download_subtitle()
@app.get("/download/{job_id}/{language}")
async def download_subtitle(job_id: str, language: str):
    subtitle_path = file_storage.get_subtitle_path(job_id, language)
    
    return FileResponse(
        subtitle_path,
        media_type="text/vtt",
        filename=f"{video_filename}_{language}.vtt"
    )
```

**技術實現**：後端直接返回檔案

---

#### 10.2 下載 SRT 格式（即時轉換）

**負責模組**：後端 SubtitleGenerator (`src/services/subtitle_generator.py`)

**流程**：
1. 讀取 VTT 檔案
2. 解析為 SubtitleSegment 對象
3. 轉換為 SRT 格式
4. 返回 SRT 內容

**代碼位置**：
```python
# src/main.py - download_subtitle_srt()
@app.get("/download/{job_id}/{language}/srt")
async def download_subtitle_srt(job_id: str, language: str):
    # 讀取 VTT 字幕
    vtt_path = file_storage.get_subtitle_path(job_id, language)
    segments = subtitle_generator.parse_vtt(vtt_path)
    
    # 轉換為 SRT 格式
    srt_content = subtitle_generator.generate_srt_content(segments)
    
    # 返回 SRT 文件
    return StreamingResponse(
        io.BytesIO(srt_content.encode('utf-8')),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={filename}.srt"}
    )
```

**SRT 生成邏輯**：
```python
# src/services/subtitle_generator.py - generate_srt_content()
def generate_srt_content(self, segments: List[SubtitleSegment]) -> str:
    srt_lines = []
    
    for segment in segments:
        # SRT 格式時間戳（使用逗號而非點）
        start = segment.format_srt_timestamp(segment.start_time)
        end = segment.format_srt_timestamp(segment.end_time)
        
        srt_lines.append(f'{segment.index}')
        srt_lines.append(f'{start} --> {end}')
        srt_lines.append(segment.text)
        srt_lines.append('')  # 空行
    
    return '\n'.join(srt_lines)
```

**技術實現**：後端即時轉換

**SRT 格式示例**：
```
1
00:00:00,000 --> 00:00:02,500
你好世界

2
00:00:02,500 --> 00:00:05,000
你好嗎
```

---

## 問題解答總結

### 1. 語言處理流程

**Q: 當系統檢測到輸入語言為「英文」時，是否會自動翻譯為多語言？**

**A:** 取決於版本和用戶選擇：

- **v2.4.2（當前版本）**：
  - 優先使用用戶選擇的語言
  - 如果用戶勾選「簡中 + 馬來文」→ 只翻譯這兩種
  - 如果用戶沒有勾選任何語言 → 顯示錯誤
  - 如果沒有傳遞語言參數（API 調用）→ 使用自動檢測邏輯

- **自動檢測邏輯（向後兼容）**：
  - 英文影片 → 自動翻譯成：繁中、簡中、馬來文
  - 中文影片 → 自動翻譯成：英文、馬來文
  - 馬來文影片 → 自動翻譯成：英文、繁中、簡中

**Q: 多語言翻譯是如何觸發的？**

**A:** 
1. 用戶在前端勾選需要的語言
2. 前端將選擇發送到後端（`target_languages` 參數）
3. 後端優先使用用戶選擇
4. 沒有選擇時才使用自動檢測邏輯

---

### 2. 字幕生成流程

**Q: 翻譯完成後，是否會針對每一種語言分別生成字幕？**

**A:** 是的！

- 原語言字幕：1 個 VTT 檔案
- 每種翻譯語言：1 個 VTT 檔案
- 總共：1 + N 個 VTT 檔案（N = 用戶選擇的語言數量）

**示例**：
```
英文影片 + 用戶選擇「簡中、馬來文」
→ 生成 3 個 VTT 檔案：
  - en.vtt（原語言）
  - zh-CN.vtt（簡體中文翻譯）
  - ms.vtt（馬來文翻譯）
```

**Q: 是否會將每種語言的字幕各自轉換為 SRT 和 VTT 格式？**

**A:** 不完全是！

- **VTT 格式**：在處理完成時就生成並保存
- **SRT 格式**：不預先生成，只在用戶下載時即時轉換

**原因**：
- VTT 是主要格式，用於網頁播放器
- SRT 只在需要時才轉換，節省儲存空間
- 轉換速度很快（毫秒級），不影響用戶體驗

---

### 3. 技術實現方式

**Q: 翻譯後的字幕生成與格式轉換（SRT / VTT）是完全由前端 JavaScript 處理，還是由後端模型 / API 負責生成？**

**A:** 完全由後端處理！

| 功能 | 負責模組 | 時機 |
|------|---------|------|
| VTT 生成 | 後端 SubtitleGenerator | 處理完成時 |
| SRT 轉換 | 後端 SubtitleGenerator | 用戶下載時 |
| 字幕顯示 | 前端 JavaScript | 播放時 |
| 字幕編輯 | 前端 JavaScript | 編輯時 |
| 字幕保存 | 後端 API | 保存時 |

**前端 JavaScript 的職責**：
- 上傳影片和語言選擇
- 顯示處理進度
- 播放影片和同步字幕
- 編輯字幕內容
- 觸發下載

**後端的職責**：
- 語音辨識（WhisperX）
- 翻譯（Google Translate）
- 生成 VTT 檔案
- 轉換 SRT 格式
- 儲存和管理檔案

---

### 4. 整體流程總結

```
完整 Pipeline（標註負責模組）
═══════════════════════════════════════════════════════════

1. 用戶上傳影片 + 選擇語言
   └─ 前端 JavaScript (app.js)

2. 後端接收與驗證
   └─ FastAPI (main.py)

3. 音訊提取
   └─ TranscriptionService + FFmpeg

4. 語音辨識 + 語言檢測
   └─ TranscriptionService + WhisperX 模型
   └─ 輸出：原語言字幕 + 檢測語言

5. 決定翻譯目標
   └─ JobManager
   └─ 邏輯：用戶選擇 > 自動檢測

6. 翻譯字幕
   └─ TranslationService + Google Translate API
   └─ 輸出：每種語言的翻譯字幕

7. 生成 VTT 檔案
   └─ SubtitleGenerator
   └─ 輸出：原語言 + 所有翻譯語言的 VTT 檔案

8. 任務完成
   └─ JobManager 標記完成
   └─ FastAPI 返回結果

9. 前端顯示結果
   └─ 前端 JavaScript
   └─ 顯示影片播放器 + 下載按鈕

10. 用戶下載字幕
    ├─ VTT 下載：後端直接返回檔案
    └─ SRT 下載：後端即時轉換後返回
```

---

## 關鍵技術點

### 為什麼 SRT 不預先生成？

1. **節省儲存空間**：只保存一種格式（VTT）
2. **即時轉換很快**：毫秒級，不影響體驗
3. **靈活性**：未來可以支援更多格式（ASS、SSA 等）

### 為什麼使用 VTT 作為主要格式？

1. **網頁播放器支援**：HTML5 video 原生支援
2. **功能豐富**：支援樣式、位置、元數據
3. **標準格式**：W3C 標準

### 翻譯是否會影響時間軸？

**不會！** 時間軸完全保留：
```python
translated_segment = SubtitleSegment(
    start_time=segment.start_time,  # 保留原始
    end_time=segment.end_time,      # 保留原始
    text=translated_text            # 只翻譯文字
)
```

---

## 相關文檔

- [多語言檢測功能](MULTILINGUAL_DETECTION.md)
- [版本更新日誌](../CHANGELOG.md)
- [安裝指南](../INSTALLATION.md)

---

**文檔版本**：v2.4.2  
**最後更新**：2024-03-23
