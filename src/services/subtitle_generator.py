"""
字幕生成器
生成和解析 VTT 格式字幕檔案
"""
import re
from pathlib import Path
from typing import List

from src.models.subtitle import SubtitleSegment
from src.utils.logger import get_logger

logger = get_logger("subtitle_generator")


class SubtitleGenerator:
    """VTT 字幕生成器"""
    
    def generate_vtt(self, segments: List[SubtitleSegment], output_path: str, language: str) -> None:
        """
        生成 VTT 字幕檔案
        
        Args:
            segments: 字幕片段列表
            output_path: 輸出檔案路徑
            language: 語言代碼
        """
        try:
            # 確保輸出目錄存在
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                # 寫入 VTT 標頭
                f.write(self._format_vtt_header())
                f.write('\n\n')
                
                # 寫入每個字幕片段
                for segment in segments:
                    f.write(segment.to_vtt_format())
                    f.write('\n')
            
            logger.info(f"已生成 VTT 字幕檔案: {output_path} ({language})")
        except Exception as e:
            logger.error(f"生成 VTT 字幕檔案失敗: {e}")
            raise
    
    def _format_vtt_header(self) -> str:
        """
        格式化 VTT 標頭
        
        Returns:
            VTT 標頭字串
        """
        return "WEBVTT"
    
    def parse_vtt(self, vtt_path: str) -> List[SubtitleSegment]:
        """
        解析 VTT 字幕檔案
        
        Args:
            vtt_path: VTT 檔案路徑
            
        Returns:
            字幕片段列表
        """
        try:
            with open(vtt_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 驗證 VTT 標頭
            if not content.startswith("WEBVTT"):
                raise ValueError("無效的 VTT 檔案：缺少 WEBVTT 標頭")
            
            segments = []
            
            # 使用正則表達式解析字幕片段
            # 格式: 索引\n時間戳 --> 時間戳\n文字\n
            pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2}\.\d{3}) --> (\d{2}:\d{2}:\d{2}\.\d{3})\n(.*?)(?=\n\n|\n\d+\n|\Z)'
            matches = re.finditer(pattern, content, re.DOTALL)
            
            for match in matches:
                index = int(match.group(1))
                start_time = self._parse_timestamp(match.group(2))
                end_time = self._parse_timestamp(match.group(3))
                text = match.group(4).strip()
                
                # 反轉義特殊字元
                text = self._unescape_vtt_text(text)
                
                # 從檔案路徑推斷語言
                language = self._infer_language_from_path(vtt_path)
                
                segment = SubtitleSegment(
                    index=index,
                    start_time=start_time,
                    end_time=end_time,
                    text=text,
                    language=language
                )
                segments.append(segment)
            
            logger.info(f"已解析 VTT 字幕檔案: {vtt_path}，共 {len(segments)} 個片段")
            return segments
        except Exception as e:
            logger.error(f"解析 VTT 字幕檔案失敗: {e}")
            raise
    
    def _parse_timestamp(self, timestamp: str) -> float:
        """
        解析 VTT 時間戳為秒數
        
        Args:
            timestamp: VTT 時間戳 (HH:MM:SS.mmm)
            
        Returns:
            秒數
        """
        parts = timestamp.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        
        return hours * 3600 + minutes * 60 + seconds
    
    def _unescape_vtt_text(self, text: str) -> str:
        """
        反轉義 VTT 特殊字元
        
        Args:
            text: 轉義後的文字
            
        Returns:
            原始文字
        """
        return (text
                .replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("&amp;", "&"))
    
    def _infer_language_from_path(self, vtt_path: str) -> str:
        """
        從檔案路徑推斷語言
        
        Args:
            vtt_path: VTT 檔案路徑
            
        Returns:
            語言代碼
        """
        filename = Path(vtt_path).stem
        
        # 常見的語言代碼
        language_map = {
            "en": "en",
            "zh-TW": "zh-TW",
            "zh-CN": "zh-CN",
            "ms": "ms"
        }
        
        return language_map.get(filename, "en")
    
    def generate_srt_content(self, segments: List[SubtitleSegment]) -> str:
        """
        生成 SRT 格式字幕內容
        
        Args:
            segments: 字幕片段列表
            
        Returns:
            SRT 格式字串
        """
        srt_lines = []
        
        for segment in segments:
            # 索引
            srt_lines.append(str(segment.index))
            
            # 時間戳（SRT 格式：HH:MM:SS,mmm）
            start = self._format_srt_timestamp(segment.start_time)
            end = self._format_srt_timestamp(segment.end_time)
            srt_lines.append(f"{start} --> {end}")
            
            # 文字
            srt_lines.append(segment.text)
            
            # 空行分隔
            srt_lines.append("")
        
        return "\n".join(srt_lines)
    
    def _format_srt_timestamp(self, seconds: float) -> str:
        """
        格式化為 SRT 時間戳 (HH:MM:SS,mmm)
        
        Args:
            seconds: 秒數
            
        Returns:
            SRT 格式時間戳
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def generate_ass_content(self, segments: List[SubtitleSegment]) -> str:
        """
        生成 ASS 格式字幕內容
        
        Args:
            segments: 字幕片段列表
            
        Returns:
            ASS 格式字串
        """
        lines = []
        
        # Script Info
        lines.append("[Script Info]")
        lines.append("ScriptType: v4.00+")
        lines.append("PlayResX: 1920")
        lines.append("PlayResY: 1080")
        lines.append("WrapStyle: 0")
        lines.append("")
        
        # Styles
        lines.append("[V4+ Styles]")
        lines.append("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding")
        lines.append("Style: Default,Arial,56,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,2,10,10,30,1")
        lines.append("")
        
        # Events
        lines.append("[Events]")
        lines.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")
        
        for segment in segments:
            start = self._format_ass_timestamp(segment.start_time)
            end = self._format_ass_timestamp(segment.end_time)
            # ASS 文字中的換行用 \N 表示
            text = segment.text.replace("\n", "\\N")
            lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")
        
        return "\n".join(lines)
    
    def _format_ass_timestamp(self, seconds: float) -> str:
        """
        格式化為 ASS 時間戳 (H:MM:SS.cc)
        
        Args:
            seconds: 秒數
            
        Returns:
            ASS 格式時間戳
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centisecs = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"
    
    def merge_subtitles(self, subtitle_paths: List[str], languages: List[str], output_format: str = "srt") -> str:
        """
        合併多個語言的字幕為單一檔案（垂直排列）
        
        Args:
            subtitle_paths: 字幕檔案路徑列表
            languages: 語言代碼列表（對應順序）
            output_format: 輸出格式（"srt" 或 "vtt"）
            
        Returns:
            合併後的字幕內容
        """
        try:
            # 解析所有字幕檔案
            all_segments = []
            for path in subtitle_paths:
                segments = self.parse_vtt(path)
                all_segments.append(segments)
            
            # 確保所有字幕有相同數量的片段
            min_length = min(len(segs) for segs in all_segments)
            
            # 根據格式生成合併字幕
            if output_format.lower() == "vtt":
                return self._merge_to_vtt(all_segments, min_length, languages)
            else:
                return self._merge_to_srt(all_segments, min_length, languages)
            
        except Exception as e:
            logger.error(f"合併字幕失敗: {e}")
            raise
    
    def _merge_to_srt(self, all_segments: List[List[SubtitleSegment]], min_length: int, languages: List[str]) -> str:
        """
        合併字幕為 SRT 格式
        
        Args:
            all_segments: 所有語言的字幕片段列表
            min_length: 最小片段數量
            languages: 語言代碼列表
            
        Returns:
            SRT 格式字串
        """
        merged_lines = []
        for i in range(min_length):
            # 索引
            merged_lines.append(str(i + 1))
            
            # 使用第一個字幕的時間戳
            segment = all_segments[0][i]
            start = self._format_srt_timestamp(segment.start_time)
            end = self._format_srt_timestamp(segment.end_time)
            merged_lines.append(f"{start} --> {end}")
            
            # 合併所有語言的文字（垂直排列）
            texts = []
            for segs in all_segments:
                if i < len(segs):
                    texts.append(segs[i].text)
            
            merged_lines.append("\n".join(texts))
            
            # 空行分隔
            merged_lines.append("")
        
        logger.info(f"已合併 {len(languages)} 種語言的字幕為 SRT 格式，共 {min_length} 個片段")
        return "\n".join(merged_lines)
    
    def _merge_to_vtt(self, all_segments: List[List[SubtitleSegment]], min_length: int, languages: List[str]) -> str:
        """
        合併字幕為 VTT 格式
        
        Args:
            all_segments: 所有語言的字幕片段列表
            min_length: 最小片段數量
            languages: 語言代碼列表
            
        Returns:
            VTT 格式字串
        """
        merged_lines = ["WEBVTT", ""]
        
        for i in range(min_length):
            # 索引
            merged_lines.append(str(i + 1))
            
            # 使用第一個字幕的時間戳（VTT 格式）
            segment = all_segments[0][i]
            start = segment.format_vtt_timestamp(segment.start_time)
            end = segment.format_vtt_timestamp(segment.end_time)
            merged_lines.append(f"{start} --> {end}")
            
            # 合併所有語言的文字（垂直排列）
            texts = []
            for segs in all_segments:
                if i < len(segs):
                    # 轉義 VTT 特殊字元
                    escaped_text = segment._escape_vtt_text(segs[i].text)
                    texts.append(escaped_text)
            
            merged_lines.append("\n".join(texts))
            
            # 空行分隔
            merged_lines.append("")
        
        logger.info(f"已合併 {len(languages)} 種語言的字幕為 VTT 格式，共 {min_length} 個片段")
        return "\n".join(merged_lines)
