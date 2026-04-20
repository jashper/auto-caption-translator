# 多語言影片自動檢測與智能翻譯

## 功能概述

從 v2.4.0 開始，系統支援自動檢測影片語言並智能選擇翻譯目標語言。

## 核心特性

### 1. 自動語言檢測

- 使用 WhisperX 自動檢測影片語言
- 支援 99 種語言（包括英文、中文、馬來文等）
- 檢測準確度高，無需手動指定

### 2. 智能翻譯邏輯

系統根據檢測到的原語言，自動選擇合適的翻譯目標語言：

| 原語言 | 翻譯目標語言 |
|--------|-------------|
| 英文 (en) | 繁體中文、簡體中文、馬來文 |
| 中文 (zh) | 英文、馬來文 |
| 馬來文 (ms) | 英文、繁體中文、簡體中文 |
| 其他語言 | 英文、繁體中文、馬來文 |

### 3. 中文簡繁體處理

- WhisperX 檢測中文時返回 `zh`（不區分簡繁）
- 系統預設將中文字幕保存為繁體中文 (`zh-TW`)
- 符合主要用戶群的使用習慣

## 使用流程

### 1. 上傳影片

上傳任何語言的影片（英文、中文、馬來文等）

### 2. 選擇翻譯語言（v2.4.2 新增）

**重要**：從 v2.4.2 開始，用戶必須手動選擇需要的翻譯語言。

- 勾選需要的語言（繁體中文、簡體中文、馬來文）
- 可以選擇 1-3 種語言
- 只會處理勾選的語言，節省時間和資源

**示例**：
- 只需要簡體中文 → 只勾選「簡體中文」
- 需要簡體中文和馬來文 → 勾選「簡體中文」和「Bahasa Melayu」
- 需要所有語言 → 勾選全部三個選項

### 3. 自動處理

系統自動執行以下步驟：

1. **提取音訊**：從影片中提取音訊（臨時文件，處理後刪除）
2. **語言檢測**：WhisperX 自動檢測語言
3. **生成原語言字幕**：轉錄為檢測到的語言
4. **智能翻譯**：翻譯成用戶選擇的語言（v2.4.2 更新）
5. **生成字幕文件**：輸出原語言 + 用戶選擇的翻譯語言的 VTT 文件

### 4. 查看結果

- 系統顯示檢測到的語言
- 提供原語言字幕下載
- 提供所有翻譯語言字幕下載

## 實際案例

### 案例 1：英文影片（選擇所有語言）

```
輸入：英文語音影片
用戶選擇：繁體中文 + 簡體中文 + 馬來文
檢測：en (English)
輸出字幕：
  - en.vtt (英文原字幕)
  - zh-TW.vtt (繁體中文翻譯)
  - zh-CN.vtt (簡體中文翻譯)
  - ms.vtt (馬來文翻譯)
```

### 案例 2：中文影片（只選擇簡體中文）

```
輸入：中文語音影片
用戶選擇：簡體中文
檢測：zh (中文)
輸出字幕：
  - zh-TW.vtt (繁體中文原字幕)
  - zh-CN.vtt (簡體中文翻譯)
處理時間：減少 50%（只處理 1 種語言而非 2 種）
```

### 案例 3：馬來文影片（選擇英文和繁體中文）

```
輸入：馬來文語音影片
用戶選擇：英文 + 繁體中文
檢測：ms (Bahasa Melayu)
輸出字幕：
  - ms.vtt (馬來文原字幕)
  - en.vtt (英文翻譯)
  - zh-TW.vtt (繁體中文翻譯)
處理時間：減少 33%（只處理 2 種語言而非 3 種）
```

### 案例 4：沒有選擇任何語言（v2.4.2 新增）

```
輸入：任何語音影片
用戶選擇：無（沒有勾選任何語言）
結果：顯示錯誤「請至少選擇一種翻譯語言」
不進行處理
```

## 重要說明

### 音訊保持不變

**系統絕對不會修改原始音訊**：

- ✅ 只提取臨時音訊用於分析
- ✅ 原始影片完全不動
- ✅ 臨時音訊處理後自動刪除
- ✅ 只輸出字幕文件（VTT）

**禁止的操作**：
- ❌ 不進行語音合成（TTS）
- ❌ 不替換音訊
- ❌ 不修改原始影片
- ❌ 不進行配音

### 語言檢測準確度

- WhisperX 語言檢測準確度很高（>95%）
- 系統接受檢測結果，不提供重新處理選項
- 如果檢測錯誤，可以重新上傳影片

## 技術實現

### 1. TranscriptionService 修改

```python
async def transcribe(self, video_path: str) -> tuple[List[SubtitleSegment], str]:
    """
    轉錄影片為原語言字幕
    
    Returns:
        (字幕片段列表, 檢測到的語言代碼)
    """
    result = self.model.transcribe(audio, batch_size=16)
    detected_language = result.get("language", "en")
    
    # 使用檢測到的語言，而非硬編碼
    for segment in result['segments']:
        subtitle_segment = SubtitleSegment(
            ...,
            language=detected_language
        )
    
    return segments, detected_language
```

### 2. TranslationService 智能選擇

```python
@staticmethod
def get_target_languages(source_lang: str) -> List[str]:
    """根據原語言決定翻譯目標語言"""
    if source_lang == 'en':
        return ['zh-TW', 'zh-CN', 'ms']
    elif source_lang == 'zh':
        return ['en', 'ms']
    elif source_lang == 'ms':
        return ['en', 'zh-TW', 'zh-CN']
    else:
        return ['en', 'zh-TW', 'ms']
```

### 3. JobManager 處理流程（v2.4.2 更新）

```python
# 轉錄並獲取檢測語言
source_segments, detected_language = await self.transcription_service.transcribe(video_path)

# 保存檢測語言
state.detected_language = detected_language

# 使用用戶選擇的語言（v2.4.2 新增）
if state.target_languages:
    # 優先使用用戶選擇
    target_languages = state.target_languages
else:
    # 沒有選擇時才使用自動檢測（向後兼容）
    target_languages = TranslationService.get_target_languages(detected_language)

# 翻譯
for lang in target_languages:
    translated = await self.translation_service.translate_segments(
        source_segments,
        detected_language,  # 原語言
        lang                # 目標語言
    )
```

## API 變更

### JobStatusResponse 新增欄位

```json
{
  "job_id": "abc123",
  "status": "completed",
  "progress": 100,
  "stage": "已完成",
  "detected_language": "zh",  // 新增：檢測到的語言
  "subtitle_files": {
    "zh-TW": "path/to/zh-TW.vtt",
    "en": "path/to/en.vtt",
    "ms": "path/to/ms.vtt"
  }
}
```

## 前端顯示

### 語言信息顯示

結果頁面會顯示檢測到的語言：

```
檢測到的語言：中文 (zh)
```

### 字幕下載標籤

- 原語言字幕會被標示為「原字幕」
- 翻譯字幕會被標示為「翻譯」

## 版本歷史

- **v2.4.2** (2024-03-23)
  - 修復語言選擇被忽略的問題
  - 用戶必須手動選擇需要的語言
  - 優先使用用戶選擇，沒有選擇時才使用自動檢測
  - 優化 Whisper 模型配置（默認使用 small）
- **v2.4.1** (2024-03-23)
  - 緊急修復中文影片處理問題
  - 添加 `zh` 語言支援
  - 對齊失敗時使用原始時間戳
- **v2.4.0** (2024-03-23)
  - 新增多語言自動檢測功能
  - 實現智能翻譯邏輯
  - 更新前端顯示檢測語言
  - 修復硬編碼 `language="en"` 的問題

## 常見問題

### Q: 系統會修改我的影片音訊嗎？

**A:** 絕對不會。系統只提取臨時音訊用於分析，處理完成後會自動刪除。原始影片的音訊保持 100% 不變。

### Q: 如果語言檢測錯誤怎麼辦？

**A:** WhisperX 的檢測準確度很高（>95%）。如果確實檢測錯誤，可以重新上傳影片。未來版本可能會添加手動指定語言的選項。

### Q: 為什麼中文影片不翻譯成簡繁體？

**A:** 因為原字幕已經是中文，簡繁體互轉意義不大。系統只翻譯成其他語言（英文、馬來文）。

### Q: 支援哪些語言？

**A:** WhisperX 支援 99 種語言的檢測和轉錄。翻譯服務支援英文、繁體中文、簡體中文和馬來文之間的互譯。

### Q: 可以自定義翻譯目標語言嗎？（v2.4.2 更新）

**A:** 可以！從 v2.4.2 開始，用戶可以在上傳時選擇需要的翻譯語言。只會處理勾選的語言，節省時間和資源。

### Q: 為什麼我的語言選擇沒有生效？（v2.4.1 及之前版本的問題）

**A:** 這是 v2.4.0 和 v2.4.1 的已知問題，已在 v2.4.2 中修復。請升級到 v2.4.2 或更高版本。

### Q: 如何改善中文和馬來文的分段質量？（v2.4.2 新增）

**A:** 編輯 `.env` 文件，將 `WHISPER_MODEL_SIZE` 改為 `small`、`medium` 或 `large`。更大的模型會提供更好的分段質量，但處理時間會增加。

## 相關文檔

- [WhisperX 語言支援列表](https://github.com/m-bain/whisperX#supported-languages)
- [安裝指南](../INSTALLATION.md)
- [更新日誌](../CHANGELOG.md)
