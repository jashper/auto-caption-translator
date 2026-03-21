# Video Subtitle Translator

Automatic video subtitle generation and translation system using Whisper and Google Translate.

## Quick Start

1. Run `START.bat` to start the server
2. Open http://localhost:8000 in your browser
3. Upload a video file
4. Select target languages for translation
5. Wait for processing to complete
6. **Watch video with synchronized subtitles**
7. **Edit subtitles if needed**
8. Download subtitles in your chosen languages (VTT or SRT format)
9. **Or batch download all subtitles at once**

## Features

- Automatic speech recognition using OpenAI Whisper
- Selective translation to Traditional Chinese, Simplified Chinese, and Malay
- Choose only the languages you need to save processing time
- **Video player with subtitle preview**
- **Edit subtitles directly in the browser**
- **Real-time subtitle synchronization with video playback**
- **Click subtitle to jump to video timestamp**
- **Batch download all subtitles as ZIP**
- **Support both VTT and SRT formats**
- **Save edited subtitles to server**
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
- **Speech Recognition**: WhisperX (enhanced Whisper with precise timestamp alignment)
- **Translation**: deep-translator (Google Translate)
- **Frontend**: HTML, CSS, JavaScript

## What's New in WhisperX

This system uses **WhisperX** instead of standard Whisper for improved subtitle quality:

- ✅ **More accurate timestamps** - Word-level alignment for precise timing
- ✅ **Better sentence segmentation** - Natural breaks at sentence boundaries
- ✅ **Improved readability** - Subtitles flow more naturally
- ✅ **Better translation quality** - Complete sentences improve translation accuracy

WhisperX is completely free and open-source, with no API costs.
