import json
import os
import subprocess

VIDEO_PATH = "input_videos/movie.mp4"
TIMESTAMP_FILE = "timestamps/generated_timestamps.json"
OUTPUT_FOLDER = "extracted_clips"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

with open(TIMESTAMP_FILE, "r") as f:
    timestamps = json.load(f)

for idx, scene in enumerate(timestamps):

    start = scene["start"]
    end = scene["end"]

    output_path = os.path.join(
        OUTPUT_FOLDER,
        f"clip_{idx+1}.mp4"
    )

    command = [
        "ffmpeg",
        "-i", VIDEO_PATH,
        "-ss", start,
        "-to", end,
        "-c:v", "libx264",
        "-c:a", "aac",
        output_path
    ]

    subprocess.run(command)

print("All clips extracted successfully.")