# Git 提交指南

## 當前狀態

專案已完成 v2.3.0 版本的開發和清理工作。

## 提交步驟

### 1. 查看更改
```bash
git status
```

### 2. 添加所有更改
```bash
git add .
```

### 3. 提交更改
```bash
git commit -m "Release v2.3.0: Playback speed control and PiP improvements

- Added playback speed control (0.5x-3x)
- Fixed PiP mode speed synchronization
- Fixed keyboard shortcuts in PiP mode
- Fixed subtitle time jump in PiP mode
- Cleaned up temporary debug files
- Updated documentation and changelog"
```

### 4. 創建版本標籤
```bash
git tag -a v2.3.0 -m "Version 2.3.0 - Playback speed control and PiP improvements"
```

### 5. 推送到遠程倉庫
```bash
# 推送代碼
git push origin master

# 推送標籤
git push origin v2.3.0
```

## 本次更新摘要

### 新增功能
- ✅ 播放速度控制（0.5×-3×）
- ✅ 畫中畫模式速度同步
- ✅ 鍵盤快捷鍵在畫中畫模式下正常工作
- ✅ 點擊字幕時間在畫中畫模式下正確跳轉

### Bug 修復
- ✅ 修復速度選單事件綁定問題
- ✅ 修復 videoPlayer 未定義錯誤
- ✅ 修復瀏覽器緩存問題

### 專案清理
- ✅ 移除 31 個臨時調試文檔
- ✅ 整理測試文件到 tests/ 文件夾
- ✅ 更新 .gitignore 規則
- ✅ 更新 CHANGELOG.md
- ✅ 更新 README.md

### 文件統計
- 刪除：31 個臨時文件
- 新增：2 個指南文件（VERSION_TAG.md, GIT_COMMIT_GUIDE.md）
- 修改：7 個核心文件
- 移動：4 個測試文件到 tests/

## 驗證清單

提交前請確認：
- [ ] 所有功能測試通過
- [ ] 播放速度控制正常工作
- [ ] 畫中畫模式正常工作
- [ ] 鍵盤快捷鍵正常工作
- [ ] 字幕時間跳轉正常工作
- [ ] 文檔已更新
- [ ] 臨時文件已清理

## 下一步

提交完成後，可以：
1. 在 GitHub 上查看版本標籤
2. 創建 Release 說明
3. 通知團隊成員更新

## 回滾方法

如果需要回滾到之前的版本：
```bash
# 查看所有版本
git tag -l

# 切換到特定版本
git checkout v2.2.0

# 返回最新版本
git checkout master
```
