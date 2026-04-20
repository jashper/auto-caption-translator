# 工具文件夾

這個文件夾包含專案的工具腳本。

## 清理存儲空間

### 使用方法（超簡單）

1. 右鍵點擊 `CLEAN_STORAGE.ps1`
2. 選擇「使用 PowerShell 運行」
3. 按 Y 確認

完成！

### 如果提示安全警告

打開 PowerShell，執行：
```
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

然後再次運行腳本。

---

## 文件說明

- **CLEAN_STORAGE.ps1** - 清理存儲空間腳本（使用這個！）
- **check_versions.py** - 檢查 Python 依賴版本
- **如何清理存儲空間.txt** - 詳細說明文檔

## storage 文件夾說明

- storage/uploads/ - 上傳的視頻（可以刪除）
- storage/subtitles/ - 生成的字幕（可以刪除）
- storage/jobs/ - 任務記錄（可以刪除）

清理後可以釋放大量磁盤空間。

## 手動清理（如果腳本不工作）

1. 打開 storage\uploads 文件夾
2. 選擇所有文件（Ctrl + A）
3. 刪除（Delete 鍵）
4. 對 storage\subtitles 和 storage\jobs 重複操作
