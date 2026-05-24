from moviepy.editor import (
    VideoFileClip,
    concatenate_videoclips,
    AudioFileClip,
    concatenate_audioclips
)

import os
import random


# ====================================
# PATHS
# ====================================

CLIPS_FOLDER = "input_clips"

SOUNDTRACK_FOLDER = "soundtrack"

OUTPUT_PATH = (
    "outputs/final_reel.mp4"
)


# ====================================
# SETTINGS
# ====================================

FINAL_REEL_DURATION = 60

MIN_CLIP_DURATION = 5

MAX_CLIP_DURATION = 20


# ====================================
# LOAD ALL VIDEO FILES
# ====================================

clip_files = sorted([

    os.path.join(CLIPS_FOLDER, file)

    for file in os.listdir(CLIPS_FOLDER)

    if file.endswith(".mp4")
])


print("\nLoading video clips...\n")


clips = []

current_duration = 0


for file in clip_files:

    # Stop at 60 seconds
    if current_duration >= FINAL_REEL_DURATION:
        break

    print(f"Loading clip: {file}")

    video = VideoFileClip(file)

    video_duration = video.duration


    # Random clip duration
    target_duration = random.uniform(

        MIN_CLIP_DURATION,

        MAX_CLIP_DURATION
    )


    # Remaining reel duration
    remaining_duration = (
        FINAL_REEL_DURATION -
        current_duration
    )


    # Prevent overflow
    target_duration = min(
        target_duration,
        remaining_duration
    )


    # If video smaller than target
    if video_duration <= target_duration:

        clip = video

    else:

        # Random continuous segment
        start_time = random.uniform(

            0,

            video_duration - target_duration
        )

        end_time = (
            start_time +
            target_duration
        )

        print(
            f"Using segment: "
            f"{start_time:.2f}s "
            f"to "
            f"{end_time:.2f}s"
        )

        clip = video.subclip(
            start_time,
            end_time
        )

    clips.append(clip)

    current_duration += clip.duration


# ====================================
# COMBINE VIDEO CLIPS
# ====================================

print("\nCombining video clips...\n")

final_video = concatenate_videoclips(
    clips,
    method="compose"
)


# ====================================
# LOAD ALL AUDIO FILES
# ====================================

audio_files = sorted([

    os.path.join(SOUNDTRACK_FOLDER, file)

    for file in os.listdir(SOUNDTRACK_FOLDER)

    if file.endswith(".mp3")
])


print("\nLoading soundtrack files...\n")


audio_clips = []


for file in audio_files:

    print(f"Loading soundtrack: {file}")

    audio = AudioFileClip(file)

    audio_clips.append(audio)


# ====================================
# COMBINE AUDIO FILES
# ====================================

print("\nCombining soundtrack audio...\n")

final_audio = concatenate_audioclips(
    audio_clips
)


# ====================================
# MATCH AUDIO TO VIDEO
# ====================================

if final_audio.duration < final_video.duration:

    final_video = final_video.subclip(
        0,
        final_audio.duration
    )

else:

    final_audio = final_audio.subclip(
        0,
        final_video.duration
    )


# ====================================
# APPLY AUDIO
# ====================================

final_video = final_video.set_audio(
    final_audio
)


# ====================================
# EXPORT FINAL REEL
# ====================================

print("\nRendering final reel...\n")

final_video.write_videofile(

    OUTPUT_PATH,

    codec="libx264",

    audio_codec="aac",

    fps=24
)


print(
    "\nFinal reel generated successfully."
)