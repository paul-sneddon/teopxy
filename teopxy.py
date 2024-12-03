#!python3

import os
import sys
import struct
import json
import math
import glob
from pydub import AudioSegment

MAXENDPOINT = 2147483646

# Parsing OP-1 metadata
def parse_op1_metadata(file_path):
    def read_chunk_header(file):
        header = file.read(8)
        if len(header) < 8:
            return None, None
        chunk_id, chunk_size = struct.unpack('>4sI', header)
        return chunk_id, chunk_size

    metadata = None
    totalsamples = 0

    with open(file_path, 'rb') as f:
        if f.read(4) != b'FORM':
            return None

        f.read(4)
        format_id = f.read(4)
        if format_id not in (b'AIFF', b'AIFC'):
            return None

        while True:
            try:
                chunk_id, chunk_size = read_chunk_header(f)
                if not chunk_id:
                    break

                if chunk_id == b'SSND':
                    totalsamples = chunk_size // 2
                    f.seek(chunk_size, os.SEEK_CUR)

                elif chunk_id == b'APPL':
                    app_id = f.read(4)
                    if app_id == b'op-1':
                        appl_data = f.read(chunk_size - 4)
                        appl_data = appl_data.decode('utf-8').strip('\0').strip()
                        metadata = json.loads(appl_data)
                    else:
                        f.seek(chunk_size - 4, os.SEEK_CUR)
                else:
                    f.seek(chunk_size, os.SEEK_CUR)
            except struct.error:
                break

    return metadata, totalsamples

# I can't figure out a simple function to map the values
def __map_gain(x):
    """
    Converts a value from the range 0 to 32767 to a range of -30 to +20 based on defined key points.

    Key Points:
        0      => -30
        4,096  => -15
        8,192  => 0
        16,384 => 10
        32,768 => 20

    Parameters:
        x (int or float): The input value to be converted. Expected range is 0 to 32767.

    Returns:
        float: The converted value in the range -30 to +20.
    """

    # Define the key points as (input, output) tuples
    key_points = [
        (0, -30),
        (4096, -15),
        (8192, 0),
        (16384, 10),
        (32768, 20)  # Note: 32768 is included to handle the upper bound
    ]

    # Clamp the input value to the valid range
    if x < 0:
        x = 0
    elif x > 32767:
        x = 32767

    # Iterate through the key points to find the appropriate interval
    for i in range(len(key_points) - 1):
        x0, y0 = key_points[i]
        x1, y1 = key_points[i + 1]

        if x <= x1:
            # Calculate the proportion (t) of how far x is between x0 and x1
            if x1 == x0:
                t = 0
            else:
                t = (x - x0) / (x1 - x0)

            # Perform linear interpolation
            y = y0 + t * (y1 - y0)
            return y

    # If x exceeds the last key point, return the last y value
    return key_points[-1][1]


# Patch JSON creation
def create_patch_json(output_dir, audio_files, metadata, total_duration_ms, num_channels):
    if metadata:
        original_json_path = os.path.join(output_dir, "original.json")
        with open(original_json_path, "w") as f:
            json.dump(metadata, f, indent=2)
        print(f"Exported {original_json_path}")
    # Else create an empty metadata object
    else:
        metadata = {}

    preset = {
        "engine": {
            "bendrange": 8191,
            "highpass": 0,
            "modulation": {
                "aftertouch": {"amount": 16383, "target": 0},
                "modwheel": {"amount": 16383, "target": 0},
                "pitchbend": {"amount": 16383, "target": 0},
                "velocity": {"amount": 16383, "target": 0}
            },
            "params": [16384] * 8,
            "playmode": "poly",
            "portamento.amount": 0,
            "portamento.type": 32767,
            "transpose": 0,
            "tuning.root": 0,
            "tuning.scale": 0,
            "velocity.sensitivity": 19660,
            "volume": 18348,
            "width": 0
        },
        "envelope": {
            "amp": {"attack": 0, "decay": 0, "release": 1000, "sustain": 32767},
            "filter": {"attack": 0, "decay": 14581, "release": 0, "sustain": 0}
        },
        "fx": {
            "active": False,
            "params": [22014, 0, 30285, 11880, 0, 32767, 0, 0],
            "type": "ladder"
        },
        "lfo": {
            "active": False,
            "params": [6212, 16865, 18344, 16000, 0, 0, 0, 0],
            "type": "tremolo"
        },
        "octave": 0,
        "platform": "OP-XY",
        "regions": [],
        "type": "drum",
        "version": 4
    }

    # Mapping for playmode values
    playmode_mapping = {
        4096: "gate",
        12288: "oneshot",
        20480: "group",
        28672: "loop"
    }

    # Map audio files to regions
    for i, audio_file in enumerate(audio_files):
        if not audio_file:
            continue  # Skip missing samples

        # Calculate frame count based on number of channels
        bytes_per_sample = 2  # 16-bit samples
        bytes_per_frame = bytes_per_sample * num_channels
        frame_count = os.path.getsize(audio_file) // bytes_per_frame

        playmode_value = metadata.get("playmode", [12288]*24)[i]
        playmode_str = playmode_mapping.get(playmode_value, "oneshot")

        pitch_value = metadata.get("pitch", [0]*24)[i]
        transpose = pitch_value // 512  # Convert pitch to semitone transpose

        volume_value = metadata.get("volume", [8192]*24)[i]
        gain = __map_gain(volume_value)

        print(f"Region {i + 1}: {audio_file}, frames={frame_count}, playmode={playmode_str}, transpose={transpose}, volume={volume_value}, gain={round(gain)}")

        region = {
            "fade.in": 0,
            "fade.out": 0,
            "framecount": frame_count,
            "hikey": 53 + i,
            "lokey": 53 + i,
            "gain": round(gain),
            "pan": 0,
            "pitch.keycenter": 60,
            "playmode": playmode_str,
            "reverse": False,
            "sample": os.path.basename(audio_file),
            "sample.end": frame_count,
            "transpose": transpose,
            "tune": 0
        }
        preset["regions"].append(region)

    patch_file = os.path.join(output_dir, "patch.json")
    with open(patch_file, "w") as f:
        json.dump(preset, f, indent=2)
    print(f"Exported {patch_file}")

def assign_samples_to_layout(wav_files, layout):
    assignments = {
        1: "kick",
        2: "kick",
        3: "snare",
        4: "snare",
        5: ["rimshot", "rim"],
        6: ["clap", "hand"],
        7: ["tambourine", "shaker"],
        9: ["hihat", "hi-hat", "closed"],
        11: ["hihat", "hi-hat", "open"],
        14: ["ride", "cymbal"],
        16: ["crash", "cymbal"],
        20: ["bass", "synth"],
        21: ["bass", "synth"],
        22: ["bass", "synth"],
        23: ["bass", "synth"],
        24: ["bass", "synth"],
    }

    used_files = set()
    result = [None] * 24

    def match_keyword_count(sample_name, keywords):
        """
        Counts how many keywords from the list are found in the sample name.
        """
        if isinstance(keywords, list):
            return sum(1 for keyword in keywords if keyword in sample_name)
        return 1 if keywords in sample_name else 0

    print("Assigning matched samples to drum layout:\n")
    for key, keywords in assignments.items():
        best_match = None
        highest_match_count = 0

        for wav_file in wav_files:
            if wav_file in used_files:
                continue

            # Calculate the match count for the current file
            match_count = match_keyword_count(wav_file.lower(), keywords)

            # If this file matches more keywords than the current best, prioritize it
            if match_count > highest_match_count:
                best_match = wav_file
                highest_match_count = match_count

        # Assign the best match if found
        if best_match:
            result[key - 1] = best_match
            used_files.add(best_match)
            print(f"Key {key}: {best_match} (Matched {highest_match_count} keywords)")

    print("Assigning unmatched samples to drum layout:\n")
    unused_files = [f for f in wav_files if f not in used_files]
    for i in range(24):
        if result[i] is None and unused_files:
            print(f"Key {i + 1}: {unused_files[0]}")
            result[i] = unused_files.pop(0)
    return result

# Splitting OP-1 drum patch

def split_op1_drum_patch(file_path, output_dir=None):
    metadata, total_samples = parse_op1_metadata(file_path)
    starts = metadata["start"]
    ends = metadata["end"]
    num_keys = min(len(starts), len(ends), 24)  # Ensure we don't exceed 24 keys

    # Load the audio file
    audio = AudioSegment.from_file(file_path, format="aiff")
    total_duration_ms = len(audio)
    sample_rate = audio.frame_rate
    num_channels = audio.channels
    print(f"Total duration: {total_duration_ms} ms")
    print(f"Total samples: {total_samples}")
    print(f"Sample rate: {sample_rate} Hz")
    print(f"Channels: {num_channels}")

    base_name = os.path.splitext(os.path.basename(file_path))[0]
    base_output_dir = output_dir or os.path.dirname(file_path)
    output_dir = os.path.join(base_output_dir, f"{base_name}.preset")
    os.makedirs(output_dir, exist_ok=True)

    audio_files = []

    # Determine max length in seconds based on total duration
    max_length_seconds = 20 if (total_duration_ms > 12000 or num_channels > 1) else 12

    print(f"Max length: {max_length_seconds} seconds")

    SAMPLECONVERSION = MAXENDPOINT / (44100 * max_length_seconds)

    for i in range(num_keys):
        raw_start = starts[i]
        raw_end = ends[i]

        if raw_start == raw_end or (raw_start == 8192 and raw_end == 8192):
            print(f"Skipping unused key {i + 1}: start={raw_start}, end={raw_end}")
            audio_files.append(None)
            continue

        # Reverse Go code logic
        start_seconds = raw_start / (441 * SAMPLECONVERSION)
        end_seconds = raw_end / (441 * SAMPLECONVERSION)

        start_ms = start_seconds * 10
        end_ms = end_seconds * 10

        if start_ms >= end_ms or start_ms < 0:
            print(f"Skipping invalid key {i + 1}: start_ms={start_ms}, end_ms={end_ms}")
            audio_files.append(None)
            continue

        print(f"Processing slice {i + 1}: start={start_ms:.2f}ms, end={end_ms:.2f}ms")
        output_path = os.path.join(output_dir, f"{base_name}_{i + 1:02d}.wav")
        sample = audio[start_ms:end_ms]
        sample.export(output_path, format="wav")
        audio_files.append(output_path)
        print(f"Exported {output_path}")

    # Generate patch.json
    create_patch_json(output_dir, audio_files, metadata, total_duration_ms, audio.channels)

def create_preset_from_wavs(folder_path, layout="standard", output_dir=None, leave_gaps=False):
    print(f"Processing directory: {folder_path}")
    print(f"Output directory: {output_dir}")
    if not os.path.isdir(folder_path):
        print(f"Error: Directory '{folder_path}' not found.")
        return

    wav_files = [f for f in os.listdir(folder_path) if f.endswith(".wav")]

    if layout == "standard":
        audio_files = assign_samples_to_layout(wav_files, layout)
    else:
        if all(f[0].isdigit() for f in wav_files):
            wav_files.sort(key=lambda x: int(x.split("_")[0]))
        else:
            wav_files.sort()
        audio_files = wav_files[:24]

    # Determine output directory
    preset_name = os.path.basename(folder_path) + ".preset"
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_dir = os.path.join(output_dir, preset_name)
    else:
        output_dir = os.path.join(folder_path, preset_name)
    os.makedirs(output_dir, exist_ok=True)

    copied_files = []
    for wav_file in audio_files:
        if wav_file:
            source_path = os.path.join(folder_path, wav_file)
            destination_path = os.path.join(output_dir, wav_file)
            copied_files.append(destination_path)
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            with open(source_path, 'rb') as src, open(destination_path, 'wb') as dest:
                dest.write(src.read())
        else:   
            if leave_gaps:
                copied_files.append(None)
    
    create_patch_json(output_dir, copied_files, None, 0, 1)

def process_directories_with_wildcard(path_pattern, layout="standard", output_dir=None, leave_gaps=False):
    directories = [path for path in glob.glob(path_pattern) if os.path.isdir(path)]

    if not directories:
        print(f"No directories match the pattern: {path_pattern}")
        return

    for folder_path in directories:
        print(f"Processing directory: {folder_path}")
        create_preset_from_wavs(folder_path, layout=layout, output_dir=output_dir, leave_gaps=leave_gaps)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python script.py <convert|create> <path|pattern> [--layout=<standard|number>] [--output=<output_dir>]")
        sys.exit(1)

    command = sys.argv[1].lower()
    path = sys.argv[2]
    layout = "standard"
    output_dir = None
    leave_gaps = "true"

    # Parse optional arguments
    for arg in sys.argv[3:]:
        if arg.startswith("--layout="):
            layout = arg.split("=")[1].lower()
        elif arg.startswith("--output="):
            output_dir = arg.split("=")[1]
        elif arg.startswith("--gaps="):
            leave_gaps = arg.split("=")[1]
    
    # Default leave_gaps to True unless explicitly set to False
    leave_gaps = False if leave_gaps == "false" else True 

    # Expand the output directory path
    if output_dir:
        output_dir = os.path.expanduser(output_dir)
        output_dir = os.path.expandvars(output_dir)

    # Check if the output directory is valid, if not, it it's parent is valid then create it
    if output_dir and not os.path.isdir(output_dir):
        parent_dir = os.path.dirname(output_dir)
        if os.path.isdir(parent_dir):
            os.makedirs(output_dir, exist_ok=True)
        else:
            print(f"Error: Output directory '{output_dir}' not found.")
            sys.exit(1)

    if command == "convert":
        split_op1_drum_patch(path, output_dir=output_dir)
    elif command == "create":
        if "*" in path or "?" in path or "[" in path:
            process_directories_with_wildcard(path, layout=layout, output_dir=output_dir, leave_gaps=leave_gaps)
        else:
            create_preset_from_wavs(path, layout=layout, output_dir=output_dir, leave_gaps=leave_gaps)
    else:
        print("Error: Unknown command. Use 'convert' or 'create'.")
        sys.exit(1)