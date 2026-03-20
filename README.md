# Video Subtitle Translator

Automatic video subtitle generation and translation system using Whisper and Google Translate.

## Quick Start

1. Run `START.bat` to start the server
2. Open http://localhost:8000 in your browser
3. Upload a video file
4. Select target languages for translation
5. Download subtitles in your chosen languages

## Features

- Automatic speech recognition using OpenAI Whisper
- Selective translation to Traditional Chinese, Simplified Chinese, and Malay
- Choose only the languages you need to save processing time
- Web-based interface
- Local processing (no cloud upload)
- Support for videos up to 2 hours

## Requirements

- Python 3.10+
- FFmpeg (must be installed separately)
- 2GB+ free disk space

## Supported Formats

- Video: .mp4, .avi, .mov, .mkv
- Max file size: 5GB
- Max duration: 2 hours

## Usage

### Start Server
```bash
START.bat
```

### Stop Server
Simply close the server window or press Ctrl+C.

## Project Structure

```
video-subtitle-translator/
├── src/              # Source code
├── static/           # Web interface
├── storage/          # Uploaded files and generated subtitles
├── logs/             # Application logs
├── START.bat         # Start server
├── STOP.bat          # Stop server
└── requirements.txt  # Python dependencies
```

## Technical Stack

- **Backend**: FastAPI, Uvicorn
- **Speech Recognition**: OpenAI Whisper
- **Translation**: deep-translator (Google Translate)
- **Frontend**: HTML, CSS, JavaScript
