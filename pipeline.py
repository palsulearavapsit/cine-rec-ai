import subprocess


print("\n===================================")
print("CineRec AI Pipeline Started")
print("===================================\n")


# ===================================
# MODEL 2
# Emotion Classification
# ===================================

print("\nRunning Scene Emotion Classifier...\n")

subprocess.run([
    "python",
    "models/scene_emotion_classifier/run_classifier.py"
])


# ===================================
# MODEL 3
# Scene Importance Ranking
# ===================================

print("\nRunning Scene Importance Ranker...\n")

subprocess.run([
    "python",
    "models/scene_importance_ranker/rank_scenes.py"
])


# ===================================
# MODEL 5
# Timestamp Generation
# ===================================

print("\nGenerating Timestamps...\n")

subprocess.run([
    "python",
    "models/video_scene_extractor/generate_timestamps.py"
])


# ===================================
# MODEL 5
# Clip Extraction
# ===================================

print("\nExtracting Video Clips...\n")

subprocess.run([
    "python",
    "models/video_scene_extractor/extract_clips.py"
])


# ===================================
# MODEL 4
# Music Matching
# ===================================

print("\nRunning Semantic Music Matcher...\n")

subprocess.run([
    "python",
    "models/semantic_music_matcher/music_matcher.py"
])


# ===================================
# MODEL 6
# Reel Composition
# ===================================

print("\nGenerating Final Reel...\n")

subprocess.run([
    "python",
    "models/reel_composer/reel_composer.py"
])


print("\n===================================")
print("CineRec AI Pipeline Completed")
print("===================================\n")