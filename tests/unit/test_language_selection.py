"""測試主要語言策略 — Primary Language 相關邏輯"""

from src.models.subtitle import SubtitleSegment
from src.models.job import JobState, JobStatus
from datetime import datetime


class TestPrimaryLanguageConcept:
    """測試：主要語言策略的核心邏輯"""

    def test_job_state_has_primary_language(self):
        """JobState 應有 primary_language 欄位"""
        now = datetime.now()
        state = JobState(
            job_id="test-1",
            status=JobStatus.QUEUED,
            progress=0,
            stage="test",
            video_filename="test.mp4",
            video_path="/tmp/test.mp4",
            target_languages=["zh-TW", "ms"],
            created_at=now,
            updated_at=now,
            primary_language="en"
        )
        assert state.primary_language == "en"

    def test_job_state_has_language_mismatch(self):
        """JobState 應有 language_mismatch 欄位"""
        now = datetime.now()
        state = JobState(
            job_id="test-2",
            status=JobStatus.QUEUED,
            progress=0,
            stage="test",
            video_filename="test.mp4",
            video_path="/tmp/test.mp4",
            target_languages=["zh-TW"],
            created_at=now,
            updated_at=now,
            primary_language="en",
            language_mismatch=True
        )
        assert state.language_mismatch is True

    def test_job_state_has_language_distribution(self):
        """JobState 應有 language_distribution 欄位"""
        now = datetime.now()
        state = JobState(
            job_id="test-3",
            status=JobStatus.QUEUED,
            progress=0,
            stage="test",
            video_filename="test.mp4",
            video_path="/tmp/test.mp4",
            target_languages=["en"],
            created_at=now,
            updated_at=now,
            primary_language="zh",
            language_distribution={"zh": 100}
        )
        assert state.language_distribution == {"zh": 100}

    def test_job_state_defaults(self):
        """新欄位預設值"""
        now = datetime.now()
        state = JobState(
            job_id="test-4",
            status=JobStatus.QUEUED,
            progress=0,
            stage="test",
            video_filename="test.mp4",
            video_path="/tmp/test.mp4",
            target_languages=["en"],
            created_at=now,
            updated_at=now,
        )
        assert state.primary_language is None
        assert state.language_distribution is None
        assert state.language_mismatch is False


class TestSubtitleDirtyFlag:
    """測試：字幕 dirty 旗標"""

    def test_default_dirty_false(self):
        """新建字幕 dirty 預設為 False"""
        seg = SubtitleSegment(index=1, start_time=0.0, end_time=5.0, text="Hello", language="en")
        assert seg.dirty is False

    def test_set_dirty_true(self):
        """可以設定 dirty 為 True"""
        seg = SubtitleSegment(index=1, start_time=0.0, end_time=5.0, text="Hello", language="en", dirty=True)
        assert seg.dirty is True

    def test_dirty_in_to_dict(self):
        """dirty 旗標應出現在 to_dict 結果中"""
        seg = SubtitleSegment(index=1, start_time=0.0, end_time=5.0, text="Hello", language="en", dirty=True)
        d = seg.to_dict()
        assert d["dirty"] is True

    def test_dirty_from_dict(self):
        """from_dict 能正確還原 dirty"""
        data = {
            "index": 1, "start_time": 0.0, "end_time": 5.0,
            "text": "Hello", "language": "en", "dirty": True
        }
        seg = SubtitleSegment.from_dict(data)
        assert seg.dirty is True

    def test_from_dict_without_dirty(self):
        """舊格式（無 dirty）也能正常建立"""
        data = {
            "index": 1, "start_time": 0.0, "end_time": 5.0,
            "text": "Hello", "language": "en"
        }
        seg = SubtitleSegment.from_dict(data)
        assert seg.dirty is False
