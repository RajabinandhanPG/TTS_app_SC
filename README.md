# Python TTS Applications - Edge TTS & LemonFox AI

Two standalone Python applications for text-to-speech conversion using Microsoft Edge TTS and LemonFox AI services. These command-line tools provide simple, efficient text-to-speech conversion with support for multiple voices and languages.

![Python TTS Apps](https://via.placeholder.com/800x300?text=Python+TTS+Applications)

## Applications Overview

### 🎯 Edge TTS App
- **Free Service**: No API key required
- **High Quality**: Microsoft's neural voices
- **Multi-Language**: 50+ languages supported
- **Fast Processing**: Local processing with cloud voices

### 🚀 LemonFox AI App  
- **AI-Powered**: Advanced neural text-to-speech
- **Premium Quality**: High-fidelity voice synthesis
- **API-Based**: Requires LemonFox API subscription
- **Customizable**: Voice parameters and settings

## Project Structure

```
python-tts-apps/
├── edge_tts_app/
│   ├── edge_tts_converter.py    # Main Edge TTS application
│   ├── voices.py                # Voice listing and management
│   ├── config.py                # Configuration settings
│   ├── output/                  # Generated audio files
│   └── requirements.txt         # Dependencies
├── lemonfox_app/
│   ├── lemonfox_converter.py    # Main LemonFox application
│   ├── api_client.py            # LemonFox API client
│   ├── config.py                # Configuration settings
│   ├── output/                  # Generated audio files
│   ├── .env.example             # Environment variables template
│   └── requirements.txt         # Dependencies
├── shared/
│   ├── utils.py                 # Common utilities
│   └── audio_utils.py           # Audio processing helpers
└── README.md                    # This file
```

## Features

### Common Features
- ✅ **Command-line Interface**: Easy to use CLI
- 🎵 **Multiple Output Formats**: MP3, WAV support
- 📁 **Batch Processing**: Convert multiple texts
- 🔧 **Configurable Settings**: Voice, speed, pitch customization
- 📊 **Progress Tracking**: Real-time conversion progress
- 🗂️ **File Management**: Organized output directory structure

### Edge TTS Specific
- 🆓 **No Cost**: Completely free to use
- ⚡ **Fast Processing**: Quick conversion times
- 🌍 **Extensive Language Support**: 50+ languages
- 🎭 **Voice Variety**: Multiple voices per language
- 📱 **Cross-Platform**: Works on Windows, macOS, Linux

### LemonFox AI Specific
- 🤖 **AI-Enhanced**: Advanced neural synthesis
- 🎨 **Voice Customization**: Fine-tune voice parameters
- 📈 **Credit Tracking**: Monitor API usage
- 🔊 **Premium Quality**: High-fidelity audio output
- ⚙️ **Advanced Settings**: Detailed voice control

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Internet connection for voice synthesis

### Quick Setup

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/python-tts-apps.git
cd python-tts-apps
```

2. **Setup Edge TTS App**:
```bash
cd edge_tts_app
pip install -r requirements.txt
```

3. **Setup LemonFox App**:
```bash
cd ../lemonfox_app
pip install -r requirements.txt
cp .env.example .env
# Edit .env file with your LemonFox API key
```

### Dependencies

#### Edge TTS App
```txt
edge-tts>=6.1.0
asyncio
aiofiles
click>=8.0.0
colorama>=0.4.4
tqdm>=4.64.0
```

#### LemonFox App
```txt
requests>=2.28.0
python-dotenv>=0.19.0
click>=8.0.0
colorama>=0.4.4
tqdm>=4.64.0
pydub>=0.25.1
```

## Usage

### Edge TTS App

#### Basic Usage
```bash
cd edge_tts_app
python edge_tts_converter.py "Hello, this is a test message"
```

#### Advanced Usage
```bash
# Specify voice
python edge_tts_converter.py "Hello world" --voice "en-US-AriaNeural"

# Adjust speech rate and pitch
python edge_tts_converter.py "Hello world" --rate "+20%" --pitch "+5Hz"

# Output to specific file
python edge_tts_converter.py "Hello world" --output "my_audio.mp3"

# List available voices
python edge_tts_converter.py --list-voices

# Filter voices by language
python edge_tts_converter.py --list-voices --language "en"
```

#### Batch Processing
```bash
# From text file
python edge_tts_converter.py --file input.txt

# Multiple texts
python edge_tts_converter.py --batch "Text 1" "Text 2" "Text 3"
```

### LemonFox AI App

#### Setup API Key
```bash
# In lemonfox_app/.env
LEMONFOX_API_KEY=your_api_key_here
```

#### Basic Usage
```bash
cd lemonfox_app
python lemonfox_converter.py "Hello, this is a test message"
```

#### Advanced Usage
```bash
# Specify voice ID
python lemonfox_converter.py "Hello world" --voice-id "voice_12345"

# Custom voice settings
python lemonfox_converter.py "Hello world" --stability 0.8 --clarity 0.9

# Check remaining credits
python lemonfox_converter.py --check-credits

# List available voices
python lemonfox_converter.py --list-voices

# High quality output
python lemonfox_converter.py "Hello world" --quality "high" --format "wav"
```

## Configuration

### Edge TTS Configuration

Create `edge_tts_app/config.py`:
```python
# Default settings
DEFAULT_VOICE = "en-US-AriaNeural"
DEFAULT_RATE = "+0%"
DEFAULT_PITCH = "+0Hz"
OUTPUT_FORMAT = "mp3"
OUTPUT_DIRECTORY = "output"
MAX_TEXT_LENGTH = 1000
```

### LemonFox Configuration

Create `lemonfox_app/config.py`:
```python
# API settings
API_BASE_URL = "https://api.lemonfox.ai/v1"
DEFAULT_VOICE_ID = "default"
DEFAULT_STABILITY = 0.75
DEFAULT_CLARITY = 0.85
OUTPUT_FORMAT = "mp3"
OUTPUT_DIRECTORY = "output"
MAX_TEXT_LENGTH = 5000
REQUEST_TIMEOUT = 30
```

## Command Reference

### Edge TTS Commands

| Command | Description | Example |
|---------|-------------|---------|
| `--voice` | Specify voice | `--voice "en-US-JennyNeural"` |
| `--rate` | Speech rate | `--rate "+20%"` |
| `--pitch` | Voice pitch | `--pitch "-10Hz"` |
| `--output` | Output file | `--output "speech.mp3"` |
| `--list-voices` | List voices | `--list-voices` |
| `--language` | Filter by language | `--language "es"` |
| `--file` | Input from file | `--file "input.txt"` |
| `--batch` | Multiple texts | `--batch "Text1" "Text2"` |

### LemonFox Commands

| Command | Description | Example |
|---------|-------------|---------|
| `--voice-id` | Voice ID | `--voice-id "voice_12345"` |
| `--stability` | Voice stability | `--stability 0.8` |
| `--clarity` | Voice clarity | `--clarity 0.9` |
| `--quality` | Output quality | `--quality "high"` |
| `--format` | Audio format | `--format "wav"` |
| `--list-voices` | List voices | `--list-voices` |
| `--check-credits` | Check credits | `--check-credits` |
| `--output` | Output file | `--output "speech.wav"` |

## Voice Management

### Available Voices

#### Edge TTS Voices (Examples)
- **English**: `en-US-AriaNeural`, `en-US-JennyNeural`, `en-GB-SoniaNeural`
- **Spanish**: `es-ES-ElviraNeural`, `es-MX-DaliaNeural`
- **French**: `fr-FR-DeniseNeural`, `fr-CA-SylvieNeural`
- **German**: `de-DE-KatjaNeural`, `de-AT-IngridNeural`
- **And 40+ more languages...

#### LemonFox Voices
- Use `python lemonfox_converter.py --list-voices` to see available options
- Voice IDs are service-specific and may change

### Voice Selection Tips
1. **Test different voices** for your use case
2. **Consider target audience** and language
3. **Match voice gender** to content context
4. **Test speech rate** for optimal listening experience

## Examples

### Simple Text Conversion
```bash
# Edge TTS
python edge_tts_converter.py "Welcome to our application!"

# LemonFox
python lemonfox_converter.py "Welcome to our application!"
```

### Batch File Processing
```bash
# Create input.txt with multiple lines of text
echo -e "Line 1: Hello world\nLine 2: This is a test\nLine 3: Goodbye" > input.txt

# Edge TTS batch processing
python edge_tts_converter.py --file input.txt

# Process each line as separate audio file
python edge_tts_converter.py --file input.txt --split-lines
```

### Custom Voice Settings
```bash
# Edge TTS with custom settings
python edge_tts_converter.py "Slow and low pitch speech" \
  --voice "en-US-GuyNeural" \
  --rate "-20%" \
  --pitch "-10Hz"

# LemonFox with premium settings
python lemonfox_converter.py "High quality speech" \
  --voice-id "premium_voice_001" \
  --stability 0.9 \
  --clarity 0.95 \
  --quality "high"
```

## Error Handling

### Common Issues

#### Edge TTS
- **Network errors**: Check internet connection
- **Voice not found**: Use `--list-voices` to verify
- **Text too long**: Split text into smaller chunks
- **Permission errors**: Check output directory permissions

#### LemonFox
- **API key invalid**: Verify key in `.env` file
- **Insufficient credits**: Check account balance
- **Rate limiting**: Add delays between requests
- **Voice ID invalid**: Use `--list-voices` to verify

### Troubleshooting

1. **Enable verbose logging**:
```bash
python edge_tts_converter.py "test" --verbose
python lemonfox_converter.py "test" --verbose
```

2. **Check configuration**:
```bash
python -c "import edge_tts; print('Edge TTS OK')"
python -c "import requests; print('Requests OK')"
```

3. **Test API connectivity**:
```bash
# Test LemonFox API
python lemonfox_converter.py --check-credits
```

## Legal Considerations

⚠️ **Important Legal Notice**:

### Edge TTS
- Uses Microsoft's Text-to-Speech service through unofficial access
- For commercial use, consider Microsoft's official Azure AI Speech platform
- Review Microsoft's terms of service for compliance requirements
- Personal and educational use is generally acceptable

### LemonFox AI
- Requires valid API subscription and key
- Commercial use allowed with proper subscription
- Review LemonFox terms of service for usage limits
- Ensure compliance with content policies

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Add your changes with tests
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add docstrings to all functions
- Include error handling
- Add unit tests for new features
- Update documentation

## Performance Tips

### Edge TTS Optimization
- **Concurrent processing**: Use async for batch operations
- **Cache voices list**: Avoid repeated API calls
- **Chunk large texts**: Split long content for better processing
- **Local storage**: Save frequently used audio

### LemonFox Optimization
- **Rate limiting**: Respect API rate limits
- **Batch requests**: Group multiple texts when possible
- **Quality settings**: Balance quality vs. processing time
- **Credit monitoring**: Track usage to avoid interruptions

## Integration

### Using as Python Module

```python
# Edge TTS integration
from edge_tts_app.edge_tts_converter import EdgeTTSConverter

converter = EdgeTTSConverter()
audio_file = converter.convert("Hello world", voice="en-US-AriaNeural")

# LemonFox integration
from lemonfox_app.lemonfox_converter import LemonFoxConverter

converter = LemonFoxConverter(api_key="your_key")
audio_file = converter.convert("Hello world", voice_id="voice_123")
```

### API Wrapper

Both apps can be wrapped as microservices or integrated into larger applications.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

These applications are provided for educational and development purposes. Users are responsible for ensuring compliance with all applicable terms of service and licensing agreements for the TTS providers they choose to use.

## Support

- 📝 **Issues**: [GitHub Issues](https://github.com/yourusername/python-tts-apps/issues)
- 📧 **Email**: your.email@example.com
- 💬 **Discussions**: [GitHub Discussions](https://github.com/yourusername/python-tts-apps/discussions)

## Changelog

### v1.0.0
- Initial release
- Edge TTS implementation
- LemonFox AI implementation
- Command-line interfaces
- Batch processing support

---

**Made with ❤️ for the Python community**
