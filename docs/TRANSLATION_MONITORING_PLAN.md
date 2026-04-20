# 翻譯服務監控與備選方案預案

## 概述

本文檔提供 Google Translate 的監控指標、評估標準，以及 NLLB-200 備選方案的快速切換指南。

**目標**：當 Google Translate 出現問題時，能在 1-2 天內切換到 NLLB-200。

---

## 📊 月度監控指標

### 1. 穩定性指標

**記錄位置**：`logs/translation_metrics.log`

**需要追蹤的數據**：

```python
# 每次翻譯任務完成後記錄
{
    "date": "2024-03-23",
    "job_id": "abc123",
    "total_segments": 150,
    "successful_translations": 148,
    "failed_translations": 2,
    "retry_count": 5,
    "rate_limit_hits": 1,
    "average_time_per_segment": 0.8,  # 秒
    "total_time": 120,  # 秒
    "languages": ["en->zh-TW", "en->zh-CN", "en->ms"]
}
```

**月度統計**：
- 總翻譯次數
- 成功率（%）
- 平均重試次數
- 速率限制觸發次數
- 平均處理時間

### 2. 質量指標

**用戶反饋追蹤**：

```markdown
## 2024年3月翻譯質量反饋

### 正面反饋
- 用戶 A：英文→繁中翻譯準確
- 用戶 B：馬來文翻譯流暢

### 負面反饋
- 用戶 C：專有名詞翻譯錯誤（3次）
- 用戶 D：句子不完整（1次）

### 質量評分（1-5）
- 英文→繁中：4.5
- 英文→簡中：4.3
- 英文→馬來文：4.0
```

### 3. 成本指標

**時間成本**：
- 每個影片的翻譯時間
- 延遲時間佔比（避免速率限制）

**用戶體驗成本**：
- 處理失敗次數
- 用戶投訴次數

---

## 🚨 觸發切換的閾值

### 紅色警報（立即考慮切換）

1. **成功率 < 90%**（連續 3 天）
2. **速率限制觸發 > 10 次/天**（連續 3 天）
3. **Google Translate API 變更**導致完全失效
4. **用戶投訴 > 5 次/月**關於翻譯失敗

### 黃色警報（開始準備）

1. **成功率 90-95%**（連續 7 天）
2. **速率限制觸發 5-10 次/天**（連續 7 天）
3. **平均處理時間增加 50%**
4. **用戶投訴 3-5 次/月**

### 綠色狀態（正常運行）

1. **成功率 > 95%**
2. **速率限制觸發 < 5 次/天**
3. **處理時間穩定**
4. **用戶投訴 < 3 次/月**

---

## 📋 NLLB-200 快速切換檢查清單

### 階段 1：環境準備（1-2 小時）

**硬體檢查**：
```bash
# 檢查磁碟空間（需要至少 5GB）
df -h

# 檢查記憶體（需要至少 8GB）
free -h

# 檢查是否有 GPU（可選）
nvidia-smi
```

**依賴安裝**：
```bash
# 安裝 transformers
pip install transformers sentencepiece protobuf

# 如果有 GPU，安裝 accelerate
pip install accelerate

# 驗證安裝
python -c "from transformers import AutoTokenizer; print('OK')"
```

**模型下載測試**：
```python
# test_nllb_download.py
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

print("開始下載 NLLB-200 模型...")
model_name = "facebook/nllb-200-distilled-600M"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
print("下載完成！")
```

### 階段 2：代碼準備（已準備好的模板）

**創建 NLLB 翻譯服務**：

保存以下代碼為 `src/services/nllb_translation_service.py`：

```python
"""
NLLB-200 翻譯服務（備選方案）
當 Google Translate 不可用時使用
"""
import asyncio
from typing import List
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

from src.models.subtitle import SubtitleSegment
from src.utils.logger import get_logger

logger = get_logger("nllb_translation")


class NLLBTranslationService:
    """NLLB-200 翻譯服務"""
    
    # 語言代碼映射（Google → NLLB）
    LANG_CODE_MAP = {
        'en': 'eng_Latn',
        'zh-TW': 'zho_Hant',
        'zh-CN': 'zho_Hans',
        'ms': 'zsm_Latn',
        'zh': 'zho_Hans'  # 默認使用簡體
    }
    
    def __init__(self, model_size: str = "600M", device: str = "cpu"):
        """
        初始化 NLLB 翻譯服務
        
        Args:
            model_size: 模型大小 (600M, 1.3B, 3.3B)
            device: 設備 (cpu, cuda)
        """
        self.model_size = model_size
        self.device = device
        self.model = None
        self.tokenizer = None
        self._load_model()
    
    def _load_model(self):
        """載入 NLLB 模型"""
        try:
            model_name = f"facebook/nllb-200-distilled-{self.model_size.lower()}"
            logger.info(f"正在載入 NLLB 模型: {model_name}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            
            # 移動到指定設備
            if self.device == "cuda" and torch.cuda.is_available():
                self.model = self.model.to("cuda")
                logger.info("NLLB 模型已載入到 GPU")
            else:
                logger.info("NLLB 模型已載入到 CPU")
            
        except Exception as e:
            logger.error(f"載入 NLLB 模型失敗: {e}")
            raise RuntimeError(f"無法載入 NLLB 模型: {e}")
    
    def _get_nllb_lang_code(self, lang: str) -> str:
        """轉換語言代碼"""
        return self.LANG_CODE_MAP.get(lang, lang)
    
    async def translate_segments(
        self,
        segments: List[SubtitleSegment],
        source_lang: str,
        target_lang: str
    ) -> List[SubtitleSegment]:
        """
        翻譯字幕片段
        
        Args:
            segments: 原始字幕片段列表
            source_lang: 原語言代碼
            target_lang: 目標語言代碼
            
        Returns:
            翻譯後的字幕片段列表
        """
        # 轉換語言代碼
        src_code = self._get_nllb_lang_code(source_lang)
        tgt_code = self._get_nllb_lang_code(target_lang)
        
        logger.info(f"開始翻譯: {source_lang}({src_code}) -> {target_lang}({tgt_code})")
        
        translated_segments = []
        
        # 批次處理（每批 10 個）
        batch_size = 10
        for i in range(0, len(segments), batch_size):
            batch = segments[i:i + batch_size]
            texts = [seg.text for seg in batch]
            
            # 批次翻譯
            translated_texts = await self._translate_batch(
                texts, src_code, tgt_code
            )
            
            # 創建翻譯後的片段
            for segment, translated_text in zip(batch, translated_texts):
                translated_segment = SubtitleSegment(
                    index=segment.index,
                    start_time=segment.start_time,
                    end_time=segment.end_time,
                    text=translated_text,
                    language=target_lang
                )
                translated_segments.append(translated_segment)
        
        logger.info(f"翻譯完成: {len(translated_segments)} 個片段")
        return translated_segments
    
    async def _translate_batch(
        self,
        texts: List[str],
        src_lang: str,
        tgt_lang: str
    ) -> List[str]:
        """批次翻譯"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._translate_batch_sync,
            texts,
            src_lang,
            tgt_lang
        )
    
    def _translate_batch_sync(
        self,
        texts: List[str],
        src_lang: str,
        tgt_lang: str
    ) -> List[str]:
        """同步批次翻譯"""
        try:
            # Tokenize
            inputs = self.tokenizer(
                texts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            )
            
            # 移動到設備
            if self.device == "cuda":
                inputs = {k: v.to("cuda") for k, v in inputs.items()}
            
            # 生成翻譯
            translated = self.model.generate(
                **inputs,
                forced_bos_token_id=self.tokenizer.lang_code_to_id[tgt_lang],
                max_length=512
            )
            
            # Decode
            translated_texts = self.tokenizer.batch_decode(
                translated,
                skip_special_tokens=True
            )
            
            return translated_texts
        
        except Exception as e:
            logger.error(f"批次翻譯失敗: {e}")
            # 返回原文
            return texts
```

### 階段 3：配置切換（5 分鐘）

**修改 `.env`**：
```env
# 翻譯引擎選擇
TRANSLATION_ENGINE=nllb  # 從 google 改為 nllb

# NLLB 配置
NLLB_MODEL_SIZE=600M  # 或 1.3B, 3.3B
NLLB_DEVICE=cpu       # 或 cuda（如果有 GPU）
```

**修改 `src/config.py`**：
```python
# 添加配置
TRANSLATION_ENGINE = os.getenv('TRANSLATION_ENGINE', 'google')
NLLB_MODEL_SIZE = os.getenv('NLLB_MODEL_SIZE', '600M')
NLLB_DEVICE = os.getenv('NLLB_DEVICE', 'cpu')
```

**修改 `src/managers/job_manager.py`**：
```python
# 在 __init__ 中
from src.config import TRANSLATION_ENGINE

if TRANSLATION_ENGINE == 'nllb':
    from src.services.nllb_translation_service import NLLBTranslationService
    self.translation_service = NLLBTranslationService()
else:
    from src.services.translation_service import TranslationService
    self.translation_service = TranslationService()
```

### 階段 4：測試驗證（30 分鐘）

**測試腳本**：
```python
# test_nllb_translation.py
import asyncio
from src.services.nllb_translation_service import NLLBTranslationService
from src.models.subtitle import SubtitleSegment

async def test():
    service = NLLBTranslationService()
    
    # 測試片段
    segments = [
        SubtitleSegment(1, 0.0, 2.0, "Hello world", "en"),
        SubtitleSegment(2, 2.0, 4.0, "How are you", "en"),
    ]
    
    # 翻譯
    translated = await service.translate_segments(segments, "en", "zh-TW")
    
    for seg in translated:
        print(f"{seg.index}: {seg.text}")

asyncio.run(test())
```

### 階段 5：回滾計劃（5 分鐘）

**如果 NLLB 有問題，快速回滾**：
```bash
# 修改 .env
TRANSLATION_ENGINE=google

# 重啟服務
# Ctrl+C 停止
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

---

## 📚 用戶教育材料

### 博客文章草稿

**標題**：「影片字幕翻譯系統的翻譯引擎選擇」

**內容大綱**：

1. **為什麼需要翻譯引擎？**
   - 語音辨識只能生成原語言字幕
   - 需要翻譯引擎將字幕翻譯成其他語言

2. **當前使用：Google Translate**
   - 優勢：質量好、免費、簡單
   - 劣勢：需要網絡、可能有速率限制

3. **備選方案：NLLB-200**
   - 優勢：離線、無限制、隱私
   - 劣勢：需要下載模型、質量略低

4. **如何選擇？**
   - 個人使用：Google Translate
   - 企業/離線：NLLB-200
   - 敏感內容：NLLB-200

5. **未來計劃**
   - 監控 Google Translate 穩定性
   - 準備好 NLLB-200 備選方案
   - 根據用戶反饋調整

### README 補充說明

在 `README.md` 中添加：

```markdown
## 翻譯引擎

本系統使用 **Google Translate** 進行字幕翻譯。

### 為什麼選擇 Google Translate？

- ✅ 翻譯質量高
- ✅ 完全免費
- ✅ 支援多種語言
- ✅ 無需額外配置

### 備選方案：NLLB-200

如果 Google Translate 不可用，系統支援切換到 NLLB-200 模型：

- ✅ 完全離線運行
- ✅ 無速率限制
- ✅ 隱私保護
- ⚠️ 需要下載模型（2.4GB）
- ⚠️ 翻譯質量略低

詳細對比請參考：[翻譯模型對比](docs/TRANSLATION_MODEL_COMPARISON.md)
```

---

## 📅 定期評估計劃

### 每月評估（5 分鐘）

**檢查清單**：
- [ ] 查看翻譯成功率
- [ ] 查看速率限制觸發次數
- [ ] 查看用戶反饋
- [ ] 更新監控指標

**記錄模板**：
```markdown
## 2024年3月翻譯服務評估

### 指標
- 成功率：98.5%
- 速率限制：2 次
- 用戶投訴：0 次
- 狀態：✅ 綠色

### 結論
繼續使用 Google Translate

### 下月關注
- 監控成功率
- 收集用戶反饋
```

### 每季度評估（30 分鐘）

**深度分析**：
1. 翻譯質量趨勢
2. 成本效益分析
3. 用戶滿意度調查
4. 技術債務評估

**決策點**：
- 是否需要切換到 NLLB-200？
- 是否需要實現混合方案？
- 是否需要優化當前方案？

---

## 🎯 行動計劃總結

### 立即執行（本週）

1. ✅ 創建監控指標記錄模板
2. ✅ 準備 NLLB 快速切換代碼（模板）
3. ✅ 撰寫用戶教育材料
4. ✅ 更新 README 說明備選方案

### 持續執行（每月）

1. ✅ 記錄翻譯指標
2. ✅ 評估服務狀態
3. ✅ 收集用戶反饋
4. ✅ 更新評估報告

### 觸發執行（當出現問題時）

1. ✅ 執行 NLLB 快速切換檢查清單
2. ✅ 測試驗證
3. ✅ 通知用戶
4. ✅ 更新文檔

---

## 📝 附錄：監控腳本

### 自動記錄翻譯指標

在 `src/services/translation_service.py` 中添加：

```python
import json
from datetime import datetime

def log_translation_metrics(self, job_id, metrics):
    """記錄翻譯指標"""
    log_file = "logs/translation_metrics.log"
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "job_id": job_id,
        **metrics
    }
    
    with open(log_file, 'a') as f:
        f.write(json.dumps(entry) + '\n')
```

### 月度報告生成腳本

```python
# tools/generate_translation_report.py
import json
from datetime import datetime, timedelta
from collections import defaultdict

def generate_monthly_report(month):
    """生成月度翻譯報告"""
    metrics = defaultdict(list)
    
    with open('logs/translation_metrics.log', 'r') as f:
        for line in f:
            entry = json.loads(line)
            # 解析並統計
            # ...
    
    # 生成報告
    print(f"## {month} 翻譯服務報告")
    print(f"成功率: {success_rate}%")
    print(f"速率限制: {rate_limit_count} 次")
    # ...

if __name__ == "__main__":
    generate_monthly_report("2024-03")
```

---

**文檔版本**：v1.0  
**創建日期**：2024-03-23  
**下次更新**：2024-04-23（月度評估）
