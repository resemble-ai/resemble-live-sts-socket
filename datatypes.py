#### NOTE: Everything sent to/from the server will be in these types
from typing import TypedDict, Literal
from http import HTTPStatus

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
