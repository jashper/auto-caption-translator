"""
翻譯服務
使用 deep-translator 將字幕翻譯成多種語言（批量合併翻譯）
"""
import asyncio
import random
import time
from typing import List
from deep_translator import GoogleTranslator

from src.models.subtitle import SubtitleSegment
from src.config import SUPPORTED_LANGUAGES
from src.utils.logger import get_logger, get_metrics_logger

logger = get_logger("translation")
metrics_logger = get_metrics_logger()

# Google Translate 合併翻譯用的分隔符
_BULK_SEPARATOR = "\n"


class TranslationService:
    """字幕翻譯服務（批量合併翻譯）"""
    
    SUPPORTED_LANGUAGES = SUPPORTED_LANGUAGES
    MAX_RETRIES = 2
    BULK_CHAR_LIMIT = 4500  # Google Translate 單次上限 ~5000，留餘量
    BULK_BATCH_DELAY = 2.0  # 批次間延遲（秒）
    
    # 翻譯失敗時的 fallback 標記（必須是目標語言，禁止保留原文）
    FALLBACK_MESSAGES = {
        'zh-TW': '[翻譯失敗]',
        'zh-CN': '[翻译失败]',
        'en': '[Translation failed]',
        'ms': '[Terjemahan gagal]',
    }
    
    def __init__(self):
        """初始化翻譯服務"""
        self.translators = {}
        self._init_translators()
    
    def _init_translators(self) -> None:
        """初始化翻譯器（支援所有語言對）"""
        target_languages = ['en', 'zh-TW', 'zh-CN', 'ms']
        
        # 使用 auto 作為 source，讓 Google Translate 自動辨識每段文字的語言
        for target in target_languages:
            key = f"auto->{target}"
            try:
                self.translators[key] = GoogleTranslator(source='auto', target=target)
                logger.debug(f"已初始化翻譯器: {key}")
            except Exception as e:
                logger.error(f"初始化翻譯器失敗 ({key}): {e}")
    
    def _build_chunks(self, texts: List[str]) -> List[List[int]]:
        """
        將文字列表按字元數上限分組，回傳每組的索引列表
        
        Args:
            texts: 原始文字列表
            
        Returns:
            分組後的索引列表，例如 [[0,1,2], [3,4,5], ...]
        """
        chunks = []
        current_chunk = []
        current_len = 0
        
        for i, text in enumerate(texts):
            # +1 是分隔符 \n 的長度
            added_len = len(text) + (1 if current_chunk else 0)
            
            if current_len + added_len > self.BULK_CHAR_LIMIT and current_chunk:
                chunks.append(current_chunk)
                current_chunk = [i]
                current_len = len(text)
            else:
                current_chunk.append(i)
                current_len += added_len
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    async def _translate_chunk(
        self,
        texts: List[str],
        translator: GoogleTranslator,
        target_lang: str,
        retry_count: int = 0,
    ) -> List[str]:
        """
        合併翻譯一組文字（用 \\n 連接後作為單次 API 請求）
        
        Args:
            texts: 要翻譯的文字列表
            translator: Google 翻譯器實例
            target_lang: 目標語言
            retry_count: 重試次數
            
        Returns:
            翻譯後的文字列表（長度與 texts 相同）
        """
        joined = _BULK_SEPARATOR.join(texts)
        
        try:
            loop = asyncio.get_event_loop()
            translated_joined = await loop.run_in_executor(
                None, translator.translate, joined
            )
            
            # 按分隔符拆回
            translated_lines = translated_joined.split(_BULK_SEPARATOR)
            
            if len(translated_lines) == len(texts):
                return [line.strip() for line in translated_lines]
            
            # 行數不匹配 → 降級為逐句翻譯
            logger.warning(
                f"批量翻譯行數不匹配（預期 {len(texts)}，得到 {len(translated_lines)}），降級為逐句翻譯"
            )
            return await self._translate_chunk_individually(texts, translator, target_lang)
        
        except Exception as e:
            error_msg = str(e).lower()
            
            # 速率限制 → 等待後重試整個 chunk
            if 'rate limit' in error_msg or 'too many requests' in error_msg or '429' in error_msg:
                if retry_count < self.MAX_RETRIES:
                    delay = 5 + (2 ** retry_count) + random.uniform(0, 3)
                    logger.warning(f"速率限制，{delay:.1f}s 後重試 chunk ({retry_count + 1}/{self.MAX_RETRIES})")
                    await asyncio.sleep(delay)
                    return await self._translate_chunk(texts, translator, target_lang, retry_count + 1)
            
            # 其他錯誤 → 重試一次，仍失敗則降級逐句
            if retry_count < self.MAX_RETRIES:
                delay = 2 ** retry_count + random.uniform(0, 1)
                logger.warning(f"批量翻譯失敗，{delay:.1f}s 後重試: {e}")
                await asyncio.sleep(delay)
                return await self._translate_chunk(texts, translator, target_lang, retry_count + 1)
            
            logger.error(f"批量翻譯失敗，降級為逐句翻譯: {e}")
            return await self._translate_chunk_individually(texts, translator, target_lang)
    
    async def _translate_chunk_individually(
        self,
        texts: List[str],
        translator: GoogleTranslator,
        target_lang: str,
    ) -> List[str]:
        """
        逐句翻譯（作為批量翻譯的 fallback）
        
        Args:
            texts: 要翻譯的文字列表
            translator: Google 翻譯器實例
            target_lang: 目標語言
            
        Returns:
            翻譯後的文字列表
        """
        results = []
        fallback = self.FALLBACK_MESSAGES.get(target_lang, '[...]')
        loop = asyncio.get_event_loop()
        
        for text in texts:
            try:
                translated = await loop.run_in_executor(None, translator.translate, text)
                results.append(translated if translated else fallback)
            except Exception as e:
                logger.error(f"逐句翻譯失敗: {text[:30]}... -> {e}")
                results.append(fallback)
            await asyncio.sleep(random.uniform(0.2, 0.5))
        
        return results
    
    async def translate_segments(
        self,
        segments: List[SubtitleSegment],
        source_lang: str,
        target_lang: str,
    ) -> List[SubtitleSegment]:
        """
        批量翻譯字幕片段（合併多句為一次 API 請求）
        
        Args:
            segments: 原始字幕片段列表
            source_lang: 原語言代碼
            target_lang: 目標語言代碼
            
        Returns:
            翻譯後的字幕片段列表
        """
        translator_key = f"auto->{target_lang}"
        if translator_key not in self.translators:
            raise ValueError(f"不支援的翻譯目標語言: {target_lang}")
        
        translator = self.translators[translator_key]
        logger.info(f"開始批量翻譯字幕: {source_lang} -> {target_lang}，共 {len(segments)} 個片段")
        
        start_time = time.time()
        
        # 提取所有文字
        all_texts = [seg.text for seg in segments]
        
        # 按字元上限分組
        chunks = self._build_chunks(all_texts)
        logger.info(f"分為 {len(chunks)} 個批次（字元上限 {self.BULK_CHAR_LIMIT}）")
        
        # 翻譯結果（按原始順序）
        translated_texts = [""] * len(segments)
        
        for chunk_idx, index_group in enumerate(chunks):
            chunk_texts = [all_texts[i] for i in index_group]
            logger.debug(f"翻譯批次 {chunk_idx + 1}/{len(chunks)}，{len(chunk_texts)} 句，{sum(len(t) for t in chunk_texts)} 字元")
            
            results = await self._translate_chunk(chunk_texts, translator, target_lang)
            
            for j, idx in enumerate(index_group):
                translated_texts[idx] = results[j]
            
            # 批次間延遲
            if chunk_idx < len(chunks) - 1:
                delay = self.BULK_BATCH_DELAY + random.uniform(0, 1.0)
                logger.debug(f"批次間休息 {delay:.1f} 秒...")
                await asyncio.sleep(delay)
        
        # 組裝結果
        translated_segments = []
        success_count = 0
        fail_count = 0
        
        for seg, translated_text in zip(segments, translated_texts):
            failed = (translated_text == seg.text) or not translated_text
            if failed:
                fail_count += 1
            else:
                success_count += 1
            
            translated_segments.append(SubtitleSegment(
                index=seg.index,
                start_time=seg.start_time,
                end_time=seg.end_time,
                text=translated_text if translated_text else self.FALLBACK_MESSAGES.get(target_lang, '[...]'),
                language=target_lang,
                translation_failed=failed,
            ))
        
        # 統計
        total = success_count + fail_count
        fail_rate = (fail_count / total * 100) if total > 0 else 0
        elapsed = time.time() - start_time
        
        summary = (
            f"SUMMARY | {source_lang}->{target_lang} | "
            f"total={total} success={success_count} fail={fail_count} "
            f"fail_rate={fail_rate:.1f}% elapsed={elapsed:.1f}s "
            f"chunks={len(chunks)}"
        )
        metrics_logger.info(summary)
        
        if fail_rate > 20:
            logger.warning(
                f"翻譯失敗率過高！{source_lang}->{target_lang} "
                f"失敗率={fail_rate:.1f}% ({fail_count}/{total})"
            )
        
        logger.info(f"翻譯完成: {source_lang} -> {target_lang}，耗時 {elapsed:.1f}s")
        return translated_segments
