"""測試翻譯片段處理邏輯 — SubtitleSegment 資料結構"""

import pytest
from src.models.subtitle import SubtitleSegment


def make_segment(**overrides):
    """建立一個預設的合法 segment，方便測試時只改需要改的欄位"""
    defaults = {
        "index": 1,
        "start_time": 0.0,
        "end_time": 5.0,
        "text": "Hello world",
        "language": "en",
    }
    defaults.update(overrides)
    return SubtitleSegment(**defaults)


# ============================================================
# 建立與驗證
# ============================================================
class TestSegmentCreation:
    """測試：建立字幕片段，驗證欄位是否正確"""

    def test_basic_creation(self):
        """正常建立一個片段"""
        seg = make_segment()
        assert seg.index == 1
        assert seg.start_time == 0.0
        assert seg.end_time == 5.0
        assert seg.text == "Hello world"
        assert seg.language == "en"
        assert seg.translation_failed is False

    def test_text_auto_strip(self):
        """文字前後的空白會被自動去除"""
        seg = make_segment(text="  Hello  ")
        assert seg.text == "Hello"

    def test_translation_failed_flag(self):
        """可以標記翻譯失敗"""
        seg = make_segment(translation_failed=True)
        assert seg.translation_failed is True


# ============================================================
# 驗證失敗的情況（應該拋出 ValueError）
# ============================================================
class TestSegmentValidation:
    """測試：非法資料應該被拒絕"""

    def test_reject_index_zero(self):
        """index 不能是 0"""
        with pytest.raises(ValueError, match="index"):
            make_segment(index=0)

    def test_reject_negative_index(self):
        """index 不能是負數"""
        with pytest.raises(ValueError, match="index"):
            make_segment(index=-1)

    def test_reject_negative_start_time(self):
        """開始時間不能是負數"""
        with pytest.raises(ValueError, match="start_time"):
            make_segment(start_time=-1.0)

    def test_reject_negative_end_time(self):
        """結束時間不能是負數"""
        with pytest.raises(ValueError, match="end_time"):
            make_segment(end_time=-1.0)

    def test_reject_start_after_end(self):
        """開始時間不能大於結束時間"""
        with pytest.raises(ValueError, match="start_time"):
            make_segment(start_time=10.0, end_time=5.0)

    def test_reject_empty_text(self):
        """文字不能為空"""
        with pytest.raises(ValueError, match="text"):
            make_segment(text="")

    def test_reject_whitespace_only_text(self):
        """只有空白的文字也不行"""
        with pytest.raises(ValueError, match="text"):
            make_segment(text="   ")

    def test_reject_unsupported_language(self):
        """不支援的語言代碼"""
        with pytest.raises(ValueError, match="不支援"):
            make_segment(language="fr")

    def test_accept_all_supported_languages(self):
        """所有支援的語言都能建立"""
        for lang in ["en", "zh", "zh-TW", "zh-CN", "ms"]:
            seg = make_segment(language=lang)
            assert seg.language == lang


# ============================================================
# 序列化（to_dict / from_dict）
# ============================================================
class TestSegmentSerialization:
    """測試：字幕片段轉成字典、從字典轉回來"""

    def test_to_dict(self):
        """轉成字典，欄位都在"""
        seg = make_segment()
        d = seg.to_dict()
        assert d["index"] == 1
        assert d["text"] == "Hello world"
        assert d["language"] == "en"
        assert d["translation_failed"] is False

    def test_from_dict(self):
        """從字典建回 segment"""
        data = {
            "index": 2,
            "start_time": 1.5,
            "end_time": 4.0,
            "text": "你好",
            "language": "zh-TW",
        }
        seg = SubtitleSegment.from_dict(data)
        assert seg.index == 2
        assert seg.text == "你好"
        assert seg.language == "zh-TW"

    def test_round_trip(self):
        """to_dict → from_dict 來回一趟，資料不變"""
        original = make_segment(index=3, text="Test", language="ms")
        restored = SubtitleSegment.from_dict(original.to_dict())
        assert original.to_dict() == restored.to_dict()


# ============================================================
# VTT 格式輸出
# ============================================================
class TestVttFormat:
    """測試：轉成 VTT 字幕格式"""

    def test_timestamp_format(self):
        """時間戳格式：HH:MM:SS.mmm"""
        seg = make_segment()
        assert seg.format_vtt_timestamp(0.0) == "00:00:00.000"
        assert seg.format_vtt_timestamp(61.5) == "00:01:01.500"
        assert seg.format_vtt_timestamp(3661.123) == "01:01:01.123"

    def test_vtt_output(self):
        """完整 VTT 片段格式"""
        seg = make_segment(index=1, start_time=0.0, end_time=5.0, text="Hello")
        vtt = seg.to_vtt_format()
        assert "1\n" in vtt
        assert "00:00:00.000 --> 00:00:05.000" in vtt
        assert "Hello" in vtt

    def test_vtt_escapes_html(self):
        """VTT 格式要轉義 HTML 特殊字元"""
        seg = make_segment(text="A < B & C > D")
        vtt = seg.to_vtt_format()
        assert "A &lt; B &amp; C &gt; D" in vtt
