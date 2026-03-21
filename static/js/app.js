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

// 追蹤模式
let trackPlaybackEnabled = false;

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
        // 如果在輸入框或可編輯元素中，不觸發快捷鍵
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) {
            return;
        }
        
        switch(e.code) {
            case 'Space':
                // 空格鍵：播放/暫停
                e.preventDefault();
                if (videoPlayer) {
                    if (videoPlayer.paused) {
                        videoPlayer.play();
                    } else {
                        videoPlayer.pause();
                    }
                }
                break;
                
            case 'ArrowLeft':
                // 左箭頭：後退 5 秒
                e.preventDefault();
                if (videoPlayer) {
                    videoPlayer.currentTime = Math.max(0, videoPlayer.currentTime - 5);
                }
                break;
                
            case 'ArrowRight':
                // 右箭頭：前進 5 秒
                e.preventDefault();
                if (videoPlayer) {
                    videoPlayer.currentTime = Math.min(videoPlayer.duration, videoPlayer.currentTime + 5);
                }
                break;
                
            case 'ArrowUp':
                // 上箭頭：音量增加
                e.preventDefault();
                if (videoPlayer) {
                    videoPlayer.volume = Math.min(1, videoPlayer.volume + 0.1);
                }
                break;
                
            case 'ArrowDown':
                // 下箭頭：音量減少
                e.preventDefault();
                if (videoPlayer) {
                    videoPlayer.volume = Math.max(0, videoPlayer.volume - 0.1);
                }
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
}

// 處理字幕模式切換
function handleSubtitleModeChange(e) {
    subtitleMode = e.target.value;
    
    const singleControls = document.getElementById('single-language-controls');
    const dualControls = document.getElementById('dual-language-controls');
    const videoContainer = document.getElementById('video-container');
    const primarySubtitleSelect = document.getElementById('primary-subtitle-select');
    
    if (subtitleMode === 'single') {
        // 單語模式
        singleControls.style.display = 'block';
        dualControls.style.display = 'none';
        videoContainer.classList.remove('subtitle-mode-dual');
        videoContainer.classList.add('subtitle-mode-single');
        
        // 同步 CC 按鈕的當前狀態到單語下拉選單
        if (videoPlayer.textTracks && primarySubtitleSelect) {
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
                const url = format === 'srt' 
                    ? `/download/${currentJobId}/${lang}/srt`
                    : `/download/${currentJobId}/${lang}`;
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
}

// 載入影片字幕（方案 C：自動判斷模式）
async function loadVideoSubtitle(mode) {
    const videoContainer = document.getElementById('video-container');
    
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
    currentLanguage = editLanguageSelect.value;
    
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
        
        item.innerHTML = `
            <div class="subtitle-time-edit" onclick="seekToTime(${parseTimeToSeconds(subtitle.start_time)})">
                ${subtitle.start_time} --> ${subtitle.end_time}
            </div>
            <div class="subtitle-text-edit" contenteditable="true" data-idx="${idx}">
                ${escapeHtml(subtitle.text)}
            </div>
            ${referenceHtml}
        `;
        
        // 監聽編輯事件
        const textEdit = item.querySelector('.subtitle-text-edit');
        textEdit.addEventListener('input', () => {
            // 自動 trim 空白格
            currentSubtitles[idx].text = textEdit.textContent.trim();
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
    if (videoPlayer) {
        // 暫時禁用追蹤模式避免跳轉時滾動
        const wasTracking = trackPlaybackEnabled;
        trackPlaybackEnabled = false;
        
        videoPlayer.currentTime = seconds;
        videoPlayer.play();
        
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
        saveSubtitlesBtn.textContent = '儲存修改';
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

// ===== 畫中畫 (Picture-in-Picture) 功能 =====

// 設定畫中畫觀察器（使用滾動事件）
function setupPiPObserver() {
    let pipHintTimeout = null;
    
    window.addEventListener('scroll', () => {
        const videoContainer = document.getElementById('video-container');
        const pipHint = document.getElementById('pip-hint');
        
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
    
    if (!pipContainer || !pipVideo || !videoPlayer) return;
    
    // 複製影片源和當前時間
    pipVideo.src = videoPlayer.src;
    pipVideo.currentTime = videoPlayer.currentTime;
    
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
    
    // 同步播放進度
    pipVideo.addEventListener('timeupdate', syncPiPToMain);
    pipVideo.addEventListener('pause', () => {
        if (videoPlayer) videoPlayer.pause();
    });
    pipVideo.addEventListener('play', () => {
        if (videoPlayer) videoPlayer.play();
    });
}

// 關閉畫中畫
function closePiP() {
    if (!pipActive) return;
    
    const pipContainer = document.getElementById('pip-container');
    const pipVideo = document.getElementById('pip-video');
    
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
    
    // 移除事件監聽
    pipVideo.removeEventListener('timeupdate', syncPiPToMain);
}

// 同步畫中畫到主影片
function syncPiPToMain() {
    const pipVideo = document.getElementById('pip-video');
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
    if (!videoPlayer.textTracks) return;
    
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
