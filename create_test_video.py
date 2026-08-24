import cv2
import numpy as np
import subprocess
import imageio_ffmpeg
import wave
import struct
import math
import os

def create_sample_video():
    """Generates a synthetic 3-second test video with moving visual shapes and audio tone."""
    width, height = 640, 480
    fps = 30
    duration = 3
    total_frames = fps * duration

    temp_raw_avi = "temp_raw.avi"
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(temp_raw_avi, fourcc, fps, (width, height))

    for i in range(total_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # Background
        frame[:] = (40, 40, 40)
        # Draw a simulated object (circle moving across the frame)
        cv2.circle(frame, (100 + i * 4, 240), 40, (0, 0, 255), -1)
        cv2.putText(frame, f"Frame {i}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        out.write(frame)
    out.release()

    # Create a 3-second audio tone WAV file
    temp_audio_wav = "temp_audio.wav"
    sample_rate = 16000
    num_samples = sample_rate * duration
    with wave.open(temp_audio_wav, "w") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for i in range(num_samples):
            # 440 Hz tone
            value = int(16000 * math.sin(2 * math.pi * 440 * (i / sample_rate)))
            wav_file.writeframes(struct.pack('<h', value))

    # Combine with ffmpeg to create sample_test.mp4
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    out_mp4 = "sample_test.mp4"
    cmd = [
        ffmpeg_exe, "-y",
        "-i", temp_raw_avi,
        "-i", temp_audio_wav,
        "-c:v", "libx264",
        "-c:a", "aac",
        out_mp4
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if os.path.exists(temp_raw_avi):
        os.remove(temp_raw_avi)
    if os.path.exists(temp_audio_wav):
        os.remove(temp_audio_wav)

    print(f"Created {out_mp4} successfully.")

if __name__ == "__main__":
    create_sample_video()
