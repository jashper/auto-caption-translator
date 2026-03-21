# Video Subtitle Translator

Automatic video subtitle generation and translation system using WhisperX and Google Translate.

## 📚 Documentation

- **[INSTALLATION.md](INSTALLATION.md)** - Complete installation guide with troubleshooting
- **[UPGRADE_WHISPERX.md](UPGRADE_WHISPERX.md)** - WhisperX upgrade process and debugging history
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and updates
- **[DESIGN.md](DESIGN.md)** - Technical design and architecture

## 🏷️ Version History

This project uses git tags to mark releases. To view different versions:

```bash
# List all versions
git tag -l

# View changes in a specific version
git show v2.1.0

# Switch to a specific version
git checkout v2.1.0

# Return to latest version
git checkout master
```

**Available versions:**
- `v1.0.0` - Initial release with basic subtitle generation
- `v2.0.0` - Added video player, subtitle editor, and batch download
- `v2.1.0` - WhisperX upgrade with improved subtitle quality (current)

For detailed changes in each version, see [CHANGELOG.md](CHANGELOG.md).

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

- Automatic speech recognition using WhisperX (improved timestamp accuracy and sentence segmentation)
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
- **Speech Recognition**: WhisperX 3.7.2 (enhanced Whisper with precise timestamp alignment)
- **Deep Learning**: PyTorch 2.8.0, torchaudio 2.8.0
- **Translation**: deep-translator (Google Translate)
- **Frontend**: HTML, CSS, JavaScript

## What's New in WhisperX

This system uses **WhisperX 3.7.2** instead of standard Whisper for improved subtitle quality:

- ✅ **More accurate timestamps** - Word-level alignment using forced alignment
- ✅ **Better sentence segmentation** - Natural breaks at sentence boundaries
- ✅ **Improved readability** - Complete sentences instead of fragmented phrases

**Example comparison:**

Standard Whisper:
```
1. I want to
2. go to the store
3. and buy some
4. groceries
```

WhisperX:
```
1. I want to go to the store and buy some groceries.
```

For installation details and troubleshooting, see [INSTALLATION.md](INSTALLATION.md).
- ✅ **Improved readability** - Subtitles flow more naturally
- ✅ **Better translation quality** - Complete sentences improve translation accuracy

WhisperX is completely free and open-source, with no API costs.
