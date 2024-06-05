# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# Sample script to demonstrate how to connect to the Resemble.AI Live STS #
# server using Socket.IO for real-time voice conversion.                  #
#                                                                         #
# Date:    2024-06-03                                                     #
# Rev:     1.0                                                            #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # 

import sounddevice as sd
import numpy as np
import socketio
import argparse
import logging
import struct
import queue
import base64
import time
import wave

from constants import SAMPLERATE, CHUNK_SIZE_MULT, AUDIO_FORMAT, ENDPOINT
from datatypes import MessageResponse, AudioData, VoiceSettings, HTTPStatus
from devices import choose_devices

rtf_list = []

class SynthesizeNamespace(socketio.ClientNamespace):
    """
    Custom namespace for handling Socket.IO events.
    """
    def __init__(self, namespace):
        super().__init__(namespace)

    def on_connect(self):
        logging.info('[SIO↕] Connected to the %s namespace', ENDPOINT)

    def on_disconnect(self):
        logging.info('[SIO↕] Disconnected from the %s namespace', ENDPOINT)

    def on_response(self, msg: AudioData):
        """
        Called when the client receives a response from the server for voice conversion.
        
        Parameters:
        msg (AudioData): The audio data received from the server.
        """
        logging.debug('[SIO↓] Received processed audio data')
        timestamp = msg['timestamp']
        response_time = time.time() * 1000 - timestamp  # Time spent processing in the server

        # Convert received data back to numpy array
        data = msg['audio_data']
        unpacked_data = struct.unpack('<%sh' % (len(data) // struct.calcsize('<h')), data)
        audio_data = np.array(unpacked_data, dtype=AUDIO_FORMAT)

        # Queue the processed audio data for playback
        playback_queue.put((audio_data, response_time)) 

    def on_message(self, msg: MessageResponse):
        """
        Called when the client receives a message from the server.
        
        Parameters:
        msg (MessageResponse): The message received from the server.
        """
        status = HTTPStatus(msg['status'])
        
        # check if the message is in the 200s, 300s, or 400s and log accordingly
        if status < 300:
            logging.info(f'[SIO↓] {msg["message"]}')
        elif status < 400:
            logging.warning(f'[SIO↓] {msg["message"]}')
        else:
            logging.error(f'[SIO↓] {msg["message"]}')


    def change_settings(self, settings: VoiceSettings):
        """
        Change the settings of the server.
        
        Parameters:
        settings (VoiceSettings): The settings to change to.
        """
        logging.info('[SIO↑] Changing settings...')

        # wait for the server to respond before continuing
        self.emit('update_model_settings', settings)

    def send_audio(self, audio_data: AudioData):
        """
        Send audio data to the server.
        
        Parameters:
        audio_data (AudioData): The audio data to send to the server.
        """

        logging.debug('[SIO↑] Sending audio data to server')
        self.emit('request_conversion', audio_data)
    
    def get_settings(self):
        """
        Get the current settings from the server.
        """

        logging.info('[SIO↑] Getting settings...')
        self.emit('get_settings')

def audio_callback(indata: np.ndarray, frames: int, t: object, status: sd.CallbackFlags) -> None:    
    """
    Callback function for handling audio input.
    
    Parameters:
    indata (numpy.ndarray): The recorded audio data.
    frames (int): The number of frames.
    t (CData): A timestamp of the audio data.
    status (CallbackFlags): The status of the callback.
    """

    if status:
        logging.warning(status)
    
    # Convert the recorded audio chunk to int16 format and bytes
    audio_chunk = (indata * 32767).astype(AUDIO_FORMAT).flatten()
    audio_chunk = struct.pack('<%sh' % len(audio_chunk), *audio_chunk)
    
    synthesize.send_audio({'timestamp': int(time.time() * 1000), 'audio_data': audio_chunk})

def playback_callback(outdata: np.ndarray, frames: int, t: object, status: sd.CallbackFlags) -> None:
    """
    Callback function for handling audio playback.
    
    Parameters:
    outdata (numpy.ndarray): The output audio data buffer.
    frames (int): The number of frames.
    time (CData): A timestamp of the audio data.
    status (CallbackFlags): The status of the callback.
    """
    if status:
        logging.warning(status)

    if not playback_queue.empty():
        audio_data, processing_time = playback_queue.get()
        audio_length = len(audio_data)
        outdata[:audio_length, 0] = audio_data  # Directly assign to the buffer slice

        playback_duration = 1000 * audio_length / SAMPLERATE
        rtf_list.append(processing_time / playback_duration)
        
        if audio_length < frames:
            logging.warning('[OUTPUT] Audio data is smaller than the buffer! Filling with zeros...')
            outdata[audio_length:, 0] = 0  # Fill the rest with zeros
    else:
        outdata.fill(0)  # Fill with zeros if no audio data is available

def main(server_url: str, 
         auth: str, 
         input_device: int, 
         output_device: int, 
         chunk_size: int, 
         wav_file_path: str, 
         voice_settings: VoiceSettings) -> None:
    """
    Main function to start the audio streams and handle server connection.
    
    Parameters:
    server_url (str): The URL of the server.
    auth (str): The authentication string for the server.
    input_device (int): The index of the input audio device.
    output_device (int): The index of the output audio device.
    chunk_size (int): The size of the audio chunk.
    wav_file_path (str): The path to save the WAV file.
    voice_settings (VoiceSettings): The settings to use for the voice.
    """
    
    global wav_file
    global playback_queue
    global synthesize

    playback_queue = queue.Queue()

    # Connect to the server
    synthesize = SynthesizeNamespace(ENDPOINT)
    sio = socketio.Client()
    sio.register_namespace(synthesize)    
    headers={'Authorization': 'Basic ' + base64.b64encode(auth.encode()).decode()} if auth else None
    sio.connect(server_url, namespaces=[ENDPOINT], headers=headers)

    # Update and read server parameters
    synthesize.change_settings(voice_settings)
    synthesize.get_settings()

    # Setup the wav file
    wav_file = wave.open(wav_file_path, 'wb')
    wav_file.setnchannels(1)
    wav_file.setsampwidth(2)  # 2 bytes for int16
    wav_file.setframerate(SAMPLERATE)

    # Start the audio streams
    try:
        with sd.InputStream(callback=audio_callback, channels=1, dtype='float32', samplerate=SAMPLERATE, blocksize=chunk_size, device=input_device):
            with sd.OutputStream(callback=playback_callback, channels=1, dtype=AUDIO_FORMAT, samplerate=SAMPLERATE, blocksize=chunk_size, device=output_device):
                logging.info('[INFO] Recording... Press Ctrl+C to stop')
                while True:
                    sd.sleep(1)
    except KeyboardInterrupt:
        pass
    # Cleanup
    wav_file.close()
    sio.disconnect()
    logging.info(f'------- Average RTF {sum(rtf_list[5:])/len(rtf_list[5:]):0.3f} -------')

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Resemble.AI LiveVC socket sample script. Press Ctrl+C to stop.')

    parser.add_argument('--url', type=str, required=True, help='URL of the server (Do not include the endpoint).')
    parser.add_argument('--auth',type=str, default=None, help='ngrok `username:password` for authentication.')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode for logging.')

    client_parameter = parser.add_argument_group('client parameters')
    client_parameter.add_argument('--num_chunks', type=int, default=8, help='Number of 2880-frame chunks to send to the server (default: 8).')
    client_parameter.add_argument('--wave_file_path', type=str, default='output.wav', help='Path to save the WAV file (default: output.wav).')

    voice_parameter = parser.add_argument_group('voice parameters')
    voice_parameter.add_argument('--voice', type=str, default='Mike', help='Name of the voice to use for synthesis.')
    voice_parameter.add_argument('--vad', type=int, default=1, help='VAD level (0: off, 1: low, 2: medium, 3: high).')
    voice_parameter.add_argument('--gpu', type=int, default=0, help='CUDA device ID.')
    voice_parameter.add_argument('--extra_convert_size', type=int, default=4096, help='Amount of context for the server to use (4096, 8192, 16384, 32768, 65536, 131072).')
    voice_parameter.add_argument('--pitch', type=float, default=0, help='Pitch factor (default: 0).')
    voice_parameter.add_argument('--crossfade_offset_rate', type=float, default=0.1, help='Crossfade offset rate (0.0 - 1.0).')
    voice_parameter.add_argument('--crossfade_end_rate', type=float, default=0.9, help='Crossfade end rate (0.0 - 1.0).')
    voice_parameter.add_argument('--crossfade_overlap_size', type=int, default=2048, help='Crossfade overlap size (default: 2048).')

    device_group = parser.add_argument_group('audio device selection. If not specified, the user will be provided with a list of devices to choose from.')
    device_group.add_argument('--input_device', '-i', type=int, help='Index of the input audio device.')
    device_group.add_argument('--output_device', '-o', type=int, help='Index of the output audio device.')

    args = parser.parse_args()

    if (args.input_device is None) != (args.output_device is None):
        parser.error("Both --input_device and --output_device must be specified together.")

    return args

if __name__ == "__main__":
    args = parse_args()
    
    chunk_size = CHUNK_SIZE_MULT * args.num_chunks
    buffer_length = int(1000 * chunk_size / SAMPLERATE)

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format='(%(levelname)s)  %(message)s')
    logging.info(f'------- Resemble.AI LiveVC Socket Client -------')
    logging.info(f'[INFO] Buffer length: {buffer_length:d} ms')

    # Select audio devices
    if args.input_device is not None and args.output_device is not None:
        input_device = args.input_device
        output_device = args.output_device
    else:
        input_device, output_device = choose_devices()
    
    voice_settings: VoiceSettings = {
        'voice': args.voice,
        'crossFadeOffsetRate': args.crossfade_offset_rate,
        'crossFadeEndRate': args.crossfade_end_rate,
        'crossFadeOverlapSize': args.crossfade_overlap_size,
        'extraConvertSize': args.extra_convert_size,
        'gpu': args.gpu,
        'pitch': args.pitch,
        'vad': args.vad
    }

    main(args.url, 
         args.auth, 
         input_device, 
         output_device,
         chunk_size, 
         args.wave_file_path,
         voice_settings)
