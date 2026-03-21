# WhisperX 斷句控制研究

## 概述

本文檔記錄 WhisperX 的斷句控制選項和實現方案，供未來開發參考。

## 背景

WhisperX v3+ 使用 `nltk sent_tokenize` 進行句子級別的分段，傾向生成完整的句子。這對翻譯質量有利，但有時會產生過長的字幕段落，影響閱讀體驗。

**示例：**
```
完整句子模式（當前）：
1. I want to go to the store and buy some groceries because we're running low on food.

短片段模式（可選）：
1. I want to go to the store
2. and buy some groceries
3. because we're running low on food.
```

## WhisperX 提供的控制選項

### 1. CLI 參數

WhisperX 的命令行工具提供以下參數：

#### `--segment_resolution`
- **值**: `"sentence"` 或 `"chunk"`
- **默認**: `"sentence"`
- **說明**:
  - `"sentence"`: 使用 nltk 進行句子級別分段（完整句子）
  - `"chunk"`: 基於 VAD (Voice Activity Detection) 的塊分段（更短）

#### `--max_line_width`
- **值**: 整數（如 40, 50, 80）
- **默認**: 無限制
- **說明**: 每行最大字符數
- **注意**: 需要配合 word-level timestamps 使用

#### `--max_line_count`
- **值**: 整數（如 1, 2）
- **默認**: 無限制
- **說明**: 每個字幕段最大行數
- **注意**: 需要配合 word-level timestamps 使用

#### 示例命令
```bash
whisperx audio.mp4 \
  --model base \
  --segment_resolution chunk \
  --max_line_width 50 \
  --max_line_count 2 \
  --language en
```

### 2. Python API

**問題**: WhisperX 的 Python API (`model.transcribe()`) 不直接支持這些參數。

**原因**: 這些參數主要用於 CLI 的輸出格式化階段，而不是轉錄階段。

**解決方案**: 需要在轉錄後進行後處理。

## 實現方案

### 方案 1：使用 VAD-based 分段（推薦用於短片段）

**優點**:
- 基於語音活動檢測，自然的停頓點
- 不需要後處理
- 時間戳最準確

**缺點**:
- 可能在句子中間斷開
- 翻譯質量可能下降（句子不完整）

**實現**: 修改 `transcribe()` 調用，使用 `segment_resolution="chunk"`

```python
# 注意：這需要修改 WhisperX 源碼或使用 CLI
result = self.model.transcribe(
    audio, 
    batch_size=16,
    # segment_resolution="chunk"  # Python API 可能不支持
)
```

### 方案 2：後處理分割（靈活性最高）

**優點**:
- 完全控制分割邏輯
- 可以根據需求自定義規則
- 不依賴 WhisperX 的內部實現

**缺點**:
- 需要重新計算時間戳（可能不夠精確）
- 增加處理時間
- 代碼複雜度增加

**實現**: 在 `TranscriptionService` 中添加後處理方法

```python
async def transcribe(self, video_path: str, max_chars_per_segment: int = None):
    # ... WhisperX 轉錄 ...
    
    # 如果設置了最大字符數，進行分段處理
    if max_chars_per_segment:
        segments = self._split_long_segments(segments, max_chars_per_segment)
    
    return segments

def _split_long_segments(self, segments, max_chars):
    """將過長的字幕段分割成較短的片段"""
    result = []
    
    for segment in segments:
        if len(segment.text) <= max_chars:
            result.append(segment)
            continue
        
        # 按句子分割（句號、問號、驚嘆號）
        import re
        sentences = re.split(r'([.!?]+\s+)', segment.text)
        
        # 重組並計算時間
        # ... 詳細實現見下方完整代碼 ...
    
    return result
```

**完整實現代碼**:

```python
def _split_long_segments(self, segments: List[SubtitleSegment], max_chars: int) -> List[SubtitleSegment]:
    """
    將過長的字幕段分割成較短的片段
    
    Args:
        segments: 原始字幕片段列表
        max_chars: 每個片段的最大字符數
        
    Returns:
        分割後的字幕片段列表
    """
    result = []
    
    for segment in segments:
        text = segment.text
        
        # 如果字幕不超過最大長度，直接添加
        if len(text) <= max_chars:
            result.append(segment)
            continue
        
        # 需要分割：按句子分割（使用句號、問號、驚嘆號）
        import re
        sentences = re.split(r'([.!?]+\s+)', text)
        
        # 重組句子（保留標點符號）
        combined_sentences = []
        for i in range(0, len(sentences), 2):
            if i + 1 < len(sentences):
                combined_sentences.append(sentences[i] + sentences[i + 1])
            else:
                combined_sentences.append(sentences[i])
        
        # 如果沒有句子分隔符，按逗號分割
        if len(combined_sentences) == 1:
            combined_sentences = [s.strip() for s in text.split(',') if s.strip()]
        
        # 計算每個子片段的時間
        duration = segment.end_time - segment.start_time
        total_chars = len(text)
        
        current_pos = 0
        for sentence in combined_sentences:
            if not sentence.strip():
                continue
            
            # 根據字符比例計算時間
            sentence_chars = len(sentence)
            
            sub_start = segment.start_time + (current_pos / total_chars) * duration
            sub_end = segment.start_time + ((current_pos + sentence_chars) / total_chars) * duration
            
            sub_segment = SubtitleSegment(
                index=0,  # 稍後重新編號
                start_time=sub_start,
                end_time=sub_end,
                text=sentence.strip(),
                language=segment.language
            )
            result.append(sub_segment)
            
            current_pos += sentence_chars
    
    return result
```

### 方案 3：使用 WhisperX 的 word-level timestamps（最精確）

**優點**:
- 使用 WhisperX 提供的詞級別時間戳
- 時間戳最精確
- 可以按任意長度分割

**缺點**:
- 需要啟用 `return_char_alignments=True`
- 數據量更大
- 實現複雜度最高

**實現**: 使用 WhisperX 的詞級別對齊

```python
# 在 align 時啟用詞級別對齊
result = whisperx.align(
    result["segments"], 
    align_model, 
    metadata, 
    audio, 
    self.device, 
    return_char_alignments=True  # 啟用詞級別時間戳
)

# 然後根據詞級別時間戳重新組合字幕
# 每 N 個詞或每 M 個字符創建一個新片段
```

## 配置方式

### 環境變量配置

在 `.env` 文件中添加：

```env
# 字幕分段控制
# 留空或不設置 = 使用 WhisperX 默認（完整句子）
# 設置數字 = 每個字幕段的最大字符數（如 80）
MAX_CHARS_PER_SEGMENT=

# 示例：
# MAX_CHARS_PER_SEGMENT=80  # 限制每段最多 80 字符
```

### 代碼配置

在 `src/config.py` 中添加：

```python
# 字幕分段配置
MAX_CHARS_PER_SEGMENT = os.getenv("MAX_CHARS_PER_SEGMENT", None)
if MAX_CHARS_PER_SEGMENT:
    MAX_CHARS_PER_SEGMENT = int(MAX_CHARS_PER_SEGMENT)
```

在 `src/managers/job_manager.py` 中使用：

```python
from src.config import MAX_CHARS_PER_SEGMENT

# 在 process_job 方法中
english_segments = await self.transcription_service.transcribe(
    state.video_path,
    max_chars_per_segment=MAX_CHARS_PER_SEGMENT
)
```

## 建議

### 當前建議：保持默認（完整句子）

**理由**:
1. **翻譯質量更好**: 完整句子提供更多上下文，翻譯更準確
2. **閱讀體驗更好**: 不會在句子中間斷開
3. **用戶可編輯**: 如果覺得太長，可以在編輯器中手動分割

### 未來可選功能

如果用戶反饋需要更短的字幕段，可以：

1. **添加前端選項**: 在上傳頁面添加「字幕長度偏好」選項
   - 選項 1: 完整句子（默認）
   - 選項 2: 短片段（每段約 50-80 字符）
   - 選項 3: 極短片段（每段約 30-50 字符）

2. **實現方案 2**: 使用後處理分割
   - 優點: 靈活、可控
   - 缺點: 時間戳可能不夠精確

3. **實現方案 3**: 使用詞級別時間戳
   - 優點: 時間戳最精確
   - 缺點: 實現複雜、數據量大

## 參考資料

- [WhisperX GitHub](https://github.com/m-bain/whisperX)
- [WhisperX CLI 參數文檔](https://notes.nicolasdeville.com/python/library-whisperx)
- [WhisperX 論文](https://arxiv.org/abs/2303.00747)

## 相關 Issue

- [V3 sentence segment issue #200](https://github.com/m-bain/whisperX/issues/200)
- 討論 WhisperX v3 的句子分段行為

## 測試建議

如果要實現斷句控制，建議測試：

1. **不同語言**: 英文、中文、日文等（標點符號不同）
2. **不同內容**: 新聞、對話、演講等（句子長度不同）
3. **邊界情況**: 
   - 沒有標點符號的長句
   - 只有一個詞的短句
   - 包含數字和特殊符號的句子
4. **時間戳準確性**: 分割後的時間戳是否仍然準確

## 實現優先級

- **P0 (當前)**: 保持默認，使用完整句子
- **P1 (未來)**: 如果用戶反饋需要，添加後處理分割
- **P2 (可選)**: 添加前端配置選項
- **P3 (進階)**: 使用詞級別時間戳實現精確分割

---

**最後更新**: 2026-03-21  
**狀態**: 研究完成，暫不實現
