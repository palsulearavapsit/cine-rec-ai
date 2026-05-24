import os
import shutil
import json
import traceback
from typing import Optional
from uuid import UUID
from app.workers.celery_app import celery_app
from app.core.config import settings
from app.core.logging import logger
from app.core.supabase_client import supabase_admin_client
from app.services.storage import StorageService
from app.services.video_processing import VideoProcessingService
from app.services.ml_orchestrator import MLOrchestrator


@celery_app.task(name="app.workers.tasks.process_reel_generation", bind=True, max_retries=1)
def process_reel_generation(self, reel_id: str):
    """
    Background Task executing the complete CineRec AI orchestration flow:
    Download Movie/Subs -> Emotion Classify -> Rank -> Cut Clips -> Match Sound -> Compose -> Upload
    """
    logger.info(f"Starting async reel generation job. Reel ID: {reel_id}")
    
    # 1. SETUP LOCAL SCRATCH DIRECTORY
    scratch_dir = os.path.join(settings.SCRATCH_DIR, reel_id)
    folders = {
        "videos": os.path.join(scratch_dir, "input_videos"),
        "subtitles": os.path.join(scratch_dir, "subtitles"),
        "clips": os.path.join(scratch_dir, "extracted_clips"),
        "soundtrack": os.path.join(scratch_dir, "soundtrack"),
        "output": os.path.join(scratch_dir, "outputs")
    }
    
    for folder in folders.values():
        os.makedirs(folder, exist_ok=True)
        
    try:
        # 2. FETCH REEL DETAILS FROM DB (Bypassing user RLS using admin client)
        reel_res = supabase_admin_client.table("reels").select("*").eq("id", reel_id).single().execute()
        if not reel_res.data:
            raise ValueError(f"Reel job records not found in database for ID: {reel_id}")
        reel = reel_res.data
        
        project_id = reel["project_id"]
        movie_id = reel["movie_id"]
        selected_emotion = reel["selected_emotion"]
        target_duration = reel["target_duration_seconds"]
        
        # Update status to processing subtitles
        update_reel_status(reel_id, "processing_subtitles")
        
        # 3. FETCH MOVIE DETAILS FROM DB
        movie_res = supabase_admin_client.table("movies").select("*").eq("id", movie_id).single().execute()
        if not movie_res.data:
            raise ValueError(f"Movie records not found in database for ID: {movie_id}")
        movie = movie_res.data
        
        video_remote_path = movie["video_storage_path"]
        srt_remote_path = movie["srt_storage_path"]
        
        if not video_remote_path or not srt_remote_path:
            raise ValueError("Movie is missing valid video or subtitle file pointers in storage.")
            
        # 4. DOWNLOAD MEDIA TO WORKER SCRATCH
        local_video_path = os.path.join(folders["videos"], "movie.mp4")
        local_srt_path = os.path.join(folders["subtitles"], "movie.srt")
        
        StorageService.download_file("movies", video_remote_path, local_video_path)
        StorageService.download_file("movies", srt_remote_path, local_srt_path)
        
        # 5. STEP 2 & 3: RUN EMOTION CLASSIFICATION & IMPORTANT RANKING
        update_reel_status(reel_id, "analyzing_emotions")
        
        # Run emotion classifier
        classified_scenes = MLOrchestrator.classify_scene_emotions(local_srt_path)
        # Run importance ranker
        ranked_scenes = MLOrchestrator.rank_scenes(classified_scenes)
        
        # 6. STEP 4: TIMESTAMP SELECTION & CLIP EXTRACTION
        update_reel_status(reel_id, "extracting_clips")
        
        # Filter scenes matching user requested emotion
        emotional_scenes = [s for s in ranked_scenes if s["dominant_emotion"] == selected_emotion]
        
        # Fallback: if no scene matches emotion, use top ranked generic scenes
        if not emotional_scenes:
            logger.warning(f"No scenes detected matching mood '{selected_emotion}'. Falling back to top overall ranked scenes.")
            emotional_scenes = ranked_scenes[:10]
            
        # Select clips that aggregate to target duration limit
        selected_scenes = []
        accumulated_duration = 0.0
        
        # We roughly estimate each subtitle block represents 3-6s of screen time
        for scene in emotional_scenes:
            if accumulated_duration >= target_duration:
                break
            
            # Retrieve start/end timestamps
            # Format: '00:01:23.450'
            start_str = scene["start"]
            end_str = scene["end"]
            
            # Simple duration estimation (in seconds)
            try:
                def to_sec(t_str):
                    parts = t_str.split(':')
                    sec_parts = parts[2].split('.')
                    return int(parts[0])*3600 + int(parts[1])*60 + int(sec_parts[0]) + float(sec_parts[1])/1000
                duration = to_sec(end_str) - to_sec(start_str)
            except Exception:
                duration = 5.0 # default estimation
                
            selected_scenes.append(scene)
            accumulated_duration += duration
            
        # Extract clips using FFmpeg wrapper
        extracted_clip_paths = []
        for idx, scene in enumerate(selected_scenes):
            clip_name = f"clip_{idx+1}.mp4"
            local_clip_path = os.path.join(folders["clips"], clip_name)
            
            # Extract clip
            VideoProcessingService.extract_clip(
                input_video_path=local_video_path,
                start_time=scene["start"],
                end_time=scene["end"],
                output_clip_path=local_clip_path
            )
            
            # Upload clip to storage
            remote_clip_path = f"{project_id}/{reel_id}/{clip_name}"
            StorageService.upload_file(
                bucket_name="extracted-clips",
                remote_destination_path=remote_clip_path,
                local_file_path=local_clip_path,
                content_type="video/mp4"
            )
            
            extracted_clip_paths.append(local_clip_path)
            
        # 7. STEP 5: SEMANTIC MUSIC MATCHING
        update_reel_status(reel_id, "matching_music")
        
        # Fetch available soundtracks from DB
        tracks_res = supabase_admin_client.table("soundtracks").select("*").execute()
        soundtracks_list = tracks_res.data or []
        
        matched_track = None
        local_track_path = None
        
        if soundtracks_list:
            try:
                matched_track = MLOrchestrator.match_music(selected_emotion, soundtracks_list)
                local_track_path = os.path.join(folders["soundtrack"], "soundtrack.mp3")
                # Download track from soundtracks storage
                StorageService.download_file(
                    bucket_name="soundtracks",
                    remote_path=matched_track["audio_storage_path"],
                    local_destination_path=local_track_path
                )
            except Exception as e:
                logger.error(f"Music matching failed: {str(e)}. Proceeding without background music.")
        else:
            logger.warning("No soundtracks loaded in database. Composition will bypass music integration.")
            
        # 8. STEP 6: REEL COMPOSITION
        update_reel_status(reel_id, "composing_reel")
        
        local_reel_path = os.path.join(folders["output"], "final_reel.mp4")
        soundtrack_paths = [local_track_path] if (local_track_path and os.path.exists(local_track_path)) else []
        
        VideoProcessingService.compose_reel(
            clips_paths=extracted_clip_paths,
            soundtrack_paths=soundtrack_paths,
            output_path=local_reel_path,
            target_duration=target_duration
        )
        
        # 9. STEP 7: UPLOAD COMPLETED REEL & FINALIZE METADATA
        remote_reel_path = f"{project_id}/{reel_id}/final_reel.mp4"
        StorageService.upload_file(
            bucket_name="reels",
            remote_destination_path=remote_reel_path,
            local_file_path=local_reel_path,
            content_type="video/mp4"
        )
        
        # Build comprehensive metadata logs
        final_metadata = {
            "analysis_details": {
                "total_scenes_found": len(classified_scenes),
                "emotion_breakdown": calculate_emotion_breakdown(classified_scenes),
                "selected_scenes": selected_scenes
            },
            "music_details": {
                "track_id": matched_track["id"] if matched_track else None,
                "track_name": matched_track["name"] if matched_track else "None",
                "artist": matched_track["artist"] if matched_track else "None"
            }
        }
        
        # Complete reels table updates
        update_data = {
            "status": "completed",
            "video_storage_path": remote_reel_path,
            "soundtrack_id": matched_track["id"] if matched_track else None,
            "metadata": final_metadata
        }
        supabase_admin_client.table("reels").update(update_data).eq("id", reel_id).execute()
        logger.info(f"Reel generation task finished successfully! Reel ID: {reel_id}")
        
    except Exception as e:
        logger.error(f"Reel generation worker pipeline crashed: {str(e)}")
        # Print full trace to output logs
        traceback.print_exc()
        
        # Update database with failure logs
        err_msg = str(e)[:300] # Cap message size
        supabase_admin_client.table("reels").update({
            "status": "failed",
            "error_message": f"{err_msg}\nTrace: {traceback.format_exc()[-200:]}"
        }).eq("id", reel_id).execute()
        
    finally:
        # 10. SCRATCH CLEANUP
        # Keeps worker node hard disks clean from bulk temporary cuts
        if os.path.exists(scratch_dir):
            logger.info(f"Purging local scratch directory for job: {scratch_dir}")
            shutil.rmtree(scratch_dir, ignore_errors=True)


def update_reel_status(reel_id: str, status: str):
    """Utility to update current execution phase in database."""
    logger.info(f"Job Status Transition -> Reel ID: {reel_id} | Status: {status}")
    supabase_admin_client.table("reels").update({"status": status}).eq("id", reel_id).execute()


def calculate_emotion_breakdown(scenes) -> dict:
    """Helper to compile emotion statistics for final metadata JSON."""
    breakdown = {}
    if not scenes:
        return breakdown
    for s in scenes:
        emo = s.get("dominant_emotion", "unknown")
        breakdown[emo] = breakdown.get(emo, 0) + 1
    return breakdown
