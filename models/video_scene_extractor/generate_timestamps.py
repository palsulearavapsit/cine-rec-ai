import pysrt
import json
import os

SUBTITLE_FILE = "subtitles/movie.srt"
OUTPUT_FILE = "timestamps/generated_timestamps.json"

subs = pysrt.open(SUBTITLE_FILE)

timestamps = []

for sub in subs:

    text = sub.text.lower()

    important_words = [
        "kill",
        "run",
        "danger",
        "love",
        "revenge",
        "fight",
        "gun",
        "war",
        "death",
        "escape"
    ]

    score = 0

    for word in important_words:
        if word in text:
            score += 1

    if score > 0:

        timestamps.append({
            "start": str(sub.start).replace(",", "."),
            "end": str(sub.end).replace(",", "."),
            "text": sub.text,
            "score": score
        })

os.makedirs("timestamps", exist_ok=True)

with open(OUTPUT_FILE, "w") as f:
    json.dump(timestamps, f, indent=4)

print("Automatic timestamps generated successfully.")