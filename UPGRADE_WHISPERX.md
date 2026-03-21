# 升級到 WhisperX 指南

## 已完成的改動

✅ 代碼已更新為使用 WhisperX
✅ requirements.txt 已更新
✅ Git 提交已完成

## 下一步：安裝依賴

### 方法 1：重新安裝所有依賴（推薦）

```bash
# 1. 停止服務器（如果正在運行）
# 關閉 START.bat 視窗或按 Ctrl+C

# 2. 卸載舊的 Whisper
pip uninstall openai-whisper -y

# 3. 安裝 WhisperX 和所有依賴
pip install -r requirements.txt

# 4. 重新啟動服務器
START.bat
```

### 方法 2：只安裝 WhisperX

```bash
pip uninstall openai-whisper -y
pip install whisperx==3.1.1
```

## 首次運行

首次使用 WhisperX 時，系統會自動下載：
1. Whisper 模型（如果尚未下載）
2. 對齊模型（alignment model）- 約 100MB

這是一次性的下載，之後會使用緩存。

## 預期效果

**改善前（Whisper）：**
```
1. I want to
2. go to the store
3. and buy some
4. groceries
```

**改善後（WhisperX）：**
```
1. I want to go to the store and buy some groceries.
```

## 驗證安裝

運行以下命令確認 WhisperX 已正確安裝：

```bash
python -c "import whisperx; print('WhisperX version:', whisperx.__version__)"
```

應該顯示：`WhisperX version: 3.1.1`

## 如果遇到問題

### 問題 1：找不到 ffmpeg
```
錯誤：ffmpeg not found
解決：確保 ffmpeg 已安裝並在 PATH 中
```

### 問題 2：記憶體不足
```
錯誤：Out of memory
解決：使用較小的模型（tiny 或 base）
在 .env 中設置：WHISPER_MODEL_SIZE=base
```

### 問題 3：下載模型失敗
```
錯誤：Failed to download model
解決：檢查網路連接，或手動下載模型
```

## 回滾到舊版本

如果需要回到 Whisper：

```bash
git revert HEAD
pip uninstall whisperx -y
pip install openai-whisper==20231117
```

## 技術細節

WhisperX 的處理流程：
1. **轉錄**：使用 faster-whisper 進行初始轉錄
2. **對齊**：使用 forced alignment 精確對齊時間戳
3. **輸出**：生成詞級別的時間戳和更好的句子分段

處理時間：
- 比標準 Whisper 慢約 20-30%（因為多了對齊步驟）
- 但字幕質量顯著提升

## 完成

安裝完成後，上傳一個測試影片，對比字幕質量！
