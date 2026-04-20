# 版本標籤指南

## 當前版本：v2.4.2

### 創建版本標籤

在完成所有更改並提交後，執行以下命令創建版本標籤：

```bash
# 添加所有更改
git add .

# 提交更改
git commit -m "Release v2.4.2: Fixed language selection issue and model optimization"

# 創建帶註釋的標籤
git tag -a v2.4.2 -m "Version 2.4.2 - Fixed language selection issue and model optimization"

# 推送到遠程倉庫（包括標籤）
git push origin master
git push origin v2.4.2
```

### 查看版本

```bash
# 列出所有標籤
git tag -l

# 查看特定版本的詳細信息
git show v2.4.2

# 切換到特定版本
git checkout v2.4.2

# 返回最新版本
git checkout master
```

### 版本歷史

- **v2.4.2** (2024-03-23) - 修復語言選擇問題和模型優化（當前版本）
- **v2.4.1** (2024-03-23) - 緊急修復：中文影片處理問題
- **v2.4.0** (2024-03-23) - 多語言自動檢測與智能翻譯
- **v2.3.0** (2026-03-22) - 播放速度控制和畫中畫改進
- **v2.2.0** (2026-03-22) - 單語/雙語字幕模式和 CC 按鈕同步
- **v2.1.0** (2026-03-21) - 升級到 WhisperX 3.7.2
- **v2.0.0** (2026-03-20) - 視頻播放器和字幕編輯器
- **v1.0.0** (2026-03-20) - 初始版本

### 本次更新內容（v2.4.2）

#### 重要修復 🔥
- 修復語言選擇被忽略的問題（用戶勾選特定語言，系統仍翻譯所有語言）
- 移除前端默認勾選，用戶必須手動選擇需要的語言
- 優先使用用戶選擇的語言，沒有選擇時才使用自動檢測

#### 優化改進 ⚡
- 升級默認 Whisper 模型從 `base` 到 `small`
- 改善中文和馬來文的句子分段質量
- 添加詳細的模型選擇註釋和說明

#### 用戶體驗改進
- 用戶完全控制翻譯語言
- 只處理需要的語言，節省時間（最多減少 66% 處理時間）
- 更好的中文/馬來文分段質量

#### 技術改進
- `JobManager.process_job()`：優先使用 `state.target_languages`
- `static/index.html`：移除默認勾選
- `.env`：升級默認模型為 small，添加詳細註釋

#### 向後兼容
- ✅ 完全向後兼容
- ✅ 沒有指定語言時仍使用自動檢測
- ✅ 不影響現有 API 調用

詳細更改請查看 [CHANGELOG.md](CHANGELOG.md) 和 [RELEASE_v2.4.2.md](RELEASE_v2.4.2.md)


