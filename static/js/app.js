// 全域變數
let selectedFile = null;
let currentJobId = null;
let pollInterval = null;

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
const downloadArea = document.getElementById('download-area');
const languageSelect = document.getElementById('language-select');
const previewArea = document.getElementById('preview-area');
const errorMessage = document.getElementById('error-message');

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
    
    // 語言選擇
    languageSelect.addEventListener('change', loadPreview);
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
    
    // 生成下載按鈕（只顯示已生成的語言）
    const languages = {
        'en': 'English',
        'zh-TW': '繁體中文',
        'zh-CN': '簡體中文',
        'ms': 'Bahasa Melayu'
    };
    
    downloadArea.innerHTML = '';
    
    // 只顯示實際生成的字幕檔案
    if (subtitleFiles) {
        for (const lang of Object.keys(subtitleFiles)) {
            const name = languages[lang] || lang;
            const btn = document.createElement('a');
            btn.href = `/download/${currentJobId}/${lang}`;
            btn.className = 'download-btn';
            btn.download = '';
            btn.innerHTML = `
                <svg class="download-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="7 10 12 15 17 10"></polyline>
                    <line x1="12" y1="15" x2="12" y2="3"></line>
                </svg>
                ${name}
            `;
            downloadArea.appendChild(btn);
        }
    }
    
    // 更新語言選擇器（只顯示可用的語言）
    languageSelect.innerHTML = '';
    if (subtitleFiles) {
        for (const lang of Object.keys(subtitleFiles)) {
            const name = languages[lang] || lang;
            const option = document.createElement('option');
            option.value = lang;
            option.textContent = name;
            languageSelect.appendChild(option);
        }
    }
    
    // 載入預覽
    loadPreview();
}

// 載入字幕預覽
async function loadPreview() {
    if (!currentJobId) return;
    
    const language = languageSelect.value;
    
    try {
        const response = await fetch(`/preview/${currentJobId}/${language}`);
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || '載入預覽失敗');
        }
        
        // 顯示字幕
        previewArea.innerHTML = '';
        data.subtitles.forEach(subtitle => {
            const item = document.createElement('div');
            item.className = 'subtitle-item';
            item.innerHTML = `
                <div class="subtitle-time">${subtitle.start_time} --> ${subtitle.end_time}</div>
                <div class="subtitle-text">${subtitle.text}</div>
            `;
            previewArea.appendChild(item);
        });
        
    } catch (error) {
        previewArea.innerHTML = `<p style="color: #c33;">載入預覽失敗: ${error.message}</p>`;
    }
}

// 顯示錯誤訊息
function showError(title, message) {
    errorMessage.innerHTML = `<strong>${title}</strong>${message}`;
    errorMessage.style.display = 'block';
    
    // 3 秒後自動隱藏
    setTimeout(hideError, 5000);
}

// 隱藏錯誤訊息
function hideError() {
    errorMessage.style.display = 'none';
}
