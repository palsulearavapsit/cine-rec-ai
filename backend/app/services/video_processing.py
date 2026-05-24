import os
import random
import subprocess
from typing import List
from app.core.logging import logger

try:
    from moviepy.editor import (
        VideoFileClip,
        concatenate_videoclips,
        AudioFileClip,
        concatenate_audioclips
    )
except ImportError:
    # Handle environment where moviepy is not installed locally during code generation
    VideoFileClip = None


class VideoProcessingService:
    @staticmethod
    def extract_clip(input_video_path: str, start_time: str, end_time: str, output_clip_path: str) -> bool:
        """
        Extracts a sub-clip from a source movie file using high-performance FFmpeg.
        Splits by timestamps without re-encoding unless necessary.
        """
        logger.info(f"Extracting clip from {input_video_path} [ {start_time} --> {end_time} ] to {output_clip_path}")
        
        # Ensure output folder exists
        os.makedirs(os.path.dirname(output_clip_path), exist_ok=True)
        
        # FFmpeg command
        # -ss before -i makes it search fast (input-seeking). -to defines endpoint.
        # Uses libx264 and AAC for maximum web compatibility.
        command = [
            "ffmpeg",
            "-y",                   # Overwrite output file if exists
            "-ss", start_time,
            "-i", input_video_path,
            "-to", end_time,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-strict", "experimental",
            output_clip_path
        ]
        
        try:
            result = subprocess.run(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                check=True
            )
            logger.info(f"Successfully extracted clip: {output_clip_path}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg clip extraction failed. Command: {' '.join(command)}")
            logger.error(f"FFmpeg stdout: {e.stdout}")
            logger.error(f"FFmpeg stderr: {e.stderr}")
            raise RuntimeError(f"FFmpeg error: {e.stderr}") from e

    @staticmethod
    def compose_reel(
        clips_paths: List[str],
        soundtrack_paths: List[str],
        output_path: str,
        target_duration: int = 60,
        min_clip_len: float = 5.0,
        max_clip_len: float = 20.0
    ):
        """
        Combines a list of video clip segments and sets a continuous audio soundtrack overlay.
        Trims composition to match target_duration, rendering using MoviePy.
        """
        if not VideoFileClip:
            raise RuntimeError("moviepy is not installed in the current Python environment.")
            
        logger.info(f"Composing final reel of {target_duration}s using {len(clips_paths)} clips and {len(soundtrack_paths)} soundtracks.")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        video_clips = []
        current_duration = 0.0
        
        try:
            # 1. LOAD AND PREPROCESS CLIPS
            for file_path in clips_paths:
                if current_duration >= target_duration:
                    break
                    
                if not os.path.exists(file_path):
                    logger.warning(f"Clip file not found: {file_path}. Skipping.")
                    continue
                    
                video = VideoFileClip(file_path)
                video_duration = video.duration
                
                # Determine clip length boundary
                target_clip_duration = random.uniform(min_clip_len, max_clip_len)
                remaining_duration = target_duration - current_duration
                target_clip_duration = min(target_clip_duration, remaining_duration)
                
                if video_duration <= target_clip_duration:
                    clip = video
                else:
                    # Sample a random continuous sub-segment
                    start_time = random.uniform(0, video_duration - target_clip_duration)
                    clip = video.subclip(start_time, start_time + target_clip_duration)
                    
                video_clips.append(clip)
                current_duration += clip.duration
                
            if not video_clips:
                raise ValueError("No valid video clips were loaded for composition.")
                
            # Concatenate clips
            logger.info("Concatenating video clips...")
            final_video = concatenate_videoclips(video_clips, method="compose")
            
            # 2. LOAD AND PREPROCESS AUDIO
            audio_clips = []
            for file_path in soundtrack_paths:
                if not os.path.exists(file_path):
                    logger.warning(f"Audio file not found: {file_path}. Skipping.")
                    continue
                audio = AudioFileClip(file_path)
                audio_clips.append(audio)
                
            if audio_clips:
                logger.info("Concatenating soundtracks...")
                final_audio = concatenate_audioclips(audio_clips)
                
                # Align audio length to match video duration
                if final_audio.duration < final_video.duration:
                    final_video = final_video.subclip(0, final_audio.duration)
                else:
                    final_audio = final_audio.subclip(0, final_video.duration)
                    
                # Bind audio to final video
                final_video = final_video.set_audio(final_audio)
            else:
                logger.warning("No soundtracks provided. Final reel will have no audio background.")
                
            # 3. WRITE FINAL OUTPUT
            logger.info(f"Rendering final reel: {output_path}")
            final_video.write_videofile(
                output_path,
                codec="libx264",
                audio_codec="aac",
                fps=24,
                threads=4,
                logger=None # Suppress verbose progress prints
            )
            logger.info("Final reel rendered successfully.")
            
        finally:
            # Clean up open file pointers to avoid lock issues in Windows/Linux
            for clip in video_clips:
                try:
                    clip.close()
                except Exception:
                    pass
            if 'final_video' in locals():
                try:
                    final_video.close()
                except Exception:
                    pass
            if 'audio_clips' in locals():
                for a in audio_clips:
                    try:
                        a.close()
                    except Exception:
                        pass
            if 'final_audio' in locals() and final_audio:
                try:
                    final_audio.close()
                except Exception:
                    pass
