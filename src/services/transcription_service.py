"""
轉錄服務
使用 Whisper 模型將影片轉錄為英文字幕
"""
import os
from typing import List
import whisper
import ffmpeg

from src.models.subtitle import SubtitleSegment
from src.config import WHISPER_MODEL_SIZE
from src.utils.logger import get_logger

logger = get_logger("transcription")


class TranscriptionService:
    """音訊轉錄服務"""
    
    def __init__(self, model_size: str = WHISPER_MODEL_SIZE):
        """
        初始化轉錄服務
        
        Args:
            model_size: Whisper 模型大小 (tiny, base, small, medium, large)
        """
        self.model_size = model_size
        self.model = None
        self._load_model()
    
    def _load_model(self) -> None:
        """載入 Whisper 模型"""
        try:
            logger.info(f"正在載入 Whisper 模型: {self.model_size}")
            self.model = whisper.load_model(self.model_size)
            logger.info(f"Whisper 模型載入成功: {self.model_size}")
        except Exception as e:
            logger.error(f"載入 Whisper 模型失敗: {e}")
            raise RuntimeError(f"無法載入 Whisper 模型: {e}")
    
    def extract_audio(self, video_path: str) -> str:
        """
        從影片提取音訊
        
        Args:
            video_path: 影片檔案路徑
            
        Returns:
            音訊檔案路徑
        """
        try:
            # 生成音訊檔案路徑
            audio_path = video_path.rsplit('.', 1)[0] + '_audio.wav'
            
            # 使用 ffmpeg 提取音訊
            logger.info(f"正在從影片提取音訊: {video_path}")
            (
                ffmpeg
                .input(video_path)
                .output(audio_path, acodec='pcm_s16le', ac=1, ar='16k')
                .overwrite_output()
                .run(quiet=True)
            )
            
            logger.info(f"音訊提取成功: {audio_path}")
            return audio_path
        except ffmpeg.Error as e:
            logger.error(f"音訊提取失敗: {e.stderr.decode() if e.stderr else str(e)}")
            raise RuntimeError(f"無法從影片提取音訊: {e}")
        except Exception as e:
            logger.error(f"音訊提取時發生錯誤: {e}")
            raise
    
    async def transcribe(self, video_path: str) -> List[SubtitleSegment]:
        """
        轉錄影片為英文字幕
        
        Args:
            video_path: 影片檔案路徑
            
        Returns:
            字幕片段列表
        """
        audio_path = None
        try:
            # 提取音訊
            audio_path = self.extract_audio(video_path)
            
            # 使用 Whisper 轉錄
            logger.info(f"正在轉錄音訊: {audio_path}")
            result = self.model.transcribe(
                audio_path,
                language="en",
                task="transcribe",
                fp16=False  # CPU 模式使用 FP32
            )
            
            # 轉換為 SubtitleSegment 列表
            segments = []
            for idx, segment in enumerate(result['segments'], start=1):
                subtitle_segment = SubtitleSegment(
                    index=idx,
                    start_time=segment['start'],
                    end_time=segment['end'],
                    text=segment['text'].strip(),
                    language="en"
                )
                segments.append(subtitle_segment)
            
            # 按開始時間排序
            segments.sort(key=lambda s: s.start_time)
            
            # 重新編號
            for idx, segment in enumerate(segments, start=1):
                segment.index = idx
            
            logger.info(f"轉錄完成，共 {len(segments)} 個字幕片段")
            return segments
        except Exception as e:
            logger.error(f"轉錄失敗: {e}")
            raise
        finally:
            # 清理臨時音訊檔案
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                    logger.debug(f"已刪除臨時音訊檔案: {audio_path}")
                except Exception as e:
                    logger.warning(f"刪除臨時音訊檔案失敗: {e}")
