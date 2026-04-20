"""
轉錄服務
使用 WhisperX 模型將影片轉錄為英文字幕（帶精確時間戳對齊）
"""
import os
import warnings
from typing import List
import whisperx
import ffmpeg
import gc
import torch

from src.models.subtitle import SubtitleSegment
from src.config import WHISPER_MODEL_SIZE, DEVICE
from src.utils.logger import get_logger

# 過濾已知的兼容性警告（這些警告不影響功能）
warnings.filterwarnings('ignore', message='.*torchaudio._backend.list_audio_backends.*')
warnings.filterwarnings('ignore', message='.*Model was trained with pyannote.audio.*')
warnings.filterwarnings('ignore', message='.*Model was trained with torch.*')

logger = get_logger("transcription")


class TranscriptionService:
    """音訊轉錄服務（使用 WhisperX）"""
    
    # 各模型的大約大小（GB），用於顯示給用戶
    MODEL_SIZES = {
        'tiny': 0.07,
        'base': 0.14,
        'small': 0.46,
        'medium': 1.5,
        'large': 3.0,
        'large-v1': 3.0,
        'large-v2': 3.0,
        'large-v3': 3.0,
    }
    
    # model_size → Hugging Face repo 名稱的映射
    _REPO_NAME_MAP = {
        'large': 'faster-whisper-large-v3',
        'large-v1': 'faster-whisper-large-v1',
        'large-v2': 'faster-whisper-large-v2',
        'large-v3': 'faster-whisper-large-v3',
    }
    
    # 標準模型名稱列表（非自訂模型）
    _STANDARD_MODELS = {'tiny', 'base', 'small', 'medium', 'large', 'large-v1', 'large-v2', 'large-v3'}
    
    def _is_custom_model(self) -> bool:
        """檢查是否為自訂 HuggingFace 模型（包含 / 表示 repo ID）"""
        return '/' in self.model_size
    
    def _get_repo_name(self) -> str:
        """取得模型對應的 Hugging Face repo 資料夾名稱"""
        if self._is_custom_model():
            # 自訂模型：org/model-name → models--org--model-name
            return f"models--{self.model_size.replace('/', '--')}"
        suffix = self._REPO_NAME_MAP.get(self.model_size, f"faster-whisper-{self.model_size}")
        return f"models--Systran--{suffix}"
    
    def _resolve_device(self) -> tuple:
        """
        根據 DEVICE 環境變數決定使用的裝置和計算類型
        
        Returns:
            (device, compute_type) 元組
        """
        device_setting = DEVICE.lower().strip()
        
        if device_setting == "cuda":
            if torch.cuda.is_available():
                logger.info(f"使用 GPU (CUDA): {torch.cuda.get_device_name(0)}")
                return "cuda", "float16"
            else:
                logger.warning("指定 CUDA 但 GPU 不可用，降級為 CPU")
                return "cpu", "int8"
        elif device_setting == "cpu":
            logger.info("使用 CPU（手動指定）")
            return "cpu", "int8"
        else:
            # auto：自動偵測
            if torch.cuda.is_available():
                logger.info(f"自動偵測到 GPU: {torch.cuda.get_device_name(0)}")
                return "cuda", "float16"
            else:
                logger.info("未偵測到 GPU，使用 CPU")
                return "cpu", "int8"
    
    def __init__(self, model_size: str = WHISPER_MODEL_SIZE):
        """
        初始化轉錄服務
        
        Args:
            model_size: Whisper 模型大小 (tiny, base, small, medium, large)
                        或 HuggingFace repo ID (例如 MediaTek-Research/Breeze-ASR-26)
        """
        self.model_size = model_size
        self.device, self.compute_type = self._resolve_device()
        self.model = None
        self.model_status = "not_loaded"  # not_loaded / checking / downloading / loading / ready / error
        self.model_status_message = ""
        self._last_loaded_size = self._read_last_model_size()
    
    def _get_cache_dir(self) -> 'Path':
        """取得 Hugging Face 模型快取目錄"""
        from pathlib import Path
        return Path.home() / ".cache" / "huggingface" / "hub"
    
    def _is_model_cached(self) -> bool:
        """檢查模型是否已完整下載到本地快取"""
        # 自訂模型：檢查對應的 HuggingFace cache 目錄
        cache_dir = self._get_cache_dir()
        model_dir = cache_dir / self._get_repo_name()
        
        if not model_dir.exists():
            return False
        
        # 檢查是否有 .incomplete 檔案（代表下載未完成）
        blobs_dir = model_dir / "blobs"
        if blobs_dir.exists():
            for f in blobs_dir.iterdir():
                if f.name.endswith('.incomplete'):
                    return False
        
        # 確認 snapshots 目錄存在且有內容
        snapshots_dir = model_dir / "snapshots"
        if not snapshots_dir.exists():
            return False
        for snapshot in snapshots_dir.iterdir():
            if snapshot.is_dir():
                # 自訂模型可能不叫 model.bin，只要有大檔案就算已快取
                if self._is_custom_model():
                    for f in snapshot.iterdir():
                        if f.is_file() and f.stat().st_size > 50_000_000:
                            return True
                else:
                    model_bin = snapshot / "model.bin"
                    if model_bin.exists() and model_bin.stat().st_size > 100_000_000:
                        return True
        return False
    
    def _get_last_model_file(self) -> 'Path':
        """取得記錄上一次模型大小的檔案路徑"""
        from pathlib import Path
        return Path(__file__).parent.parent.parent / "logs" / ".last_model_size"
    
    def _read_last_model_size(self) -> str:
        """讀取上一次成功載入的模型大小"""
        try:
            f = self._get_last_model_file()
            if f.exists():
                return f.read_text().strip()
        except Exception:
            pass
        return ""
    
    def _save_last_model_size(self) -> None:
        """儲存當前成功載入的模型大小"""
        try:
            f = self._get_last_model_file()
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(self.model_size)
        except Exception:
            pass
    
    def _get_download_progress(self) -> float:
        """檢查模型下載進度（0.0 ~ 1.0），如果沒在下載則回傳 -1"""
        cache_dir = self._get_cache_dir()
        blobs_dir = cache_dir / self._get_repo_name() / "blobs"
        if not blobs_dir.exists():
            return -1
        for f in blobs_dir.iterdir():
            if f.name.endswith('.incomplete'):
                downloaded_mb = f.stat().st_size / (1024 * 1024)
                total_mb = self.MODEL_SIZES.get(self.model_size, 1.5) * 1024
                return min(downloaded_mb / total_mb, 0.99) if total_mb > 0 else 0
        return -1
    
    def get_model_info(self) -> dict:
        """回傳模型狀態資訊（供 API 使用）"""
        size_gb = self.MODEL_SIZES.get(self.model_size, 0)
        is_cached = self._is_model_cached()
        changed_from = self._last_loaded_size if self._last_loaded_size and self._last_loaded_size != self.model_size else None
        
        # 動態更新下載狀態訊息
        if self.model_status in ("downloading", "loading") and not is_cached:
            progress = self._get_download_progress()
            if progress >= 0:
                self.model_status = "downloading"
                pct = int(progress * 100)
                change_prefix = f"模型變更：{changed_from} → {self.model_size}，" if changed_from else ""
                size_info = f"約 {size_gb}GB" if size_gb > 0 else "大小未知"
                self.model_status_message = f"{change_prefix}正在下載 {self.model_size} 模型（{pct}%，{size_info}）..."
        
        return {
            "model_size": self.model_size,
            "model_size_gb": size_gb,
            "is_cached": is_cached,
            "is_custom_model": self._is_custom_model(),
            "device": self.device,
            "status": self.model_status,
            "status_message": self.model_status_message,
            "changed_from": changed_from,
        }
    
    def _load_model(self) -> None:
        """載入 WhisperX 模型（自動偵測快取狀態，智能提示）"""
        try:
            size_gb = self.MODEL_SIZES.get(self.model_size, 0)
            is_cached = self._is_model_cached()
            changed = self._last_loaded_size and self._last_loaded_size != self.model_size
            
            # 智能日誌提示
            if changed:
                logger.info(f"偵測到模型變更: {self._last_loaded_size} → {self.model_size}")
            
            change_prefix = f"模型變更：{self._last_loaded_size} → {self.model_size}，" if changed else ""
            model_label = self.model_size
            size_info = f"約 {size_gb}GB" if size_gb > 0 else "大小未知"
            
            if is_cached:
                self.model_status = "loading"
                self.model_status_message = f"{change_prefix}正在載入 {model_label} 模型（已快取，{size_info}）..."
                logger.info(self.model_status_message)
            else:
                self.model_status = "downloading"
                self.model_status_message = f"{change_prefix}正在下載 {model_label} 模型（{size_info}，首次下載可能需要幾分鐘）..."
                logger.info(self.model_status_message)
            
            # 完全禁用 weights_only 檢查（WhisperX 模型是可信的）
            original_load = torch.load
            
            def force_weights_only_false(*args, **kwargs):
                kwargs['weights_only'] = False
                return original_load(*args, **kwargs)
            
            torch.load = force_weights_only_false
            
            try:
                self.model = whisperx.load_model(
                    self.model_size, 
                    self.device, 
                    compute_type=self.compute_type,
                    vad_options={"vad_onset": 0.35, "vad_offset": 0.25}
                )
            finally:
                torch.load = original_load
            
            self.model_status = "ready"
            self.model_status_message = f"{model_label} 模型載入完成（{self.device}）"
            self._save_last_model_size()
            logger.info(f"WhisperX 模型載入成功: {model_label}（裝置: {self.device}）")
        except Exception as e:
            self.model_status = "error"
            self.model_status_message = f"模型載入失敗: {str(e)[:100]}"
            logger.error(f"載入 WhisperX 模型失敗: {e}")
            raise RuntimeError(f"無法載入 WhisperX 模型: {e}")
    
    # ── 字幕斷句常量 ──
    # 超過此秒數的段落會嘗試拆分
    SEGMENT_MAX_DURATION = 8.0
    # 超過此字元數的段落會嘗試拆分
    SEGMENT_MAX_CHARS = 80
    # 拆分後每段的最小字元數（避免太碎）
    SEGMENT_MIN_CHARS = 30
    
    # 英文標點和連接詞切割符號
    _PUNCT_SPLIT = {'.', ',', '!', '?', ';', ':'}
    _CONJ_SPLIT = {'and', 'but', 'so', 'because', 'however', 'then', 'also', 'yet'}
    
    def _split_long_segments(self, segments: list) -> list:
        """
        後處理：利用 word-level timestamps 將過長的字幕段落拆分成適合閱讀的長度。
        
        拆分策略：
        1. 若段落 ≤ max_duration 且 ≤ max_chars，保留原樣
        2. 若段落有 word-level timestamps，在標點或連接詞處拆分
        3. 若沒有 word-level timestamps，按字元數均分（使用段落的起止時間線性插值）
        
        Args:
            segments: WhisperX align 後的 segments 列表（含 words 欄位）
            
        Returns:
            拆分後的 segments 列表
        """
        result = []
        
        for seg in segments:
            duration = seg['end'] - seg['start']
            text = seg.get('text', '').strip()
            words = seg.get('words', [])
            
            # 不需要拆分的段落
            if duration <= self.SEGMENT_MAX_DURATION and len(text) <= self.SEGMENT_MAX_CHARS:
                result.append(seg)
                continue
            
            # 有 word-level timestamps → 按標點/連接詞智能拆分
            if words and len(words) >= 2:
                sub_segs = self._split_by_words(seg, words)
                result.extend(sub_segs)
            else:
                # 沒有 word timestamps → 保留原樣（不做硬切，以免破壞語意）
                result.append(seg)
        
        split_count = len(result) - len(segments)
        if split_count > 0:
            logger.info(f"字幕斷句後處理：{len(segments)} 段 → {len(result)} 段（拆分了 {split_count} 段）")
        
        return result
    
    def _split_by_words(self, seg: dict, words: list) -> list:
        """
        利用 word-level timestamps 在標點/連接詞處拆分一個段落。
        
        Args:
            seg: 原始段落 dict
            words: word-level timestamps 列表，每個元素含 word, start, end
            
        Returns:
            拆分後的子段落列表
        """
        # 過濾掉缺少時間戳的 word（alignment 有時會失敗）
        valid_words = [w for w in words if 'start' in w and 'end' in w]
        if len(valid_words) < 2:
            return [seg]
        
        # 找出所有合理的切割點
        split_candidates = []
        char_count = 0
        
        for i, w in enumerate(valid_words):
            word_text = w.get('word', '').strip()
            char_count += len(word_text) + 1  # +1 for space
            
            # 不在頭尾切
            if i == 0 or i == len(valid_words) - 1:
                continue
            
            # 累積字元太少不切（避免太碎）
            if char_count < self.SEGMENT_MIN_CHARS:
                continue
            
            is_punct = any(word_text.endswith(p) for p in self._PUNCT_SPLIT)
            # 下一個字是連接詞 → 在這個字後面切
            next_word = valid_words[i + 1].get('word', '').strip().lower() if i + 1 < len(valid_words) else ''
            is_before_conj = next_word in self._CONJ_SPLIT
            
            if is_punct or is_before_conj:
                split_candidates.append((i, char_count))
                char_count = 0
        
        if not split_candidates:
            # 沒找到好的切割點 → 按時間/字數均分
            return self._split_evenly(seg, valid_words)
        
        # 根據切割點生成子段落
        sub_segments = []
        start_word_idx = 0
        
        for cut_idx, _ in split_candidates:
            chunk_words = valid_words[start_word_idx:cut_idx + 1]
            if chunk_words:
                sub_seg = self._make_sub_segment(chunk_words)
                sub_segments.append(sub_seg)
            start_word_idx = cut_idx + 1
        
        # 最後一段
        if start_word_idx < len(valid_words):
            chunk_words = valid_words[start_word_idx:]
            if chunk_words:
                sub_seg = self._make_sub_segment(chunk_words)
                sub_segments.append(sub_seg)
        
        return sub_segments if sub_segments else [seg]
    
    def _split_evenly(self, seg: dict, valid_words: list) -> list:
        """
        當找不到標點/連接詞切割點時，按字數大致均分。
        
        Args:
            seg: 原始段落
            valid_words: 有時間戳的 word 列表
            
        Returns:
            均分後的子段落列表
        """
        total_text = seg.get('text', '').strip()
        duration = seg['end'] - seg['start']
        # 計算需要拆成幾段
        num_parts = max(2, int(duration / self.SEGMENT_MAX_DURATION) + 1)
        words_per_part = max(1, len(valid_words) // num_parts)
        
        sub_segments = []
        for i in range(0, len(valid_words), words_per_part):
            chunk = valid_words[i:i + words_per_part]
            if chunk:
                sub_segments.append(self._make_sub_segment(chunk))
        
        return sub_segments if sub_segments else [seg]
    
    def _make_sub_segment(self, chunk_words: list) -> dict:
        """
        從一組 word 建立一個子段落 dict。
        
        Args:
            chunk_words: word-level timestamps 列表
            
        Returns:
            段落 dict，格式與 WhisperX segments 相同
        """
        text = ' '.join(w.get('word', '').strip() for w in chunk_words)
        return {
            'start': chunk_words[0]['start'],
            'end': chunk_words[-1]['end'],
            'text': text,
            'words': chunk_words,
        }
    
    def _detect_language_multi_segment(self, audio) -> str:
        """
        多段語言偵測：取開頭、中間、結尾各 30 秒做投票，提升偵測準確度
        
        Args:
            audio: whisperx 載入的音訊數據
            
        Returns:
            偵測到的語言代碼
        """
        sample_rate = 16000
        segment_duration = 30 * sample_rate  # 30 秒
        total_length = len(audio)
        
        # 如果音訊短於 60 秒，只用前 30 秒偵測
        if total_length <= 60 * sample_rate:
            sample_length = min(total_length, segment_duration)
            result = self.model.transcribe(audio[:sample_length], batch_size=16)
            return result.get("language", "en")
        
        # 取三段：開頭、中間、結尾
        positions = [
            0,                                          # 開頭
            max(0, (total_length // 2) - (segment_duration // 2)),  # 中間
            max(0, total_length - segment_duration),    # 結尾
        ]
        
        detected_languages = []
        for pos in positions:
            end = min(pos + segment_duration, total_length)
            sample = audio[pos:end]
            try:
                result = self.model.transcribe(sample, batch_size=16)
                lang = result.get("language", "en")
                detected_languages.append(lang)
            except Exception as e:
                logger.warning(f"語言偵測片段失敗（位置 {pos}）: {e}")
        
        if not detected_languages:
            return "en"
        
        # 多數決投票
        from collections import Counter
        counter = Counter(detected_languages)
        winner = counter.most_common(1)[0][0]
        
        if len(set(detected_languages)) > 1:
            logger.info(f"多段語言偵測結果: {detected_languages}，採用多數決: {winner}")
        
        return winner
    
    def extract_audio(self, video_path: str) -> str:
        """
        從影片提取音訊
        
        Args:
            video_path: 影片檔案路徑
            
        Returns:
            音訊檔案路徑
        """
        try:
            # 生成音訊檔案路徑（存放在與影片相同的任務資料夾）
            audio_dir = os.path.dirname(video_path)
            audio_path = os.path.join(audio_dir, 'audio.wav')
            
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
    
    def _transcribe_sync(self, video_path: str, language: str = None) -> tuple[List[SubtitleSegment], str, str]:
        """
        同步轉錄（在執行緒池中執行，避免阻塞事件循環）
        """
        # 延遲載入模型（第一次使用時）
        if self.model is None:
            self._load_model()
        
        audio_path = None
        try:
            # 提取音訊
            audio_path = self.extract_audio(video_path)
            
            # 步驟 1: 使用 WhisperX 轉錄
            logger.info(f"正在轉錄音訊: {audio_path}")
            audio = whisperx.load_audio(audio_path)
            
            # 步驟 0: 多段語言偵測（取開頭/中間/結尾各 30 秒做投票）
            auto_detected_language = self._detect_language_multi_segment(audio)
            logger.info(f"自動偵測語言: {auto_detected_language}")
            
            if language:
                # 使用者指定語言 → 直接用，跳過自動偵測
                logger.info(f"使用指定語言: {language}")
                if language != auto_detected_language:
                    logger.warning(f"語言不符：使用者指定 {language}，偵測到 {auto_detected_language}")
                result = self.model.transcribe(audio, batch_size=16, language=language)
                used_language = language
            else:
                # 未指定 → 讓 WhisperX 自動偵測（使用完整音訊）
                logger.info("未指定語言，使用自動偵測")
                result = self.model.transcribe(audio, batch_size=16)
                used_language = result.get("language", "en")
                auto_detected_language = used_language
            logger.info(f"轉錄完成，共 {len(result['segments'])} 個初始片段")
            
            # 步驟 2: 載入對齊模型並進行精確對齊
            logger.info("正在進行時間戳對齊...")
            try:
                align_model, metadata = whisperx.load_align_model(
                    language_code=used_language, 
                    device=self.device
                )
                
                result = whisperx.align(
                    result["segments"], 
                    align_model, 
                    metadata, 
                    audio, 
                    self.device, 
                    return_char_alignments=False
                )
                
                logger.info("時間戳對齊完成")
                
                # 清理對齊模型以釋放記憶體
                del align_model
                gc.collect()
                if self.device != "cpu":
                    torch.cuda.empty_cache()
            except Exception as e:
                # 如果對齊失敗（例如語言不支援），使用原始時間戳
                logger.warning(f"時間戳對齊失敗（語言 {used_language} 可能不支援對齊模型），使用原始時間戳: {e}")
                # result 已經包含原始時間戳，繼續使用
            
            # 步驟 3: 後處理斷句 — 拆分過長的段落
            result['segments'] = self._split_long_segments(result['segments'])
            
            # 轉換為 SubtitleSegment 列表（使用檢測到的語言）
            segments = []
            for idx, segment in enumerate(result['segments'], start=1):
                subtitle_segment = SubtitleSegment(
                    index=idx,
                    start_time=segment['start'],
                    end_time=segment['end'],
                    text=segment['text'].strip(),
                    language=used_language  # 使用檢測到的語言，而非硬編碼
                )
                segments.append(subtitle_segment)
            
            # 按開始時間排序
            segments.sort(key=lambda s: s.start_time)
            
            # 重新編號
            for idx, segment in enumerate(segments, start=1):
                segment.index = idx
            
            logger.info(f"轉錄完成，共 {len(segments)} 個字幕片段（已對齊），語言: {used_language}")
            return segments, used_language, auto_detected_language
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

    async def transcribe(self, video_path: str, language: str = None) -> tuple[List[SubtitleSegment], str, str]:
        """
        轉錄影片為原語言字幕（使用 WhisperX 進行精確對齊和語言檢測）
        
        透過 run_in_executor 在執行緒池中執行，避免阻塞事件循環，
        確保狀態輪詢等 API 在轉錄期間仍可正常回應。
        
        Args:
            video_path: 影片檔案路徑
            language: 指定語言代碼（例如 'en', 'zh', 'ms'），None 則自動偵測
            
        Returns:
            (字幕片段列表, 使用的語言代碼, 自動偵測的語言代碼)
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._transcribe_sync, video_path, language)
