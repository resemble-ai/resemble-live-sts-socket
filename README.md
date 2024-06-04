# Resemble.AI LiveVC Socket Client

This repository contains a fully featured sample script to demonstrate how to connect to the Resemble.AI LiveVC server using Socket.IO for real-time voice conversion.

## Table of Contents
- [Installation](#installation)
- [Usage](#usage)
- [Arguments](#arguments)
- [Developing Custom Socket Client](#developing-custom-socket-client)
- [License](#license)

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/resemble-ai/resemble-live-sts-socket.git  
    cd resemble-live-sts-socket
    ```

2. Install the required dependencies:
    ```sh
    conda create socket_demo python=3.11.4
    pip install -r requirements.txt
    ```

## Usage
Running the script:
```sh
python main.py --url <server_url> --voice <voice>
# Or if you are using authentication
python main.py --url <server_url> --voice <voice> --auth <username:password>
```
If you do not want to input your microphone and speaker id each time, then the following command with the id you have been choosing:
```sh
python main.py --url <server_url> --voice <voice> \
               --input_device <microphone id> \
               --output_device <speaker id>
```


## Arguments
```yaml
usage: main.py [-h] --url URL [--auth AUTH] [--debug] [--num_chunks NUM_CHUNKS] [--wave_file_path WAVE_FILE_PATH] [--voice VOICE] [--vad VAD] [--gpu GPU] [--extra_convert_size EXTRA_CONVERT_SIZE] [--pitch PITCH] [--crossfade_offset_rate CROSSFADE_OFFSET_RATE] [--crossfade_end_rate CROSSFADE_END_RATE] [--crossfade_overlap_size CROSSFADE_OVERLAP_SIZE] [--input_device INPUT_DEVICE] [--output_device OUTPUT_DEVICE]

Resemble.AI LiveVC socket sample script. Press Ctrl+C to stop.

options:
  -h, --help            show this help message and exit
  --url URL             URL of the server (required)
  --auth AUTH           ngrok `username:password` for authentication.
  --debug               Enable debug mode for logging.

client parameters:
  --num_chunks NUM_CHUNKS           Number of 2880-frame chunks to send to the server (default: 8).
  --wave_file_path WAVE_FILE_PATH   Path to save the WAV file (default: output.wav).

voice parameters:
  --voice VOICE                                         Name of the voice to use for synthesis.
  --vad VAD                                             VAD level (0: off, 1: low, 2: medium, 3: high) (default: 1).
  --gpu GPU                                             CUDA device ID (default: 0).
  --extra_convert_size EXTRA_CONVERT_SIZE               Amount of context for the server to use (4096, 8192, 16384, 32768, 65536, 131072) (default: 4096).
  --pitch PITCH                                         Pitch factor (default: 0).
  --crossfade_offset_rate CROSSFADE_OFFSET_RATE         Crossfade offset rate (0.0 - 1.0) (default: 0.1)
  --crossfade_end_rate CROSSFADE_END_RATE               Crossfade end rate (0.0 - 1.0) (default: 0.9).
  --crossfade_overlap_size CROSSFADE_OVERLAP_SIZE       Crossfade overlap size (default: 2048).

audio device selection. If not specified the user will be provided with a list of devices to choose from.:
  --input_device INPUT_DEVICE, -i INPUT_DEVICE          Index of the input audio device.
  --output_device OUTPUT_DEVICE, -o OUTPUT_DEVICE       Index of the output audio device.
```
## Developing Custom Socket Client
This implementation uses Socket.IO to connect to the server and achieves real-time voice conversion on a M2 Macbook Air client machine, but a lower level websocket implementation can be made as well. 

### Events
- **request_conversion**:
    - Type: `Emit`
    - Description: Sends audio data to the server
    - Data type: `AudioData`
    - Triggers: `on_response`
- **update_model_settings**: 
    - Type: `Emit`
    - Description: Sends updated settings to the server
    - Data type: `VoiceSettings`
    - Triggers: `on_message`
- **get_settings**:
    - Type: `Emit`
    - Description: Requests the current settings dict from the server.
    - Triggers: `on_message`
- **on_connect**:
    - Type: `Response`
    - Description: Callback for when a connection is established to the server
- **on_disconnect**:
    - Type: `Response`
    - Description: Callback for when the connection to the server is disconnected.
- **on_response**:
    - Type: `Response`
    - Description: Called when the client receives the audio response from the server.
    - Data type: `MessageResponse`
- **on_message**:
    - Type: `Response`
    - Description: Called when the client receives a message from the server.
    - Data type: `MessageResponse`

### Data types (`datatypes.py`)
All data sent to and from the server will be in the following data types.
```py
class MessageResponse(TypedDict):
    status: HTTPStatus
    message: str | dict
class AudioData(TypedDict):
    timestamp: int      # milliseconds
    audio_data: bytes   # packed little-endian short integers
class VoiceSettings(TypedDict):
    crossFadeOffsetRate: float # 0.0 - 1.0
    crossFadeEndRate: float    # 0.0 - 1.0 
    crossFadeOverlapSize: int  # 2048
    extraConvertSize: Literal[4096, 8192, 16384, 32768, 65536, 131072]
    gpu: int    # CUDA device ID
    pitch: float
    vad: Literal[0, 1, 2, 3] # 0: off, 1: low, 2: medium, 3: high
```

### Constants (`constants.py`)
These constants are configured to be exactly what the server expects. They cannot be changed.

- **SAMPLERATE = 48000**: Sample rate for audio processing.
- **CHUNK_SIZE_MULT = 2880**: Chunk size multiplier.
- **AUDIO_FORMAT = 'int16'**: Audio format.
- **ENDPOINT = '/synthesize'**: Socket endpoint.

---

For more information, please refer to the code comments and docstrings within the scripts.

## License

This project is licensed under MIT. See the [LICENSE](LICENSE) file for details.

