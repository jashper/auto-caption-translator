// 全域變數
let selectedFile = null;
let currentJobId = null;
let pollInterval = null;
let currentSubtitles = [];
let originalSubtitles = []; // 當前編輯語言的原始版本（第一次載入）
let initialSubtitlesCache = {}; // 所有語言的初始版本緩存 {lang: subtitles}
let currentLanguage = 'en';
let referenceLanguage = null;
let referenceSubtitles = [];
let isEditing = false;
let subtitleMode = 'single'; // 'single' or 'dual'
let availableLanguages = {};
let pipActive = false;
let videoObserver = null;

// 自定義字幕相關
let primarySubtitleData = [];
let secondarySubtitleData = [];
let subtitleUpdateInterval = null;

// Track Blob URLs（用於清理記憶體）
let trackBlobUrls = [];

// 追蹤模式
let trackPlaybackEnabled = false;

// 未儲存變更追蹤
let hasUnsavedChanges = false;

// 處理計時
let processingStartTime = null;

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

// 新增的 DOM 元素（結果區域的元素在需要時動態獲取）
const editLanguageSelect = document.getElementById('edit-language-select');
const subtitleEditorArea = document.getElementById('subtitle-editor-area');
const saveSubtitlesBtn = document.getElementById('save-subtitles-btn');
const resetSubtitlesBtn = document.getElementById('reset-subtitles-btn');
const batchDownloadBtn = document.getElementById('batch-download-btn');
const includeVideoCheckbox = document.getElementById('include-video-checkbox');

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initDropdowns();
    setupEventListeners();
    checkModelStatus();
});

// ===== Dark Mode =====
function initTheme() {
    const saved = localStorage.getItem('theme');
    if (saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.classList.add('dark');
    }
    updateThemeIcon();

    // Theme toggle button
    const toggle = document.getElementById('theme-toggle');
    if (toggle) {
        toggle.addEventListener('click', () => {
            document.documentElement.classList.add('transitioning');
            document.documentElement.classList.toggle('dark');
            const isDark = document.documentElement.classList.contains('dark');
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
            updateThemeIcon();
            setTimeout(() => document.documentElement.classList.remove('transitioning'), 300);
        });
    }

    // Listen for OS-level theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
            document.documentElement.classList.toggle('dark', e.matches);
            updateThemeIcon();
        }
    });
}

function updateThemeIcon() {
    const isDark = document.documentElement.classList.contains('dark');
    const lightIcon = document.getElementById('theme-icon-light');
    const darkIcon = document.getElementById('theme-icon-dark');
    if (lightIcon) lightIcon.style.display = isDark ? 'none' : 'block';
    if (darkIcon) darkIcon.style.display = isDark ? 'block' : 'none';
}

// ===== Dropdowns =====
function initDropdowns() {
    // Shortcuts dropdown toggle
    const shortcutsToggle = document.getElementById('shortcuts-toggle');
    const shortcutsDropdown = document.getElementById('shortcuts-dropdown');
    if (shortcutsToggle && shortcutsDropdown) {
        shortcutsToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            shortcutsDropdown.classList.toggle('open');
        });
    }

    // Close dropdowns on outside click
    document.addEventListener('click', (e) => {
        document.querySelectorAll('.dropdown.open').forEach(dd => {
            if (!dd.contains(e.target)) dd.classList.remove('open');
        });
    });

    // Close on Escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.dropdown.open').forEach(dd => dd.classList.remove('open'));
        }
    });
}

// 檢查模型狀態（頁面載入時自動執行）
let modelStatusInterval = null;

async function checkModelStatus() {
    try {
        const response = await fetch('/health');
        if (!response.ok) return;
        const data = await response.json();
        
        updateModelStatusBanner(data);
        
        // 如果模型未就緒，持續輪詢
        if (data.model_status !== 'ready' && data.model_status !== 'error') {
            if (!modelStatusInterval) {
                modelStatusInterval = setInterval(checkModelStatus, 2000);
            }
        } else {
            // 模型已就緒或出錯，停止輪詢
            if (modelStatusInterval) {
                clearInterval(modelStatusInterval);
                modelStatusInterval = null;
            }
            // 就緒時 3 秒後自動隱藏
            if (data.model_status === 'ready') {
                setTimeout(() => {
                    const banner = document.getElementById('model-status-banner');
                    if (banner) banner.style.display = 'none';
                }, 3000);
            }
        }
    } catch (e) {
        // 伺服器可能還沒啟動完，稍後重試
        if (!modelStatusInterval) {
            modelStatusInterval = setInterval(checkModelStatus, 3000);
        }
    }
}

function updateModelStatusBanner(data) {
    const banner = document.getElementById('model-status-banner');
    const icon = document.getElementById('model-status-icon');
    const text = document.getElementById('model-status-text');
    if (!banner || !icon || !text) return;
    
    // 清除舊的 class
    banner.className = 'model-status-banner';
    
    const modelName = data.model_size || '?';
    const sizeGb = data.model_size_gb || 0;
    const changedFrom = data.model_changed_from;
    
    let statusClass = '';
    let statusIcon = '';
    let statusText = '';
    
    switch (data.model_status) {
        case 'downloading':
            statusClass = 'status-downloading';
            statusIcon = '⬇️';
            // 使用後端提供的訊息（包含下載百分比和模型變更資訊）
            statusText = data.model_status_message || `正在下載 ${modelName} 模型（${sizeGb}GB）`;
            break;
        case 'loading':
            statusClass = 'status-loading';
            statusIcon = '⏳';
            // 使用後端提供的訊息（包含模型變更資訊）
            statusText = data.model_status_message || `正在載入 ${modelName} 模型（${sizeGb}GB）`;
            break;
        case 'ready':
            statusClass = 'status-ready';
            statusIcon = '✅';
            statusText = changedFrom 
                ? `已從 ${changedFrom} 切換為 ${modelName}，就緒`
                : `${modelName} 已就緒`;
            break;
        case 'error':
            statusClass = 'status-error';
            statusIcon = '❌';
            statusText = `模型載入失敗：${data.model_status_message || '未知錯誤'}`;
            break;
        case 'not_loaded':
            statusClass = 'status-loading';
            statusIcon = '⏳';
            statusText = `正在準備語音識別模型...`;
            break;
        default:
            return; // 未知狀態不顯示
    }
    
    banner.classList.add(statusClass);
    icon.textContent = statusIcon;
    text.textContent = statusText;
    banner.style.display = 'block';
    
    // 模型未就緒時禁用上傳按鈕
    if (uploadBtn) {
        if (data.model_status === 'ready') {
            // 模型就緒 — 按鈕狀態取決於是否已選檔案
            uploadBtn.disabled = !selectedFile;
        } else if (data.model_status === 'error') {
            uploadBtn.disabled = true;
        } else {
            uploadBtn.disabled = true;
        }
    }
}

// 設置播放速度（用於其他地方調用）
function setPlaybackSpeed(speed) {
    const videoPlayer = document.getElementById('video-player');
    if (!videoPlayer) {
        console.warn('找不到視頻元素');
        return;
    }
    
    videoPlayer.playbackRate = speed;
    
    // 更新下拉選單
    const speedSelect = document.getElementById('speed-select');
    if (speedSelect) {
        speedSelect.value = speed;
    }
    
    // 同步畫中畫視頻速度
    const pipVideo = document.getElementById('pip-video');
    if (pipVideo && pipActive) {
        pipVideo.playbackRate = speed;
    }
    
    console.log(`播放速度已設置為: ${speed}x`);
}

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
    
    // 影片語言選擇連動翻譯語言
    document.querySelectorAll('input[name="source-language"]').forEach(radio => {
        radio.addEventListener('change', handleSourceLanguageChange);
    });
    
    // 頁面載入時，根據預設主要語言隱藏對應翻譯選項
    handleSourceLanguageChange();
    
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
    
    // 參考語言選擇器
    const referenceLanguageSelect = document.getElementById('reference-language-select');
    if (referenceLanguageSelect) {
        referenceLanguageSelect.addEventListener('change', handleReferenceLanguageChange);
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
    
    // 鍵盤快捷鍵（使用動態獲取元素）
    document.addEventListener('keydown', (e) => {
        // 如果在輸入框或可編輯元素中，不觸發快捷鍵
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) {
            return;
        }
        
        // 如果畫中畫啟動，控制子畫面；否則控制主視頻
        const activeVideo = pipActive 
            ? document.getElementById('pip-video') 
            : document.getElementById('video-player');
        
        if (!activeVideo) {
            console.warn('找不到活動視頻元素，pipActive:', pipActive);
            return;
        }
        
        switch(e.code) {
            case 'Space':
                // 空格鍵：播放/暫停
                e.preventDefault();
                console.log('空格鍵按下，控制:', pipActive ? '子畫面' : '主視頻');
                if (activeVideo.paused) {
                    activeVideo.play();
                    console.log('播放');
                } else {
                    activeVideo.pause();
                    console.log('暫停');
                }
                break;
                
            case 'ArrowLeft':
                // 左箭頭：後退 5 秒
                e.preventDefault();
                activeVideo.currentTime = Math.max(0, activeVideo.currentTime - 5);
                break;
                
            case 'ArrowRight':
                // 右箭頭：前進 5 秒
                e.preventDefault();
                activeVideo.currentTime = Math.min(activeVideo.duration, activeVideo.currentTime + 5);
                break;
                
            case 'ArrowUp':
                // 上箭頭：音量增加
                e.preventDefault();
                activeVideo.volume = Math.min(1, activeVideo.volume + 0.1);
                break;
                
            case 'ArrowDown':
                // 下箭頭：音量減少
                e.preventDefault();
                activeVideo.volume = Math.max(0, activeVideo.volume - 0.1);
                break;
                
            case 'KeyF':
                // F 鍵：全屏切換
                e.preventDefault();
                toggleFullscreenContainer();
                break;
                
            case 'KeyT':
                // T 鍵：切換追蹤模式
                e.preventDefault();
                const trackBtn = document.getElementById('track-playback-btn');
                if (trackBtn) {
                    trackPlaybackEnabled = !trackPlaybackEnabled;
                    if (trackPlaybackEnabled) {
                        trackBtn.classList.add('active');
                    } else {
                        trackBtn.classList.remove('active');
                    }
                }
                break;
                
            case 'KeyS':
                // S 鍵：切換字幕顯示/隱藏
                e.preventDefault();
                toggleSubtitleVisibility();
                break;
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
    
    // 畫中畫控制
    const pipCloseBtn = document.getElementById('pip-close-btn');
    if (pipCloseBtn) {
        pipCloseBtn.addEventListener('click', closePiP);
    }
    
    // 設定滾動監聽（用於畫中畫）
    setupPiPObserver();
    
    // 監聽全屏狀態變化
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('mozfullscreenchange', handleFullscreenChange);
    document.addEventListener('MSFullscreenChange', handleFullscreenChange);
    
    // 追蹤模式切換按鈕
    const trackPlaybackBtn = document.getElementById('track-playback-btn');
    if (trackPlaybackBtn) {
        trackPlaybackBtn.addEventListener('click', () => {
            trackPlaybackEnabled = !trackPlaybackEnabled;
            
            // 切換按鈕狀態
            if (trackPlaybackEnabled) {
                trackPlaybackBtn.classList.add('active');
            } else {
                trackPlaybackBtn.classList.remove('active');
            }
        });
    }
    
    // 未儲存離開警告
    window.addEventListener('beforeunload', (e) => {
        if (hasUnsavedChanges) {
            e.preventDefault();
            e.returnValue = '';
        }
    });
}

// 處理字幕模式切換
function handleSubtitleModeChange(e) {
    subtitleMode = e.target.value;
    
    const singleControls = document.getElementById('single-language-controls');
    const dualControls = document.getElementById('dual-language-controls');
    const videoContainer = document.getElementById('video-container');
    const primarySubtitleSelect = document.getElementById('primary-subtitle-select');
    const videoPlayer = document.getElementById('video-player');
    
    if (subtitleMode === 'single') {
        // 單語模式
        singleControls.style.display = 'block';
        dualControls.style.display = 'none';
        videoContainer.classList.remove('subtitle-mode-dual');
        videoContainer.classList.add('subtitle-mode-single');
        
        // 同步 CC 按鈕的當前狀態到單語下拉選單
        if (videoPlayer && videoPlayer.textTracks && primarySubtitleSelect) {
            let activeTrack = null;
            for (let i = 0; i < videoPlayer.textTracks.length; i++) {
                const track = videoPlayer.textTracks[i];
                if (track.mode === 'showing') {
                    activeTrack = track;
                    break;
                }
            }
            
            // 如果 CC 按鈕有選擇語言，同步到下拉選單
            if (activeTrack) {
                primarySubtitleSelect.value = activeTrack.language;
                console.log(`切換到單語模式：同步 CC 狀態 ${activeTrack.language}`);
            } else {
                // CC 按鈕是關閉的，設為無字幕
                primarySubtitleSelect.value = '';
                console.log('切換到單語模式：CC 是關閉的');
            }
        }
        
        // 切換到單語模式
        loadVideoSubtitle('single');
    } else {
        // 雙語模式
        singleControls.style.display = 'none';
        dualControls.style.display = 'block';
        videoContainer.classList.remove('subtitle-mode-single');
        videoContainer.classList.add('subtitle-mode-dual');
        
        // 確保所有 tracks 都存在（雙語模式也需要 tracks 以便 fullscreen 時 CC 按鈕可用）
        if (Object.keys(availableLanguages).length > 0) {
            initializeAllTracks(Object.keys(availableLanguages), null);
        }
        
        // 切換到雙語模式
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
        showError('不支援的格式', '請上傳 MP4、AVI、MOV 或 MKV');
        return;
    }
    
    // 檢查檔案大小（5GB）
    const maxSize = 5 * 1024 * 1024 * 1024;
    if (file.size > maxSize) {
        showError('檔案過大', '請上傳小於 5GB 的影片');
        return;
    }
    
    selectedFile = file;
    // 只有模型已就緒時才啟用上傳按鈕
    const banner = document.getElementById('model-status-banner');
    const isModelReady = !banner || banner.style.display === 'none' || banner.classList.contains('status-ready');
    uploadBtn.disabled = !isModelReady;
    
    // 更新上傳區顯示
    const uploadText = uploadArea.querySelector('.upload-text');
    uploadText.textContent = file.name;
    
    hideError();
}

// 主要語言連動翻譯語言：隱藏與主要語言相同的翻譯選項
function handleSourceLanguageChange() {
    const primaryLang = document.querySelector('input[name="source-language"]:checked').value;

    document.querySelectorAll('input[name="target-language"]').forEach(cb => {
        const label = cb.closest('.checkbox-label');
        if (cb.value === primaryLang) {
            // 主要語言 = 此翻譯選項 → 隱藏並取消勾選
            cb.checked = false;
            label.style.display = 'none';
        } else {
            label.style.display = '';
        }
    });
}

// 格式化檔案大小
function formatFileSize(bytes) {
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// 上傳檔案
async function uploadFile() {
    if (!selectedFile) return;
    
    // 取得選中的語言
    const checkboxes = document.querySelectorAll('input[name="target-language"]:checked');
    const targetLanguages = Array.from(checkboxes).map(cb => cb.value);
    
    // 驗證至少選擇一種語言
    if (targetLanguages.length === 0) {
        showError('未選擇語言', '請至少選擇一種翻譯語言');
        return;
    }
    
    uploadBtn.disabled = true;
    
    // 取得選中的影片語言
    const sourceLanguage = document.querySelector('input[name="source-language"]:checked').value;
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('target_languages', targetLanguages.join(','));
    formData.append('source_language', sourceLanguage);
    
    // 立刻顯示進度區，讓使用者看到上傳進度
    uploadSection.style.display = 'none';
    progressSection.style.display = 'block';
    
    // 顯示正在處理的檔名
    const filenameEl = document.getElementById('progress-filename');
    if (filenameEl) {
        filenameEl.textContent = selectedFile.name;
    }
    
    updateProgress(0, '正在上傳…', null);
    
    const xhr = new XMLHttpRequest();
    xhr.timeout = 300000; // 5 分鐘超時（大檔案需要更多時間）
    
    // 上傳進度追蹤（上傳佔總進度 0-15%，處理佔 15-100%）
    xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
            const percent = Math.round((e.loaded / e.total) * 14);
            const loaded = formatFileSize(e.loaded);
            const total = formatFileSize(e.total);
            updateProgress(percent, `上傳中 ${loaded} / ${total}`, null, false, true);
        }
    };
    
    // 上傳完成，等待伺服器回應
    xhr.upload.onload = () => {
        updateProgress(15, '上傳完成，準備開始處理…', null, false, true);
    };
    
    // 收到伺服器回應
    xhr.onload = () => {
        try {
            const data = JSON.parse(xhr.responseText);
            
            if (xhr.status >= 200 && xhr.status < 300) {
                currentJobId = data.job_id;
                updateProgress(15, '已收到，正在排入處理佇列…', null, true);
                startPolling();
            } else {
                showError('上傳失敗', data.error || '伺服器錯誤');
                uploadSection.style.display = 'block';
                progressSection.style.display = 'none';
                uploadBtn.disabled = false;
            }
        } catch (e) {
            showError('上傳失敗', '伺服器回應格式錯誤');
            uploadSection.style.display = 'block';
            progressSection.style.display = 'none';
            uploadBtn.disabled = false;
        }
    };
    
    // 錯誤處理
    xhr.onerror = () => {
        showError('上傳失敗', '網路連線錯誤');
        uploadSection.style.display = 'block';
        progressSection.style.display = 'none';
        uploadBtn.disabled = false;
    };
    
    // 超時處理
    xhr.ontimeout = () => {
        showError('上傳逾時', '請嘗試較小的檔案');
        uploadSection.style.display = 'block';
        progressSection.style.display = 'none';
        uploadBtn.disabled = false;
    };
    
    xhr.open('POST', '/upload');
    xhr.send(formData);
}

// 開始輪詢任務狀態
function startPolling() {
    processingStartTime = Date.now();
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
        if (data.status === 'queued') {
            updateProgress(15, '排隊等待中，稍後自動開始處理…', null, true);
        } else {
            // 後端 0-100% 映射到統一進度 15-100%（上傳佔 0-15%）
            const mappedProgress = 15 + Math.round(data.progress * 0.85);
            updateProgress(mappedProgress, data.stage, data.estimated_seconds);
        }
        
        // 語言不符警告
        if (data.language_mismatch) {
            const mismatchWarning = document.getElementById('language-mismatch-warning');
            const mismatchText = document.getElementById('mismatch-warning-text');
            if (mismatchWarning && mismatchText) {
                const langNames = {
                    'en': 'English', 'zh': '中文', 'zh-TW': '繁體中文', 
                    'zh-CN': '簡體中文', 'ms': 'Bahasa Melayu'
                };
                const primaryName = langNames[data.primary_language] || data.primary_language;
                const detectedName = langNames[data.detected_language] || data.detected_language;
                mismatchText.textContent = `您選擇的語言是「${primaryName}」，但偵測到「${detectedName}」。可能影響翻譯品質。`;
                mismatchWarning.style.display = 'block';
            }
        }
        
        // 檢查是否完成
        if (data.status === 'completed') {
            stopPolling();
            showResults(data.subtitle_files, data.detected_language, data.primary_language);
        } else if (data.status === 'failed') {
            stopPolling();
            showError('處理失敗', data.error_message || '未知錯誤');
        }
        
    } catch (error) {
        stopPolling();
        showError('查詢狀態失敗', error.message);
    }
}

function updateProgress(progress, stage, estimatedSeconds, indeterminate = false, hidePercent = false) {
    if (indeterminate) {
        progressFill.classList.add('indeterminate');
        progressFill.style.width = '';
        progressText.textContent = '';
        progressText.classList.add('hidden');
    } else {
        progressFill.classList.remove('indeterminate');
        progressFill.style.width = `${progress}%`;
        if (hidePercent) {
            progressText.textContent = '';
            progressText.classList.add('hidden');
        } else {
            progressText.textContent = `${progress}%`;
            progressText.classList.remove('hidden');
        }
    }
    stageText.textContent = stage;

    // 顯示預估剩餘時間（處理階段：統一進度 15-100%）
    const estimateEl = document.getElementById('estimate-text');
    if (estimateEl) {
        if (processingStartTime && progress >= 25 && progress < 100) {
            const elapsed = (Date.now() - processingStartTime) / 1000;
            // 處理進度比例：(progress - 15) / 85 = 0.0 ~ 1.0
            const processingRatio = (progress - 15) / 85;
            const totalEstimate = elapsed / processingRatio;
            const remaining = Math.max(0, Math.round(totalEstimate - elapsed));
            const mins = Math.floor(remaining / 60);
            const secs = remaining % 60;
            estimateEl.textContent = mins > 0
                ? `剩餘約 ${mins} 分 ${secs} 秒`
                : `剩餘約 ${secs} 秒`;
        } else if (processingStartTime && progress > 15 && progress < 25) {
            estimateEl.textContent = '正在估算…';
        } else {
            estimateEl.textContent = '';
        }
    }
}

// 顯示結果
function showResults(subtitleFiles, detectedLanguage, primaryLanguage) {
    progressSection.style.display = 'none';
    resultSection.style.display = 'block';
    
    // 設定影片播放器（動態獲取元素）
    const videoPlayer = document.getElementById('video-player');
    if (videoPlayer) {
        videoPlayer.src = `/video/${currentJobId}`;
    }
    
    // 語言名稱映射
    const languages = {
        'en': 'English',
        'zh': '中文',
        'zh-TW': '繁體中文',
        'zh-CN': '簡體中文',
        'ms': 'Bahasa Melayu'
    };
    
    // 顯示檢測到的語言
    if (detectedLanguage) {
        const detectedLangName = languages[detectedLanguage] || detectedLanguage;
        const languageInfo = document.getElementById('language-info');
        if (languageInfo) {
            let html = '';
            
            // 如果偵測語言與主要語言不同，顯示提醒
            if (primaryLanguage && detectedLanguage !== primaryLanguage) {
                html = `<span style="color: var(--warning-text);">⚠ 偵測語言為 ${detectedLangName}，與選擇的「${languages[primaryLanguage] || primaryLanguage}」不同</span>`;
            } else {
                html = `偵測語言：${detectedLangName}`;
            }
            
            languageInfo.innerHTML = html;
            languageInfo.style.display = 'block';
            // 5 秒後自動隱藏
            setTimeout(() => {
                if (languageInfo) languageInfo.style.display = 'none';
            }, 5000);
        }
    }
    
    // 儲存實際可用的語言（只包含用戶選擇的語言）
    availableLanguages = {};
    if (subtitleFiles) {
        for (const lang of Object.keys(subtitleFiles)) {
            availableLanguages[lang] = languages[lang] || lang;
        }
    }
    
    // 生成下載列表（緊湊式）
    const downloadList = document.getElementById('download-list');
    downloadList.innerHTML = '';
    
    if (subtitleFiles) {
        for (const lang of Object.keys(subtitleFiles)) {
            const name = availableLanguages[lang] || lang;
            
            const row = document.createElement('div');
            row.className = 'download-row';
            row.innerHTML = `
                <div class="download-row-title">${name}</div>
                <div class="download-row-actions">
                    <select class="format-select-compact" data-lang="${lang}">
                        <option value="vtt">VTT</option>
                        <option value="srt" selected>SRT</option>
                        <option value="ass">ASS</option>
                    </select>
                    <button class="btn btn-secondary btn-compact" data-lang="${lang}">
                        下載
                    </button>
                </div>
            `;
            
            // 添加下載事件
            const downloadBtn = row.querySelector('.btn-compact');
            downloadBtn.addEventListener('click', () => {
                const formatSelect = row.querySelector('.format-select-compact');
                const format = formatSelect.value;
                let url;
                if (format === 'vtt') {
                    url = `/download/${currentJobId}/${lang}`;
                } else {
                    url = `/download/${currentJobId}/${lang}/${format}`;
                }
                window.location.href = url;
            });
            
            downloadList.appendChild(row);
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
    const referenceLanguageSelect = document.getElementById('reference-language-select');
    if (referenceLanguageSelect) {
        referenceLanguageSelect.innerHTML = '<option value="">無參考語言</option>';
    }
    
    if (subtitleFiles) {
        for (const lang of Object.keys(subtitleFiles)) {
            const name = availableLanguages[lang] || lang;
            
            // 編輯語言選擇器
            const option = document.createElement('option');
            option.value = lang;
            option.textContent = name;
            editLanguageSelect.appendChild(option);
            
            // 參考語言選擇器（只添加實際可用的語言）
            if (referenceLanguageSelect) {
                const refOption = document.createElement('option');
                refOption.value = lang;
                refOption.textContent = name;
                referenceLanguageSelect.appendChild(refOption);
            }
        }
    }
    
    // 確保字幕模式默認為 single
    subtitleMode = 'single';
    const singleModeRadio = document.querySelector('input[name="subtitle-mode"][value="single"]');
    if (singleModeRadio) {
        singleModeRadio.checked = true;
    }
    const singleControls = document.getElementById('single-language-controls');
    const dualControls = document.getElementById('dual-language-controls');
    if (singleControls) singleControls.style.display = 'block';
    if (dualControls) dualControls.style.display = 'none';
    
    // 設置容器為單語模式
    const videoContainer = document.getElementById('video-container');
    if (videoContainer) {
        videoContainer.classList.remove('subtitle-mode-dual');
        videoContainer.classList.add('subtitle-mode-single');
    }
    
    // 初始化單語模式：添加所有語言的 track（讓 CC 按鈕可以切換）
    if (subtitleFiles && Object.keys(subtitleFiles).length > 0) {
        initializeAllTracks(Object.keys(subtitleFiles));
    }
    
    // 生成合併字幕複選框（卡片式）
    const mergeLanguageCards = document.getElementById('merge-language-cards');
    mergeLanguageCards.innerHTML = '';
    if (subtitleFiles) {
        for (const lang of Object.keys(subtitleFiles)) {
            const name = languages[lang] || lang;
            const label = document.createElement('label');
            label.className = 'language-card';
            label.innerHTML = `
                <input type="checkbox" name="merge-language" value="${lang}">
                <span class="card-content">
                    <span class="card-title">${name}</span>
                </span>
            `;
            mergeLanguageCards.appendChild(label);
        }
    }
    
    // 載入第一個語言的字幕進行編輯
    if (Object.keys(subtitleFiles).length > 0) {
        currentLanguage = Object.keys(subtitleFiles)[0];
        editLanguageSelect.value = currentLanguage;
        loadSubtitlesForEdit();
    }
    
    // 綁定播放速度控制事件（必須在結果區顯示後綁定）
    const speedSelect = document.getElementById('speed-select');
    // 重新獲取 videoPlayer（因為之前的作用域已結束）
    const videoPlayerElement = document.getElementById('video-player');
    
    if (speedSelect && videoPlayerElement) {
        // 強制重置速度選單為 1×（防止瀏覽器記住之前的選擇）
        speedSelect.value = '1';
        
        // 綁定視頻事件
        videoPlayerElement.addEventListener('timeupdate', syncSubtitles);
        
        // 點擊影片暫停/播放
        videoPlayerElement.addEventListener('click', () => {
            if (videoPlayerElement.paused) {
                videoPlayerElement.play();
            } else {
                videoPlayerElement.pause();
            }
        });
        
        // 修復長視頻加載問題
        videoPlayerElement.addEventListener('loadedmetadata', () => {
            console.log('視頻元數據已加載');
        });
        
        videoPlayerElement.addEventListener('error', (e) => {
            console.error('視頻加載錯誤:', e);
            if (videoPlayerElement.error) {
                console.error('錯誤代碼:', videoPlayerElement.error.code);
                console.error('錯誤訊息:', videoPlayerElement.error.message);
            }
            // 嘗試重新加載
            if (videoPlayerElement.error && videoPlayerElement.error.code === 3) {
                console.log('嘗試重新加載視頻...');
                const currentTime = videoPlayerElement.currentTime;
                videoPlayerElement.load();
                videoPlayerElement.currentTime = currentTime;
            }
        });
        
        // 處理 seeking 事件（拖動進度條）
        videoPlayerElement.addEventListener('seeking', () => {
            console.log('正在跳轉到:', videoPlayerElement.currentTime);
        });
        
        videoPlayerElement.addEventListener('seeked', () => {
            console.log('跳轉完成:', videoPlayerElement.currentTime);
        });
        
        // 移除舊的事件監聽器（如果有）
        const newSpeedSelect = speedSelect.cloneNode(true);
        speedSelect.parentNode.replaceChild(newSpeedSelect, speedSelect);
        
        // 綁定速度控制事件
        newSpeedSelect.addEventListener('change', (e) => {
            const speed = parseFloat(e.target.value);
            console.log('選擇速度:', speed);
            videoPlayerElement.playbackRate = speed;
            console.log('主視頻播放速度已設置為:', videoPlayerElement.playbackRate);
            
            // 同步畫中畫視頻速度
            const pipVideo = document.getElementById('pip-video');
            if (pipVideo && pipActive) {
                pipVideo.playbackRate = speed;
                console.log('畫中畫視頻速度已同步為:', pipVideo.playbackRate);
            }
        });
        
        // 重置播放速度為 1×
        videoPlayerElement.playbackRate = 1;
        newSpeedSelect.value = '1';
        console.log('✓ 播放速度已重置為 1×，事件已綁定');
    } else {
        console.error('❌ 錯誤：找不到速度選單或視頻元素');
        console.log('speedSelect:', speedSelect);
        console.log('videoPlayerElement:', videoPlayerElement);
    }
}

// 載入影片字幕（方案 C：自動判斷模式）
async function loadVideoSubtitle(mode) {
    const videoContainer = document.getElementById('video-container');
    const videoPlayer = document.getElementById('video-player');
    
    if (!videoPlayer) {
        console.error('找不到視頻元素');
        return;
    }
    
    // 停止之前的字幕更新
    if (subtitleUpdateInterval) {
        clearInterval(subtitleUpdateInterval);
        subtitleUpdateInterval = null;
    }
    
    // 清空字幕數據
    primarySubtitleData = [];
    secondarySubtitleData = [];
    
    if (mode === 'single') {
        // === 單語模式：使用原生 track ===
        const primarySubtitleSelect = document.getElementById('primary-subtitle-select');
        const selectedLang = primarySubtitleSelect.value;
        
        videoContainer.classList.remove('subtitle-mode-dual');
        videoContainer.classList.add('subtitle-mode-single');
        
        // 清除自定義字幕
        clearCustomSubtitles();
        
        // 更新所有 textTracks 的顯示狀態（頁面 → CC）
        if (videoPlayer.textTracks) {
            for (let i = 0; i < videoPlayer.textTracks.length; i++) {
                const track = videoPlayer.textTracks[i];
                if (selectedLang && track.language === selectedLang) {
                    track.mode = 'showing';
                    console.log(`頁面 → CC: 顯示 ${selectedLang}`);
                } else {
                    track.mode = 'hidden';
                }
            }
        }
        
    } else if (mode === 'dual') {
        // === 雙語模式：使用自定義渲染 ===
        const primarySubtitleSelectDual = document.getElementById('primary-subtitle-select-dual');
        const secondarySubtitleSelect = document.getElementById('secondary-subtitle-select');
        
        const primaryLang = primarySubtitleSelectDual.value;
        const secondaryLang = secondarySubtitleSelect.value;
        
        videoContainer.classList.remove('subtitle-mode-single');
        videoContainer.classList.add('subtitle-mode-dual');
        
        // 禁用所有 textTracks（確保原生字幕完全關閉）
        if (videoPlayer.textTracks) {
            for (let i = 0; i < videoPlayer.textTracks.length; i++) {
                videoPlayer.textTracks[i].mode = 'hidden';
            }
        }
        
        console.log('雙語模式：已隱藏所有 textTracks');
        
        if (!primaryLang && !secondaryLang) {
            clearCustomSubtitles();
            return;
        }
        
        // 載入主字幕數據
        if (primaryLang) {
            await loadSubtitleData(primaryLang, 'primary');
        } else {
            primarySubtitleData = [];
        }
        
        // 載入副字幕數據
        if (secondaryLang) {
            await loadSubtitleData(secondaryLang, 'secondary');
        } else {
            secondarySubtitleData = [];
            const secondaryText = document.getElementById('secondary-subtitle-text');
            if (secondaryText) {
                secondaryText.textContent = '';
                secondaryText.classList.remove('show');
            }
        }
        
        // 啟動自定義字幕更新循環
        startSubtitleUpdate();
    }
}

// 載入字幕數據
async function loadSubtitleData(language, type) {
    try {
        const response = await fetch(`/preview/${currentJobId}/${language}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || '載入字幕失敗');
        }
        
        // 轉換為時間戳格式
        const subtitleData = data.subtitles.map(sub => ({
            start: parseTimeToSeconds(sub.start_time),
            end: parseTimeToSeconds(sub.end_time),
            text: sub.text
        }));
        
        if (type === 'primary') {
            primarySubtitleData = subtitleData;
        } else {
            secondarySubtitleData = subtitleData;
        }
        
    } catch (error) {
        console.error(`載入 ${language} 字幕失敗:`, error);
    }
}

// 啟動字幕更新
function startSubtitleUpdate() {
    if (subtitleUpdateInterval) {
        clearInterval(subtitleUpdateInterval);
    }
    
    // 每 100ms 更新一次字幕顯示
    subtitleUpdateInterval = setInterval(updateCustomSubtitles, 100);
}

// 更新自定義字幕顯示（僅雙語模式）
function updateCustomSubtitles() {
    const videoPlayer = document.getElementById('video-player');
    if (!videoPlayer) return;
    
    const currentTime = videoPlayer.currentTime;
    const primaryText = document.getElementById('primary-subtitle-text');
    const secondaryText = document.getElementById('secondary-subtitle-text');
    
    // 檢查當前模式
    const currentMode = document.querySelector('input[name="subtitle-mode"]:checked')?.value || 'single';
    
    // 單語模式下不更新自定義字幕（使用原生 track）
    if (currentMode === 'single') {
        if (primaryText) {
            primaryText.textContent = '';
            primaryText.classList.remove('show');
        }
        if (secondaryText) {
            secondaryText.textContent = '';
            secondaryText.classList.remove('show');
        }
        return;
    }
    
    // === 雙語模式：更新自定義字幕 ===
    
    // 更新主字幕
    const primarySub = findCurrentSubtitle(primarySubtitleData, currentTime);
    if (primarySub && primaryText) {
        primaryText.textContent = primarySub.text;
        primaryText.classList.add('show');
    } else if (primaryText) {
        primaryText.textContent = '';
        primaryText.classList.remove('show');
    }
    
    // 更新副字幕（只有在有數據時）
    if (secondarySubtitleData && secondarySubtitleData.length > 0) {
        const secondarySub = findCurrentSubtitle(secondarySubtitleData, currentTime);
        if (secondarySub && secondaryText) {
            secondaryText.textContent = secondarySub.text;
            secondaryText.classList.add('show');
        } else if (secondaryText) {
            secondaryText.textContent = '';
            secondaryText.classList.remove('show');
        }
    } else if (secondaryText) {
        // 沒有副字幕數據時，確保完全隱藏
        secondaryText.textContent = '';
        secondaryText.classList.remove('show');
    }
}

// 查找當前時間對應的字幕
function findCurrentSubtitle(subtitleData, currentTime) {
    return subtitleData.find(sub => currentTime >= sub.start && currentTime <= sub.end);
}

// 清除自定義字幕
function clearCustomSubtitles() {
    const primaryText = document.getElementById('primary-subtitle-text');
    const secondaryText = document.getElementById('secondary-subtitle-text');
    
    if (primaryText) {
        primaryText.textContent = '';
        primaryText.classList.remove('show');
    }
    if (secondaryText) {
        secondaryText.textContent = '';
        secondaryText.classList.remove('show');
    }
    
    if (subtitleUpdateInterval) {
        clearInterval(subtitleUpdateInterval);
        subtitleUpdateInterval = null;
    }
}

// 載入字幕進行編輯
async function loadSubtitlesForEdit() {
    if (!currentJobId) return;
    
    const editLanguageSelect = document.getElementById('edit-language-select');
    const newLanguage = editLanguageSelect.value;
    
    // 切換語言時警告未儲存的變更
    if (hasUnsavedChanges && newLanguage !== currentLanguage) {
        if (!confirm('目前有未儲存的修改，切換語言將會遺失。確定要繼續嗎？')) {
            editLanguageSelect.value = currentLanguage;
            return;
        }
    }
    
    currentLanguage = newLanguage;
    
    try {
        const response = await fetch(`/preview/${currentJobId}/${currentLanguage}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || '載入字幕失敗');
        }
        
        currentSubtitles = data.subtitles;
        
        // 如果這個語言還沒有緩存初始版本，保存它
        if (!initialSubtitlesCache[currentLanguage]) {
            initialSubtitlesCache[currentLanguage] = JSON.parse(JSON.stringify(data.subtitles));
            console.log(`已緩存 ${currentLanguage} 的初始版本`);
        }
        
        // originalSubtitles 始終指向初始版本
        originalSubtitles = JSON.parse(JSON.stringify(initialSubtitlesCache[currentLanguage]));
        
        // 更新參考語言選擇器（排除當前編輯語言）
        updateReferenceLanguageOptions();
        
        // 如果有參考語言，重新載入
        if (referenceLanguage && referenceLanguage !== currentLanguage) {
            await loadReferenceSubtitles();
        } else {
            referenceLanguage = null;
            referenceSubtitles = [];
            renderSubtitleEditor();
        }
        
        // 載入後重置髒狀態
        hasUnsavedChanges = false;
        updateSaveButtonState();
        
    } catch (error) {
        showError('載入字幕失敗', error.message);
    }
}

// 更新參考語言選擇器選項
function updateReferenceLanguageOptions() {
    const referenceLanguageSelect = document.getElementById('reference-language-select');
    if (!referenceLanguageSelect) return;
    
    const currentValue = referenceLanguageSelect.value;
    referenceLanguageSelect.innerHTML = '<option value="">無參考語言</option>';
    
    // 添加所有語言，但排除當前編輯語言
    Object.keys(availableLanguages).forEach(lang => {
        if (lang !== currentLanguage) {
            const option = document.createElement('option');
            option.value = lang;
            option.textContent = availableLanguages[lang];
            referenceLanguageSelect.appendChild(option);
        }
    });
    
    // 如果之前選擇的參考語言還可用，保持選中
    if (currentValue && currentValue !== currentLanguage) {
        referenceLanguageSelect.value = currentValue;
    } else {
        referenceLanguageSelect.value = '';
    }
}

// 處理參考語言變更
async function handleReferenceLanguageChange() {
    const referenceLanguageSelect = document.getElementById('reference-language-select');
    if (!referenceLanguageSelect) return;
    
    referenceLanguage = referenceLanguageSelect.value || null;
    
    if (referenceLanguage) {
        await loadReferenceSubtitles();
    } else {
        referenceSubtitles = [];
        renderSubtitleEditor();
    }
}

// 載入參考字幕
async function loadReferenceSubtitles() {
    if (!currentJobId || !referenceLanguage) {
        renderSubtitleEditor();
        return;
    }
    
    try {
        const response = await fetch(`/preview/${currentJobId}/${referenceLanguage}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || '載入參考字幕失敗');
        }
        
        referenceSubtitles = data.subtitles;
        renderSubtitleEditor();
        
    } catch (error) {
        console.error('載入參考字幕失敗:', error);
        referenceSubtitles = [];
        renderSubtitleEditor();
    }
}

// 渲染字幕編輯器
function renderSubtitleEditor() {
    const subtitleEditorArea = document.getElementById('subtitle-editor-area');
    subtitleEditorArea.innerHTML = '';
    
    currentSubtitles.forEach((subtitle, idx) => {
        const item = document.createElement('div');
        item.className = 'subtitle-edit-item';
        item.dataset.index = subtitle.index;
        item.dataset.startTime = subtitle.start_time;
        item.dataset.endTime = subtitle.end_time;
        
        // 如果有參考語言，顯示在下方（只讀）
        let referenceHtml = '';
        if (referenceLanguage && referenceSubtitles[idx]) {
            const refText = referenceSubtitles[idx].text;
            referenceHtml = `
                <div class="subtitle-reference">
                    ${escapeHtml(refText)}
                </div>
            `;
            item.classList.add('with-reference');
        }
        
        // 檢查是否與初始版本不同（用於單行還原）
        const initialText = initialSubtitlesCache[currentLanguage]?.[idx]?.text || '';
        const isModified = subtitle.text !== initialText;
        
        item.innerHTML = `
            <div class="subtitle-item-header">
                <div class="subtitle-time-edit" onclick="seekToTime(${parseTimeToSeconds(subtitle.start_time)})">
                    ${subtitle.start_time} --> ${subtitle.end_time}
                </div>
                <button class="subtitle-undo-btn ${isModified ? 'visible' : ''}" title="還原此行">↩</button>
            </div>
            <div class="subtitle-text-edit" contenteditable="true" data-idx="${idx}">
                ${escapeHtml(subtitle.text)}
            </div>
            ${referenceHtml}
        `;
        
        // 監聽編輯事件
        const textEdit = item.querySelector('.subtitle-text-edit');
        const undoBtn = item.querySelector('.subtitle-undo-btn');
        
        textEdit.addEventListener('input', () => {
            currentSubtitles[idx].text = textEdit.textContent.trim();
            // 更新單行還原按鈕
            const initText = initialSubtitlesCache[currentLanguage]?.[idx]?.text || '';
            if (currentSubtitles[idx].text !== initText) {
                undoBtn.classList.add('visible');
            } else {
                undoBtn.classList.remove('visible');
            }
            checkUnsavedChanges();
        });
        
        textEdit.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const nextItem = item.nextElementSibling;
                if (nextItem) {
                    const nextEdit = nextItem.querySelector('.subtitle-text-edit');
                    if (nextEdit) nextEdit.focus();
                }
            }
        });
        
        textEdit.addEventListener('focus', () => {
            item.classList.add('editing');
        });
        
        textEdit.addEventListener('blur', () => {
            item.classList.remove('editing');
        });
        
        // 單行還原
        undoBtn.addEventListener('click', () => {
            const initText = initialSubtitlesCache[currentLanguage]?.[idx]?.text || '';
            currentSubtitles[idx].text = initText;
            textEdit.textContent = initText;
            undoBtn.classList.remove('visible');
            checkUnsavedChanges();
        });
        
        subtitleEditorArea.appendChild(item);
    });
}

// 檢查是否有未儲存的變更
function checkUnsavedChanges() {
    if (!initialSubtitlesCache[currentLanguage]) {
        hasUnsavedChanges = false;
    } else {
        const initial = initialSubtitlesCache[currentLanguage];
        hasUnsavedChanges = currentSubtitles.some((sub, idx) => 
            sub.text !== (initial[idx]?.text || '')
        );
    }
    updateSaveButtonState();
}

// 更新儲存按鈕狀態
function updateSaveButtonState() {
    const saveBtn = document.getElementById('save-subtitles-btn');
    if (!saveBtn) return;
    if (hasUnsavedChanges) {
        saveBtn.innerHTML = '<span class="save-indicator">●</span> 儲存';
        saveBtn.classList.add('has-changes');
    } else {
        saveBtn.innerHTML = '儲存';
        saveBtn.classList.remove('has-changes');
    }
}

// 同步字幕高亮（影片播放時）
function syncSubtitles() {
    const videoPlayer = document.getElementById('video-player');
    if (!videoPlayer || !currentSubtitles.length) return;
    
    const currentTime = videoPlayer.currentTime;
    
    // 找到當前時間對應的字幕
    const items = subtitleEditorArea.querySelectorAll('.subtitle-edit-item');
    let activeItem = null;
    
    items.forEach(item => {
        const startTime = parseFloat(item.dataset.startTime.split(':').reduce((acc, time) => (60 * acc) + +time));
        const endTime = parseFloat(item.dataset.endTime.split(':').reduce((acc, time) => (60 * acc) + +time));
        
        if (currentTime >= startTime && currentTime <= endTime) {
            item.classList.add('active');
            activeItem = item;
        } else {
            item.classList.remove('active');
        }
    });
    
    // 只有在追蹤模式開啟時才自動滾動
    if (trackPlaybackEnabled && activeItem) {
        activeItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

// 跳轉到指定時間（不觸發滾動）
function seekToTime(seconds) {
    // 根據畫中畫狀態選擇控制對象
    const activeVideo = pipActive 
        ? document.getElementById('pip-video') 
        : document.getElementById('video-player');
    
    if (activeVideo) {
        // 暫時禁用追蹤模式避免跳轉時滾動
        const wasTracking = trackPlaybackEnabled;
        trackPlaybackEnabled = false;
        
        activeVideo.currentTime = seconds;
        activeVideo.play();
        
        console.log(`跳轉到 ${seconds.toFixed(2)} 秒，控制: ${pipActive ? '子畫面' : '主視頻'}`);
        
        // 如果是畫中畫模式，也需要同步主視頻的時間（保持同步）
        if (pipActive) {
            const videoPlayer = document.getElementById('video-player');
            if (videoPlayer) {
                videoPlayer.currentTime = seconds;
            }
        }
        
        // 100ms 後恢復追蹤模式設置
        setTimeout(() => {
            trackPlaybackEnabled = wasTracking;
        }, 100);
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
        // 準備字幕數據（trim 所有文字）
        const subtitlesData = currentSubtitles.map(sub => ({
            index: sub.index,
            start_time: parseTimeToSeconds(sub.start_time),
            end_time: parseTimeToSeconds(sub.end_time),
            text: sub.text.trim() // 確保儲存時也 trim
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
        
        // 更新原始字幕（不再更新，保持初始版本）
        // originalSubtitles 保持不變，指向 initialSubtitlesCache
        
        showSuccess('儲存成功', '字幕已更新');
        
        // 強制重新載入所有 tracks（避免緩存問題）
        const currentMode = document.querySelector('input[name="subtitle-mode"]:checked')?.value || 'single';
        if (currentMode === 'single') {
            // 單語模式：重新初始化所有 tracks
            const primarySubtitleSelect = document.getElementById('primary-subtitle-select');
            const selectedLang = primarySubtitleSelect?.value;
            initializeAllTracks(Object.keys(availableLanguages), selectedLang);
        } else {
            // 雙語模式：重新載入字幕數據
            await reloadCurrentSubtitle();
        }
        
    } catch (error) {
        showError('儲存失敗', error.message);
    } finally {
        saveSubtitlesBtn.disabled = false;
        hasUnsavedChanges = false;
        updateSaveButtonState();
    }
}

// 重置字幕
function resetSubtitles() {
    if (confirm('確定要重置到最初版本嗎？所有修改都會遺失。')) {
        // 從緩存中恢復初始版本
        if (initialSubtitlesCache[currentLanguage]) {
            currentSubtitles = JSON.parse(JSON.stringify(initialSubtitlesCache[currentLanguage]));
            originalSubtitles = JSON.parse(JSON.stringify(initialSubtitlesCache[currentLanguage]));
            renderSubtitleEditor();
            hasUnsavedChanges = false;
            updateSaveButtonState();
            showSuccess('已重置', '字幕已恢復到最初版本');
        } else {
            showError('重置失敗', '找不到初始版本');
        }
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
    const count = checkboxes.length;
    const hint = document.getElementById('merge-selection-hint');
    const btn = document.getElementById('generate-merged-btn');
    
    if (!hint || !btn) return;
    
    if (count === 0) {
        hint.textContent = '請選擇 2-3 種語言';
        hint.className = 'merge-hint';
        btn.disabled = true;
    } else if (count === 1) {
        hint.textContent = '✗ 請至少選擇 2 種語言';
        hint.className = 'merge-hint error';
        btn.disabled = true;
    } else if (count >= 2 && count <= 3) {
        hint.textContent = `✓ 已選擇 ${count} 種語言`;
        hint.className = 'merge-hint success';
        btn.disabled = false;
    } else {
        hint.textContent = '✗ 最多選擇 3 種語言';
        hint.className = 'merge-hint error';
        btn.disabled = true;
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
    
    // 讀取格式選擇
    const formatSelect = document.getElementById('merge-format-select');
    const format = formatSelect ? formatSelect.value : 'srt';
    
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
                format: format
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
        a.download = `merged_${selectedLanguages.join('_')}.${format}`;
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
    
    // 錯誤訊息顯示較久（8秒），一般通知 3 秒
    const duration = type === 'error' ? 8000 : 3000;
    setTimeout(() => {
        notification.style.display = 'none';
    }, duration);
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

// ===== 畫中畫 (Picture-in-Picture) 功能 =====

// 設定畫中畫觀察器（使用滾動事件）
function setupPiPObserver() {
    let pipHintTimeout = null;
    
    window.addEventListener('scroll', () => {
        const videoContainer = document.getElementById('video-container');
        const pipHint = document.getElementById('pip-hint');
        const videoPlayer = document.getElementById('video-player');
        
        if (!videoContainer || !pipHint || !videoPlayer) return;
        
        // 計算影片容器頂部距離視窗頂部的距離
        const rect = videoContainer.getBoundingClientRect();
        const distanceFromTop = rect.top;
        
        // 如果畫中畫已啟動，檢查是否需要關閉（當影片回到視窗內時）
        if (pipActive && distanceFromTop > -100) {
            closePiP();
            return;
        }
        
        // 如果畫中畫未啟動，檢查是否需要顯示提示或啟動
        if (!pipActive) {
            // 當影片頂部超過視窗頂部 50px 時，顯示提示
            if (distanceFromTop < -50 && distanceFromTop > -300) {
                pipHint.classList.add('show');
                
                // 清除之前的超時
                if (pipHintTimeout) {
                    clearTimeout(pipHintTimeout);
                }
                
                // 2 秒後自動隱藏提示
                pipHintTimeout = setTimeout(() => {
                    pipHint.classList.remove('show');
                }, 2000);
            } else {
                pipHint.classList.remove('show');
            }
            
            // 當影片頂部超過視窗頂部 300px 且正在播放時，啟動畫中畫
            if (distanceFromTop < -300 && !videoPlayer.paused) {
                activatePiP();
            }
        }
    });
}

// 啟動畫中畫
function activatePiP() {
    if (pipActive) return;
    
    const pipContainer = document.getElementById('pip-container');
    const pipVideo = document.getElementById('pip-video');
    const videoPlayer = document.getElementById('video-player');
    
    if (!pipContainer || !pipVideo || !videoPlayer) return;
    
    // 複製影片源和當前時間
    pipVideo.src = videoPlayer.src;
    pipVideo.currentTime = videoPlayer.currentTime;
    
    // 同步播放速度
    pipVideo.playbackRate = videoPlayer.playbackRate;
    console.log(`畫中畫已同步播放速度: ${pipVideo.playbackRate}×`);
    
    // 同步播放狀態
    if (!videoPlayer.paused) {
        pipVideo.play();
    }
    
    // 靜音主影片（避免雙音軌）
    videoPlayer.muted = true;
    videoPlayer.pause();
    
    // 顯示畫中畫容器
    pipContainer.classList.add('active');
    pipActive = true;
    console.log('✓ 畫中畫已啟動，pipActive =', pipActive);
    
    // 同步播放進度
    pipVideo.addEventListener('timeupdate', syncPiPToMain);
    pipVideo.addEventListener('pause', () => {
        const videoPlayer = document.getElementById('video-player');
        if (videoPlayer) videoPlayer.pause();
    });
    pipVideo.addEventListener('play', () => {
        const videoPlayer = document.getElementById('video-player');
        if (videoPlayer) videoPlayer.play();
    });
}

// 關閉畫中畫
function closePiP() {
    if (!pipActive) return;
    
    const pipContainer = document.getElementById('pip-container');
    const pipVideo = document.getElementById('pip-video');
    const videoPlayer = document.getElementById('video-player');
    
    if (!pipContainer || !pipVideo || !videoPlayer) return;
    
    // 同步時間回主影片
    videoPlayer.currentTime = pipVideo.currentTime;
    
    // 取消靜音主影片
    videoPlayer.muted = false;
    
    // 同步播放狀態
    if (!pipVideo.paused) {
        videoPlayer.play();
    }
    
    // 停止畫中畫影片
    pipVideo.pause();
    pipVideo.src = '';
    
    // 隱藏畫中畫容器
    pipContainer.classList.remove('active');
    pipActive = false;
    console.log('✓ 畫中畫已關閉，pipActive =', pipActive);
    
    // 移除事件監聽
    pipVideo.removeEventListener('timeupdate', syncPiPToMain);
}

// 同步畫中畫到主影片
function syncPiPToMain() {
    const pipVideo = document.getElementById('pip-video');
    const videoPlayer = document.getElementById('video-player');
    if (pipVideo && videoPlayer && pipActive) {
        videoPlayer.currentTime = pipVideo.currentTime;
    }
}

// ===== 鍵盤快捷鍵輔助函數 =====

// 切換全屏（使用容器而非單獨影片元素）
function toggleFullscreenContainer() {
    const videoContainer = document.getElementById('video-container');
    if (!videoContainer) return;
    
    if (!document.fullscreenElement && !document.webkitFullscreenElement && 
        !document.mozFullScreenElement && !document.msFullscreenElement) {
        // 進入全屏
        if (videoContainer.requestFullscreen) {
            videoContainer.requestFullscreen();
        } else if (videoContainer.webkitRequestFullscreen) {
            videoContainer.webkitRequestFullscreen();
        } else if (videoContainer.mozRequestFullScreen) {
            videoContainer.mozRequestFullScreen();
        } else if (videoContainer.msRequestFullscreen) {
            videoContainer.msRequestFullscreen();
        }
    } else {
        // 退出全屏
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        } else if (document.mozCancelFullScreen) {
            document.mozCancelFullScreen();
        } else if (document.msExitFullscreen) {
            document.msExitFullscreen();
        }
    }
}

// 處理全屏狀態變化
function handleFullscreenChange() {
    const overlay = document.getElementById('custom-subtitle-overlay');
    const videoContainer = document.getElementById('video-container');
    const primaryText = document.getElementById('primary-subtitle-text');
    const secondaryText = document.getElementById('secondary-subtitle-text');
    
    if (!overlay || !videoContainer) return;
    
    const isFullscreen = document.fullscreenElement === videoContainer ||
                        document.webkitFullscreenElement === videoContainer ||
                        document.mozFullScreenElement === videoContainer ||
                        document.msFullscreenElement === videoContainer;
    
    if (isFullscreen) {
        console.log('進入全屏模式');
        
        // 強制設置字幕層樣式
        overlay.style.cssText = `
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
            position: absolute !important;
            bottom: 100px !important;
            left: 0 !important;
            right: 0 !important;
            width: 100% !important;
            max-width: 100% !important;
            z-index: 2147483647 !important;
            pointer-events: none !important;
            text-align: center !important;
            transform: translateX(0) !important;
        `;
        
        // 強制設置字幕文字樣式
        if (primaryText) {
            primaryText.style.cssText = `
                display: inline-block !important;
                padding: 8px 16px !important;
                background: rgba(0, 0, 0, 0.8) !important;
                border-radius: 4px !important;
                margin: 4px 0 !important;
                font-size: 2.5rem !important;
                color: #ffffff !important;
                font-weight: 500 !important;
                line-height: 1.4 !important;
                text-shadow: 2px 2px 8px rgba(0, 0, 0, 0.9) !important;
            `;
        }
        
        if (secondaryText) {
            secondaryText.style.cssText = `
                display: inline-block !important;
                padding: 8px 16px !important;
                background: rgba(0, 0, 0, 0.8) !important;
                border-radius: 4px !important;
                margin: 4px 0 !important;
                font-size: 1.8rem !important;
                color: #e2e8f0 !important;
                line-height: 1.4 !important;
                text-shadow: 2px 2px 8px rgba(0, 0, 0, 0.9) !important;
            `;
        }
        
        console.log('全屏字幕層已設置:', {
            overlayDisplay: overlay.style.display,
            overlayZIndex: overlay.style.zIndex,
            overlayPosition: overlay.style.position,
            primaryTextDisplay: primaryText ? primaryText.style.display : 'N/A',
            secondaryTextDisplay: secondaryText ? secondaryText.style.display : 'N/A'
        });
        
    } else {
        console.log('退出全屏模式');
        
        // 退出全屏時，清除內聯樣式（恢復 CSS 控制）
        overlay.style.cssText = '';
        if (primaryText) primaryText.style.cssText = '';
        if (secondaryText) secondaryText.style.cssText = '';
    }
}

// 切換字幕顯示/隱藏
function toggleSubtitleVisibility() {
    const overlay = document.getElementById('custom-subtitle-overlay');
    if (!overlay) return;
    
    if (overlay.style.display === 'none') {
        overlay.style.display = 'block';
    } else {
        overlay.style.display = 'none';
    }
}

// 獲取語言名稱
function getLanguageName(langCode) {
    return availableLanguages[langCode] || langCode;
}

// 重新載入當前顯示的字幕（用於儲存後刷新）
async function reloadCurrentSubtitle() {
    const currentMode = document.querySelector('input[name="subtitle-mode"]:checked')?.value || 'single';
    
    if (currentMode === 'single') {
        // 單語模式：檢查當前選擇的語言
        const primarySubtitleSelect = document.getElementById('primary-subtitle-select');
        const selectedLang = primarySubtitleSelect?.value;
        
        // 如果當前顯示的語言就是剛編輯的語言，重新載入
        if (selectedLang === currentLanguage) {
            console.log(`重新載入單語字幕: ${currentLanguage}`);
            
            // 重新初始化所有 tracks（帶時間戳避免緩存）
            initializeAllTracks(Object.keys(availableLanguages), selectedLang);
        }
    } else if (currentMode === 'dual') {
        // 雙語模式：檢查主語言或副語言
        const primarySubtitleSelectDual = document.getElementById('primary-subtitle-select-dual');
        const secondarySubtitleSelect = document.getElementById('secondary-subtitle-select');
        
        const primaryLang = primarySubtitleSelectDual?.value;
        const secondaryLang = secondarySubtitleSelect?.value;
        
        // 如果編輯的是主語言，重新載入主語言
        if (primaryLang === currentLanguage) {
            console.log(`重新載入主語言: ${currentLanguage}`);
            await loadSubtitleData(currentLanguage, 'primary');
        }
        
        // 如果編輯的是副語言，重新載入副語言
        if (secondaryLang === currentLanguage) {
            console.log(`重新載入副語言: ${currentLanguage}`);
            await loadSubtitleData(currentLanguage, 'secondary');
        }
        
        // 如果字幕更新循環沒在運行，啟動它
        if (!subtitleUpdateInterval) {
            startSubtitleUpdate();
        }
    }
}

// 初始化所有語言的 track 元素（單語模式）
function initializeAllTracks(languages, activeLanguage = null) {
    const videoPlayer = document.getElementById('video-player');
    if (!videoPlayer || !currentJobId) return;
    
    // 移除現有的所有 track
    const existingTracks = videoPlayer.querySelectorAll('track');
    existingTracks.forEach(track => track.remove());
    
    // 為每種語言添加 track 元素
    languages.forEach(lang => {
        const track = document.createElement('track');
        track.kind = 'subtitles';
        track.srclang = lang;
        track.label = availableLanguages[lang] || lang;
        track.src = `/download/${currentJobId}/${lang}?t=${Date.now()}`;
        
        videoPlayer.appendChild(track);
    });
    
    console.log(`已初始化 ${languages.length} 個 track 元素`);
    
    // 等待 tracks 載入後設置活動語言
    setTimeout(() => {
        if (videoPlayer.textTracks) {
            // 先全部設為 hidden
            for (let i = 0; i < videoPlayer.textTracks.length; i++) {
                videoPlayer.textTracks[i].mode = 'hidden';
            }
            
            // 如果指定了活動語言，啟用它
            if (activeLanguage) {
                for (let i = 0; i < videoPlayer.textTracks.length; i++) {
                    const track = videoPlayer.textTracks[i];
                    if (track.language === activeLanguage) {
                        track.mode = 'showing';
                        console.log(`已啟用字幕: ${activeLanguage}`);
                        break;
                    }
                }
            }
            
            // 設置 textTracks 變化監聽器（雙向同步）
            setupTextTrackSync();
        }
    }, 300);
}

// 設置 textTracks 與頁面下拉選單的雙向同步
function setupTextTrackSync() {
    const videoPlayer = document.getElementById('video-player');
    if (!videoPlayer || !videoPlayer.textTracks) return;
    
    // 監聽 textTracks 的變化（CC 按鈕操作）
    videoPlayer.textTracks.addEventListener('change', () => {
        const currentMode = document.querySelector('input[name="subtitle-mode"]:checked')?.value || 'single';
        const primarySubtitleSelect = document.getElementById('primary-subtitle-select');
        
        if (!primarySubtitleSelect) return;
        
        // 找到當前顯示的 track
        let activeTrack = null;
        for (let i = 0; i < videoPlayer.textTracks.length; i++) {
            const track = videoPlayer.textTracks[i];
            if (track.mode === 'showing') {
                activeTrack = track;
                break;
            }
        }
        
        // 同步到單語模式的頁面下拉選單（無論當前是什麼模式）
        if (activeTrack) {
            // CC 按鈕選擇了某個語言
            if (primarySubtitleSelect.value !== activeTrack.language) {
                primarySubtitleSelect.value = activeTrack.language;
                console.log(`CC → 頁面: ${activeTrack.language} (當前模式: ${currentMode})`);
            }
        } else {
            // CC 按鈕關閉了字幕
            if (primarySubtitleSelect.value !== '') {
                primarySubtitleSelect.value = '';
                console.log(`CC → 頁面: 無字幕 (當前模式: ${currentMode})`);
            }
        }
    });
}
