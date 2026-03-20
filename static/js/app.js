// 全域變數
let selectedFile = null;
let currentJobId = null;
let pollInterval = null;
let currentSubtitles = [];
let originalSubtitles = [];
let currentLanguage = 'en';
let isEditing = false;
let subtitleMode = 'single'; // 'single' or 'dual'
let availableLanguages = {};

// DOM 元素
const uploadArea = document.getElementById('upload-area');
const fileInput = document.getElementById('file-input');
const uploadBtn = document.getElementById('upload-btn');
const uploadSection = document.getElementById('upload-section');
const progressSection = document.getElementById('progress-section');
const resultSection = document.getElementById('result-section');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const stageText = document.getElementById('stage-text');

// 新增的 DOM 元素
const videoPlayer = document.getElementById('video-player');
const editLanguageSelect = document.getElementById('edit-language-select');
const subtitleEditorArea = document.getElementById('subtitle-editor-area');
const saveSubtitlesBtn = document.getElementById('save-subtitles-btn');
const resetSubtitlesBtn = document.getElementById('reset-subtitles-btn');
const batchDownloadBtn = document.getElementById('batch-download-btn');
const includeVideoCheckbox = document.getElementById('include-video-checkbox');

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
});

// 設定事件監聽器
function setupEventListeners() {
    // 上傳區點擊
    uploadArea.addEventListener('click', () => {
        fileInput.click();
    });
    
    // 檔案選擇
    fileInput.addEventListener('change', handleFileSelect);
    
    // 拖曳事件
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);
    
    // 上傳按鈕
    uploadBtn.addEventListener('click', uploadFile);
    
    // 編輯器控制
    if (editLanguageSelect) {
        editLanguageSelect.addEventListener('change', loadSubtitlesForEdit);
    }
    if (saveSubtitlesBtn) {
        saveSubtitlesBtn.addEventListener('click', saveSubtitles);
    }
    if (resetSubtitlesBtn) {
        resetSubtitlesBtn.addEventListener('click', resetSubtitles);
    }
    if (batchDownloadBtn) {
        batchDownloadBtn.addEventListener('click', batchDownload);
    }
    
    // 合併字幕
    const generateMergedBtn = document.getElementById('generate-merged-btn');
    if (generateMergedBtn) {
        generateMergedBtn.addEventListener('click', generateMergedSubtitle);
    }
    
    // 監聽合併字幕複選框變化
    document.addEventListener('change', (e) => {
        if (e.target.name === 'merge-language') {
            updateMergeButtonState();
        }
    });
    
    // 影片播放器事件
    if (videoPlayer) {
        videoPlayer.addEventListener('timeupdate', syncSubtitles);
        
        // 點擊影片暫停/播放
        videoPlayer.addEventListener('click', () => {
            if (videoPlayer.paused) {
                videoPlayer.play();
            } else {
                videoPlayer.pause();
            }
        });
    }
    
    // 鍵盤快捷鍵
    document.addEventListener('keydown', (e) => {
        // 空格鍵：暫停/播放
        if (e.code === 'Space' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA' && !e.target.isContentEditable) {
            e.preventDefault();
            if (videoPlayer && !videoPlayer.paused) {
                videoPlayer.pause();
            } else if (videoPlayer) {
                videoPlayer.play();
            }
        }
    });
    
    // 字幕模式切換
    const subtitleModeRadios = document.querySelectorAll('input[name="subtitle-mode"]');
    subtitleModeRadios.forEach(radio => {
        radio.addEventListener('change', handleSubtitleModeChange);
    });
    
    // 字幕選擇器
    const primarySubtitleSelect = document.getElementById('primary-subtitle-select');
    const primarySubtitleSelectDual = document.getElementById('primary-subtitle-select-dual');
    const secondarySubtitleSelect = document.getElementById('secondary-subtitle-select');
    
    if (primarySubtitleSelect) {
        primarySubtitleSelect.addEventListener('change', () => loadVideoSubtitle('single'));
    }
    if (primarySubtitleSelectDual) {
        primarySubtitleSelectDual.addEventListener('change', () => loadVideoSubtitle('dual'));
    }
    if (secondarySubtitleSelect) {
        secondarySubtitleSelect.addEventListener('change', () => loadVideoSubtitle('dual'));
    }
}

// 處理字幕模式切換
function handleSubtitleModeChange(e) {
    subtitleMode = e.target.value;
    
    const singleControls = document.getElementById('single-language-controls');
    const dualControls = document.getElementById('dual-language-controls');
    
    if (subtitleMode === 'single') {
        singleControls.style.display = 'block';
        dualControls.style.display = 'none';
        loadVideoSubtitle('single');
    } else {
        singleControls.style.display = 'none';
        dualControls.style.display = 'block';
        loadVideoSubtitle('dual');
    }
}

// 處理檔案選擇
function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        validateAndSetFile(file);
    }
}

// 處理拖曳
function handleDragOver(e) {
    e.preventDefault();
    uploadArea.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    
    const file = e.dataTransfer.files[0];
    if (file) {
        validateAndSetFile(file);
    }
}

// 驗證並設定檔案
function validateAndSetFile(file) {
    // 檢查檔案格式
    const validFormats = ['.mp4', '.avi', '.mov', '.mkv'];
    const fileExt = '.' + file.name.split('.').pop().toLowerCase();
    
    if (!validFormats.includes(fileExt)) {
        showError('檔案格式不支援', '請上傳 MP4, AVI, MOV 或 MKV 格式的影片');
        return;
    }
    
    // 檢查檔案大小（5GB）
    const maxSize = 5 * 1024 * 1024 * 1024;
    if (file.size > maxSize) {
        showError('檔案太大', '請上傳小於 5GB 的影片檔案');
        return;
    }
    
    selectedFile = file;
    uploadBtn.disabled = false;
    
    // 更新上傳區顯示
    const uploadText = uploadArea.querySelector('.upload-text');
    uploadText.textContent = `已選擇: ${file.name}`;
    
    hideError();
}

// 上傳檔案
async function uploadFile() {
    if (!selectedFile) return;
    
    // 取得選中的語言
    const checkboxes = document.querySelectorAll('input[name="target-language"]:checked');
    const targetLanguages = Array.from(checkboxes).map(cb => cb.value);
    
    // 驗證至少選擇一種語言
    if (targetLanguages.length === 0) {
        showError('請選擇語言', '請至少選擇一種翻譯語言');
        return;
    }
    
    uploadBtn.disabled = true;
    uploadBtn.textContent = '上傳中...';
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('target_languages', targetLanguages.join(','));
    
    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || '上傳失敗');
        }
        
        currentJobId = data.job_id;
        
        // 顯示進度區
        uploadSection.style.display = 'none';
        progressSection.style.display = 'block';
        
        // 開始輪詢狀態
        startPolling();
        
    } catch (error) {
        showError('上傳失敗', error.message);
        uploadBtn.disabled = false;
        uploadBtn.textContent = '開始上傳';
    }
}

// 開始輪詢任務狀態
function startPolling() {
    pollInterval = setInterval(checkStatus, 2000);
    checkStatus(); // 立即檢查一次
}

// 停止輪詢
function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

// 檢查任務狀態
async function checkStatus() {
    if (!currentJobId) return;
    
    try {
        const response = await fetch(`/status/${currentJobId}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || '查詢狀態失敗');
        }
        
        // 更新進度
        updateProgress(data.progress, data.stage);
        
        // 檢查是否完成
        if (data.status === 'completed') {
            stopPolling();
            showResults(data.subtitle_files);
        } else if (data.status === 'failed') {
            stopPolling();
            showError('處理失敗', data.error_message || '未知錯誤');
        }
        
    } catch (error) {
        stopPolling();
        showError('查詢狀態失敗', error.message);
    }
}

// 更新進度顯示
function updateProgress(progress, stage) {
    progressFill.style.width = `${progress}%`;
    progressText.textContent = `${progress}% - ${stage}`;
    stageText.textContent = stage;
}

// 顯示結果
function showResults(subtitleFiles) {
    progressSection.style.display = 'none';
    resultSection.style.display = 'block';
    
    // 設定影片播放器
    videoPlayer.src = `/video/${currentJobId}`;
    
    // 語言名稱映射
    const languages = {
        'en': 'English',
        'zh-TW': '繁體中文',
        'zh-CN': '簡體中文',
        'ms': 'Bahasa Melayu'
    };
    
    // 儲存可用語言
    availableLanguages = languages;
    
    // 生成下載卡片
    const downloadCards = document.getElementById('download-cards');
    downloadCards.innerHTML = '';
    
    if (subtitleFiles) {
        for (const lang of Object.keys(subtitleFiles)) {
            const name = languages[lang] || lang;
            
            const card = document.createElement('div');
            card.className = 'download-card';
            card.innerHTML = `
                <div class="download-card-title">${name}</div>
                <div class="download-card-controls">
                    <select class="format-select" data-lang="${lang}">
                        <option value="vtt">VTT 格式</option>
                        <option value="srt" selected>SRT 格式</option>
                    </select>
                </div>
                <button class="btn download-card-btn" data-lang="${lang}">
                    下載
                </button>
            `;
            
            // 添加下載事件
            const downloadBtn = card.querySelector('.download-card-btn');
            downloadBtn.addEventListener('click', () => {
                const formatSelect = card.querySelector('.format-select');
                const format = formatSelect.value;
                const url = format === 'srt' 
                    ? `/download/${currentJobId}/${lang}/srt`
                    : `/download/${currentJobId}/${lang}`;
                window.location.href = url;
            });
            
            downloadCards.appendChild(card);
        }
    }
    
    // 更新所有字幕選擇器
    const primarySubtitleSelect = document.getElementById('primary-subtitle-select');
    const primarySubtitleSelectDual = document.getElementById('primary-subtitle-select-dual');
    const secondarySubtitleSelect = document.getElementById('secondary-subtitle-select');
    
    // 清空並重新填充
    [primarySubtitleSelect, primarySubtitleSelectDual, secondarySubtitleSelect].forEach(select => {
        if (select) {
            select.innerHTML = '<option value="">無字幕</option>';
            if (subtitleFiles) {
                for (const lang of Object.keys(subtitleFiles)) {
                    const name = languages[lang] || lang;
                    const option = document.createElement('option');
                    option.value = lang;
                    option.textContent = name;
                    select.appendChild(option);
                }
            }
        }
    });
    
    // 更新編輯器語言選擇器
    editLanguageSelect.innerHTML = '';
    if (subtitleFiles) {
        for (const lang of Object.keys(subtitleFiles)) {
            const name = languages[lang] || lang;
            const option = document.createElement('option');
            option.value = lang;
            option.textContent = name;
            editLanguageSelect.appendChild(option);
        }
    }
    
    // 生成合併字幕複選框
    const mergeLanguageCheckboxes = document.getElementById('merge-language-checkboxes');
    mergeLanguageCheckboxes.innerHTML = '';
    if (subtitleFiles) {
        for (const lang of Object.keys(subtitleFiles)) {
            const name = languages[lang] || lang;
            const label = document.createElement('label');
            label.className = 'checkbox-label';
            label.innerHTML = `
                <input type="checkbox" name="merge-language" value="${lang}">
                <span>${name}</span>
            `;
            mergeLanguageCheckboxes.appendChild(label);
        }
    }
    
    // 載入第一個語言的字幕進行編輯
    if (Object.keys(subtitleFiles).length > 0) {
        currentLanguage = Object.keys(subtitleFiles)[0];
        editLanguageSelect.value = currentLanguage;
        loadSubtitlesForEdit();
    }
}

// 載入影片字幕（VTT track）
async function loadVideoSubtitle(mode) {
    const trackPrimary = document.getElementById('video-track-primary');
    const trackSecondary = document.getElementById('video-track-secondary');
    
    if (mode === 'single') {
        const primarySubtitleSelect = document.getElementById('primary-subtitle-select');
        const selectedLang = primarySubtitleSelect.value;
        
        // 清除副字幕
        trackSecondary.src = '';
        trackSecondary.mode = 'disabled';
        
        if (!selectedLang) {
            // 移除主字幕
            trackPrimary.src = '';
            trackPrimary.mode = 'disabled';
            videoPlayer.classList.remove('dual-subtitle');
            return;
        }
        
        // 設定主字幕
        const languages = {
            'en': 'English',
            'zh-TW': '繁體中文',
            'zh-CN': '簡體中文',
            'ms': 'Bahasa Melayu'
        };
        
        trackPrimary.src = `/download/${currentJobId}/${selectedLang}`;
        trackPrimary.srclang = selectedLang;
        trackPrimary.label = languages[selectedLang] || selectedLang;
        trackPrimary.mode = 'showing';
        videoPlayer.classList.remove('dual-subtitle');
        
    } else if (mode === 'dual') {
        const primarySubtitleSelectDual = document.getElementById('primary-subtitle-select-dual');
        const secondarySubtitleSelect = document.getElementById('secondary-subtitle-select');
        
        const primaryLang = primarySubtitleSelectDual.value;
        const secondaryLang = secondarySubtitleSelect.value;
        
        const languages = {
            'en': 'English',
            'zh-TW': '繁體中文',
            'zh-CN': '簡體中文',
            'ms': 'Bahasa Melayu'
        };
        
        // 設定主字幕
        if (primaryLang) {
            trackPrimary.src = `/download/${currentJobId}/${primaryLang}`;
            trackPrimary.srclang = primaryLang;
            trackPrimary.label = languages[primaryLang] || primaryLang;
            trackPrimary.mode = 'showing';
        } else {
            trackPrimary.src = '';
            trackPrimary.mode = 'disabled';
        }
        
        // 設定副字幕
        if (secondaryLang) {
            trackSecondary.src = `/download/${currentJobId}/${secondaryLang}`;
            trackSecondary.srclang = secondaryLang;
            trackSecondary.label = languages[secondaryLang] || secondaryLang;
            trackSecondary.mode = 'showing';
            videoPlayer.classList.add('dual-subtitle');
        } else {
            trackSecondary.src = '';
            trackSecondary.mode = 'disabled';
            videoPlayer.classList.remove('dual-subtitle');
        }
    }
    
    // 重新載入影片以應用字幕
    videoPlayer.load();
}

// 載入字幕進行編輯
async function loadSubtitlesForEdit() {
    if (!currentJobId) return;
    
    currentLanguage = editLanguageSelect.value;
    
    try {
        const response = await fetch(`/preview/${currentJobId}/${currentLanguage}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || '載入字幕失敗');
        }
        
        currentSubtitles = data.subtitles;
        originalSubtitles = JSON.parse(JSON.stringify(data.subtitles)); // 深拷貝
        
        renderSubtitleEditor();
        
    } catch (error) {
        showError('載入字幕失敗', error.message);
    }
}

// 渲染字幕編輯器
function renderSubtitleEditor() {
    subtitleEditorArea.innerHTML = '';
    
    currentSubtitles.forEach((subtitle, idx) => {
        const item = document.createElement('div');
        item.className = 'subtitle-edit-item';
        item.dataset.index = subtitle.index;
        item.dataset.startTime = subtitle.start_time;
        item.dataset.endTime = subtitle.end_time;
        
        item.innerHTML = `
            <div class="subtitle-time-edit" onclick="seekToTime(${parseTimeToSeconds(subtitle.start_time)})">
                ${subtitle.start_time} --> ${subtitle.end_time}
            </div>
            <div class="subtitle-text-edit" contenteditable="true" data-idx="${idx}">
                ${escapeHtml(subtitle.text)}
            </div>
        `;
        
        // 監聽編輯事件
        const textEdit = item.querySelector('.subtitle-text-edit');
        textEdit.addEventListener('input', () => {
            currentSubtitles[idx].text = textEdit.textContent;
        });
        
        textEdit.addEventListener('focus', () => {
            item.classList.add('editing');
        });
        
        textEdit.addEventListener('blur', () => {
            item.classList.remove('editing');
        });
        
        subtitleEditorArea.appendChild(item);
    });
}

// 同步字幕高亮（影片播放時）
function syncSubtitles() {
    if (!videoPlayer || !currentSubtitles.length) return;
    
    const currentTime = videoPlayer.currentTime;
    
    // 找到當前時間對應的字幕
    const items = subtitleEditorArea.querySelectorAll('.subtitle-edit-item');
    items.forEach(item => {
        const startTime = parseFloat(item.dataset.startTime.split(':').reduce((acc, time) => (60 * acc) + +time));
        const endTime = parseFloat(item.dataset.endTime.split(':').reduce((acc, time) => (60 * acc) + +time));
        
        if (currentTime >= startTime && currentTime <= endTime) {
            item.classList.add('active');
            // 自動滾動到當前字幕
            item.scrollIntoView({ behavior: 'smooth', block: 'center' });
        } else {
            item.classList.remove('active');
        }
    });
}

// 跳轉到指定時間
function seekToTime(seconds) {
    if (videoPlayer) {
        videoPlayer.currentTime = seconds;
        videoPlayer.play();
    }
}

// 解析時間字串為秒數
function parseTimeToSeconds(timeStr) {
    const parts = timeStr.split(':');
    const hours = parseInt(parts[0]);
    const minutes = parseInt(parts[1]);
    const seconds = parseFloat(parts[2]);
    return hours * 3600 + minutes * 60 + seconds;
}

// 儲存字幕
async function saveSubtitles() {
    if (!currentJobId || !currentLanguage) return;
    
    saveSubtitlesBtn.disabled = true;
    saveSubtitlesBtn.textContent = '儲存中...';
    
    try {
        // 準備字幕數據
        const subtitlesData = currentSubtitles.map(sub => ({
            index: sub.index,
            start_time: parseTimeToSeconds(sub.start_time),
            end_time: parseTimeToSeconds(sub.end_time),
            text: sub.text
        }));
        
        const response = await fetch(`/subtitle/${currentJobId}/${currentLanguage}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(subtitlesData)
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || '儲存失敗');
        }
        
        // 更新原始字幕
        originalSubtitles = JSON.parse(JSON.stringify(currentSubtitles));
        
        showSuccess('儲存成功', '字幕已更新');
        
    } catch (error) {
        showError('儲存失敗', error.message);
    } finally {
        saveSubtitlesBtn.disabled = false;
        saveSubtitlesBtn.textContent = '儲存修改';
    }
}

// 重置字幕
function resetSubtitles() {
    if (confirm('確定要重置所有修改嗎？')) {
        currentSubtitles = JSON.parse(JSON.stringify(originalSubtitles));
        renderSubtitleEditor();
        showSuccess('已重置', '字幕已恢復到上次儲存的狀態');
    }
}

// 批量下載
async function batchDownload() {
    if (!currentJobId) return;
    
    const includeVideo = includeVideoCheckbox.checked;
    const url = `/download-all/${currentJobId}?include_video=${includeVideo}`;
    
    // 直接下載
    window.location.href = url;
}

// 更新合併按鈕狀態
function updateMergeButtonState() {
    const checkboxes = document.querySelectorAll('input[name="merge-language"]:checked');
    const generateMergedBtn = document.getElementById('generate-merged-btn');
    
    if (checkboxes.length >= 2 && checkboxes.length <= 3) {
        generateMergedBtn.disabled = false;
    } else {
        generateMergedBtn.disabled = true;
    }
}

// 生成合併字幕
async function generateMergedSubtitle() {
    if (!currentJobId) return;
    
    const checkboxes = document.querySelectorAll('input[name="merge-language"]:checked');
    const selectedLanguages = Array.from(checkboxes).map(cb => cb.value);
    
    if (selectedLanguages.length < 2 || selectedLanguages.length > 3) {
        showError('選擇錯誤', '請選擇 2-3 種語言');
        return;
    }
    
    const generateMergedBtn = document.getElementById('generate-merged-btn');
    generateMergedBtn.disabled = true;
    generateMergedBtn.textContent = '生成中...';
    
    try {
        const response = await fetch(`/merge-subtitles/${currentJobId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                languages: selectedLanguages,
                format: 'srt'
            })
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || '生成失敗');
        }
        
        // 下載合併字幕
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `merged_${selectedLanguages.join('_')}.srt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showSuccess('生成成功', '合併字幕已下載');
        
    } catch (error) {
        showError('生成失敗', error.message);
    } finally {
        generateMergedBtn.disabled = false;
        generateMergedBtn.textContent = '生成合併字幕';
        updateMergeButtonState();
    }
}

// 顯示成功訊息
function showSuccess(title, message) {
    showNotification(`${title}: ${message}`, 'success');
}

// 顯示錯誤訊息
function showError(title, message) {
    showNotification(`${title}: ${message}`, 'error');
}

// 顯示通知
function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification ${type}`;
    notification.style.display = 'block';
    
    // 3 秒後自動隱藏
    setTimeout(() => {
        notification.style.display = 'none';
    }, 3000);
}

// 隱藏錯誤訊息（保留兼容性）
function hideError() {
    const notification = document.getElementById('notification');
    notification.style.display = 'none';
}

// HTML 轉義
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
