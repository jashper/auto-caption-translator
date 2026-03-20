"""
翻譯服務
使用 deep-translator 將字幕翻譯成多種語言
"""
import asyncio
from typing import List
from deep_translator import GoogleTranslator

from src.models.subtitle import SubtitleSegment
from src.config import SUPPORTED_LANGUAGES
from src.utils.logger import get_logger

logger = get_logger("translation")


class TranslationService:
    """字幕翻譯服務"""
    
    SUPPORTED_LANGUAGES = SUPPORTED_LANGUAGES
    MAX_RETRIES = 3
    BATCH_SIZE = 50  # 每批次翻譯的片段數量
    
    def __init__(self):
        """初始化翻譯服務"""
        self.translators = {}
        self._init_translators()
    
    def _init_translators(self) -> None:
        """初始化翻譯器"""
        for lang_code in self.SUPPORTED_LANGUAGES.keys():
            if lang_code != "en":  # 不需要英文翻譯器
                try:
                    self.translators[lang_code] = GoogleTranslator(source='en', target=lang_code)
                    logger.debug(f"已初始化翻譯器: en -> {lang_code}")
                except Exception as e:
                    logger.error(f"初始化翻譯器失敗 (en -> {lang_code}): {e}")
    
    async def translate_segments(
        self,
        segments: List[SubtitleSegment],
        target_lang: str
    ) -> List[SubtitleSegment]:
        """
        翻譯字幕片段
        
        Args:
            segments: 原始字幕片段列表
            target_lang: 目標語言代碼
            
        Returns:
            翻譯後的字幕片段列表
        """
        if target_lang not in self.translators:
            raise ValueError(f"不支援的目標語言: {target_lang}")
        
        logger.info(f"開始翻譯字幕: en -> {target_lang}，共 {len(segments)} 個片段")
        
        translated_segments = []
        translator = self.translators[target_lang]
        
        # 批次翻譯
        for i in range(0, len(segments), self.BATCH_SIZE):
            batch = segments[i:i + self.BATCH_SIZE]
            logger.debug(f"翻譯批次 {i // self.BATCH_SIZE + 1}/{(len(segments) + self.BATCH_SIZE - 1) // self.BATCH_SIZE}")
            
            for segment in batch:
                # 翻譯文字
                translated_text = await self._translate_text(
                    segment.text,
                    target_lang,
                    translator
                )
                
                # 建立翻譯後的片段（保留時間軸）
                translated_segment = SubtitleSegment(
                    index=segment.index,
                    start_time=segment.start_time,
                    end_time=segment.end_time,
                    text=translated_text,
                    language=target_lang,
                    translation_failed=(translated_text == segment.text)
                )
                translated_segments.append(translated_segment)
        
        logger.info(f"翻譯完成: en -> {target_lang}")
        return translated_segments
    
    async def _translate_text(
        self,
        text: str,
        target_lang: str,
        translator: GoogleTranslator,
        retry_count: int = 0
    ) -> str:
        """
        翻譯單一文字（帶重試機制）
        
        Args:
            text: 原始文字
            target_lang: 目標語言代碼
            translator: 翻譯器實例
            retry_count: 當前重試次數
            
        Returns:
            翻譯後的文字
        """
        try:
            # 在執行緒池中執行翻譯（因為 deep-translator 是同步的）
            loop = asyncio.get_event_loop()
            translated = await loop.run_in_executor(
                None,
                translator.translate,
                text
            )
            return translated
        except Exception as e:
            if retry_count < self.MAX_RETRIES:
                # 指數退避重試
                delay = 2 ** retry_count
                logger.warning(f"翻譯失敗，{delay} 秒後重試 ({retry_count + 1}/{self.MAX_RETRIES}): {e}")
                await asyncio.sleep(delay)
                return await self._translate_text(text, target_lang, translator, retry_count + 1)
            else:
                # 達到最大重試次數，保留原文
                logger.error(f"翻譯失敗，已達最大重試次數，保留原文: {e}")
                return text
