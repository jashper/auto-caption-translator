# 維護指南

## 版本檢查

檢查當前環境版本是否一致：

```bash
python check_versions.py
```

如果版本不一致：

```bash
pip install -r requirements-locked.txt --force-reinstall
```

## 當前版本

已驗證可用的版本：

```
whisperx==3.7.2
torch==2.8.0+cpu
torchaudio==2.8.0+cpu
```

**注意：** 最新版本是 whisperx 3.8.2，但 3.7.2 已驗證穩定，建議保持不變。

## 常見警告（可忽略）

運行時可能看到以下警告，**不影響功能**：

1. `torchaudio._backend.list_audio_backends has been deprecated` - pyannote.audio 內部問題
2. `Model was trained with pyannote.audio 0.0.1, yours is 3.4.0` - WhisperX 已適配
3. `Model was trained with torch 1.10.0, yours is 2.8.0` - PyTorch 向後兼容

這些警告已在代碼中過濾。

## 更新依賴（謹慎）

如需更新依賴：

```bash
# 1. 創建測試分支
git checkout -b test-update

# 2. 更新特定包
pip install whisperx==3.8.2 --upgrade

# 3. 測試功能
# 上傳測試影片，驗證所有功能

# 4. 如果測試通過
pip freeze > requirements-frozen.txt
# 手動更新 requirements-locked.txt

# 5. 如果測試失敗，回滾
pip install whisperx==3.7.2 --force-reinstall
```

## 首次運行

首次運行會下載約 1.5GB 的模型文件，緩存在：
- `~/.cache/huggingface/`
- `~/.cache/torch/`

後續運行會使用緩存，不需要重新下載。

## 相關文檔

- [README.md](README.md) - 項目概述
- [INSTALLATION.md](INSTALLATION.md) - 安裝指南
- [CHANGELOG.md](CHANGELOG.md) - 版本歷史
