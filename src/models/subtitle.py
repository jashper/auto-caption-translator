"""
字幕資料模型
定義字幕片段的資料結構和相關方法
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class SubtitleSegment:
    """
    字幕片段資料結構
    
    Attributes:
        index: 片段索引（從 1 開始）
        start_time: 開始時間（秒）
        end_time: 結束時間（秒）
        text: 字幕文字
        language: 語言代碼 (en, zh-TW, zh-CN, ms)
        translation_failed: 翻譯失敗標記
    """
    index: int
    start_time: float
    end_time: float
    text: str
    language: str
    translation_failed: bool = False
    dirty: bool = False
    
    def __post_init__(self):
        """驗證資料有效性"""
        # 自動 trim 文字
        self.text = self.text.strip()
        
        if self.index < 1:
            raise ValueError("index 必須大於或等於 1")
        if self.start_time < 0:
            raise ValueError("start_time 必須非負")
        if self.end_time < 0:
            raise ValueError("end_time 必須非負")
        if self.start_time > self.end_time:
            raise ValueError("start_time 必須小於或等於 end_time")
        if not self.text.strip():
            raise ValueError("text 不能為空")
        # 支援的語言：包括 zh（WhisperX 檢測結果）
        if self.language not in ["en", "zh", "zh-TW", "zh-CN", "ms"]:
            raise ValueError(f"不支援的語言: {self.language}")
    
    def to_dict(self) -> dict:
        """
        轉換為字典格式
        
        Returns:
            字典表示
        """
        return {
            "index": self.index,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "text": self.text,
            "language": self.language,
            "translation_failed": self.translation_failed,
            "dirty": self.dirty
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SubtitleSegment":
        """
        從字典建立實例
        
        Args:
            data: 字典資料
            
        Returns:
            SubtitleSegment 實例
        """
        # 過濾掉未知的 key（向後相容）
        valid_fields = {'index', 'start_time', 'end_time', 'text', 'language', 'translation_failed', 'dirty'}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)
    
    def format_vtt_timestamp(self, seconds: float) -> str:
        """
        格式化為 VTT 時間戳 (HH:MM:SS.mmm)
        
        Args:
            seconds: 秒數
            
        Returns:
            格式化的時間戳字串
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    
    def _escape_vtt_text(self, text: str) -> str:
        """
        轉義 VTT 特殊字元
        
        Args:
            text: 原始文字
            
        Returns:
            轉義後的文字
        """
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))
    
    def to_vtt_format(self) -> str:
        """
        轉換為 VTT 格式字串
        
        Returns:
            VTT 格式的字幕片段
        """
        start = self.format_vtt_timestamp(self.start_time)
        end = self.format_vtt_timestamp(self.end_time)
        escaped_text = self._escape_vtt_text(self.text)
        return f"{self.index}\n{start} --> {end}\n{escaped_text}\n"
