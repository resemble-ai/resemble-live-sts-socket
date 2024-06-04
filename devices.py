import sounddevice as sd
import logging

def list_devices(device_type='input'):
    """
    List audio devices based on the device type (input or output).
    
    Parameters:
    device_type (str): Type of device to list ('input' or 'output').
    
    Returns:
    set: A set of indices of available devices of the specified type.
    """
    devices = sd.query_devices()
    if len(devices) == 0:
        raise ValueError("No audio devices found. Make sure you are running this script on a local machine.")

    indices = set()
    print(f"\n{device_type.capitalize()} Devices:")
    for i, device in enumerate(devices):
        if (device_type == 'input' and device['max_input_channels'] >= 1) or \
           (device_type == 'output' and device['max_output_channels'] >= 1):
            print(f"{i}: {device['name']}")
            indices.add(i)
    return indices

def choose_device(device_type='input'):
    """
    Choose an audio device based on the device type (input or output).
    
    Parameters:
    device_type (str): Type of device to choose ('input' or 'output').
    
    Returns:
    tuple: A tuple containing the device index and device name.
    """
    while True:
        try:
            indices = list_devices(device_type)
            index = int(input(f"Enter the index of your {device_type} device: "))
            if index in indices:
                device_info = sd.query_devices(index)
                return index, device_info['name']
            else:
                print(f"Selected index is not a {device_type} device. Please choose another device.")
        except (ValueError, IndexError):
            print("Invalid index. Please enter a valid device index from the list.")

def choose_devices():
    """
    Choose both input and output devices.
    
    Returns:
    tuple: A tuple containing the indices of the chosen input and output devices.
    """
    input_device = choose_device('input')
    output_device = choose_device('output')
    logging.info('[IN] Input device: %s', input_device[1])
    logging.info('[OUT] Output device: %s', output_device[1])
    return input_device[0], output_device[0]
