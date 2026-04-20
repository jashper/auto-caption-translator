"""測試檔案驗證邏輯 — 格式檢查、大小檢查"""

from src.validators.file_validator import Validator, ValidationResult


class TestValidationResult:
    """測試 ValidationResult 資料結構"""

    def test_success(self):
        """成功結果：is_valid=True，沒有錯誤訊息"""
        result = ValidationResult.success()
        assert result.is_valid is True
        assert result.error_message is None
        assert result.error_code is None

    def test_failure(self):
        """失敗結果：is_valid=False，有錯誤訊息和代碼"""
        result = ValidationResult.failure("檔案太大", "FILE_TOO_LARGE")
        assert result.is_valid is False
        assert result.error_message == "檔案太大"
        assert result.error_code == "FILE_TOO_LARGE"


class TestValidateFileFormat:
    """測試：檔案格式是否被接受"""

    def setup_method(self):
        """每個測試前，建立一個新的 Validator"""
        self.validator = Validator()

    # --- 應該通過的格式 ---

    def test_mp4(self):
        assert self.validator.validate_file_format("video.mp4") is True

    def test_avi(self):
        assert self.validator.validate_file_format("video.avi") is True

    def test_mov(self):
        assert self.validator.validate_file_format("video.mov") is True

    def test_mkv(self):
        assert self.validator.validate_file_format("video.mkv") is True

    def test_uppercase_extension(self):
        """大寫副檔名也應該通過（如 VIDEO.MP4）"""
        assert self.validator.validate_file_format("VIDEO.MP4") is True

    def test_mixed_case(self):
        """混合大小寫也通過"""
        assert self.validator.validate_file_format("video.Mp4") is True

    # --- 應該拒絕的格式 ---

    def test_reject_txt(self):
        assert self.validator.validate_file_format("readme.txt") is False

    def test_reject_mp3(self):
        """音訊檔不是影片"""
        assert self.validator.validate_file_format("audio.mp3") is False

    def test_reject_exe(self):
        assert self.validator.validate_file_format("virus.exe") is False

    def test_reject_no_extension(self):
        """沒有副檔名的檔案"""
        assert self.validator.validate_file_format("noextension") is False

    def test_reject_empty_string(self):
        """空字串"""
        assert self.validator.validate_file_format("") is False


class TestValidateFileSize:
    """測試：檔案大小限制（最大 5GB）"""

    def setup_method(self):
        self.validator = Validator()
        self.ONE_GB = 1024 * 1024 * 1024

    def test_small_file_passes(self):
        """100MB 的檔案 → 通過"""
        result = self.validator.validate_file_size(100 * 1024 * 1024)
        assert result.is_valid is True

    def test_exactly_5gb_passes(self):
        """剛好 5GB → 通過（不是「超過」）"""
        result = self.validator.validate_file_size(5 * self.ONE_GB)
        assert result.is_valid is True

    def test_over_5gb_fails(self):
        """超過 5GB → 拒絕"""
        result = self.validator.validate_file_size(5 * self.ONE_GB + 1)
        assert result.is_valid is False
        assert result.error_code == "FILE_TOO_LARGE"

    def test_zero_bytes_passes(self):
        """0 bytes 的檔案 → 大小檢查通過（格式不在這裡檢查）"""
        result = self.validator.validate_file_size(0)
        assert result.is_valid is True

    def test_very_large_file_fails(self):
        """100GB → 當然拒絕"""
        result = self.validator.validate_file_size(100 * self.ONE_GB)
        assert result.is_valid is False
        assert result.error_code == "FILE_TOO_LARGE"
