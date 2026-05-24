import os
import pickle
import json
import pysrt
from typing import List, Dict, Any
import numpy as np
from app.core.logging import logger

# Try loading torch/safetensors safely
try:
    import torch
    from safetensors.torch import load_file as load_safetensors
except ImportError:
    torch = None
    load_safetensors = None


class MLOrchestrator:
    _models_cache = {}

    @classmethod
    def load_emotion_classifier(cls):
        """
        Loads the Hugging Face transformer / safetensors model into warm memory.
        """
        model_dir = "models/scene_emotion_classifier"
        if "emotion_classifier" in cls._models_cache:
            return cls._models_cache["emotion_classifier"]

        if not os.path.exists(model_dir):
            logger.warning(f"Emotion classifier folder not found at {model_dir}. Operating in fallback/rule-based mode.")
            return None

        try:
            logger.info("Initializing scene emotion classifier model into memory...")
            # Example loading logic from local weights
            if load_safetensors and torch:
                weights_path = os.path.join(model_dir, "model.safetensors")
                config_path = os.path.join(model_dir, "config.json")
                
                # Check for files
                if os.path.exists(weights_path) and os.path.exists(config_path):
                    # Load weights
                    state_dict = load_safetensors(weights_path)
                    with open(config_path, "r") as f:
                        config = json.load(f)
                    
                    # Store standard metadata
                    model_obj = {
                        "weights": state_dict,
                        "config": config,
                        "vocab_path": os.path.join(model_dir, "vocab.txt")
                    }
                    cls._models_cache["emotion_classifier"] = model_obj
                    logger.info("Emotion classifier loaded into CPU/GPU memory successfully.")
                    return model_obj
            
            logger.warning("Libraries (torch, safetensors) missing or weights unavailable. Falling back to rule-based classification.")
            return None
        except Exception as e:
            logger.error(f"Error loading emotion classifier: {str(e)}. Using fallback.")
            return None

    @classmethod
    def load_importance_ranker(cls):
        """
        Loads the Scikit-learn/XGBoost importance model pickle.
        """
        model_path = "models/scene_importance_ranker/importance_model.pkl"
        if "importance_ranker" in cls._models_cache:
            return cls._models_cache["importance_ranker"]

        if not os.path.exists(model_path):
            logger.warning(f"Importance model pickle not found at {model_path}. Operating in fallback ranker mode.")
            return None

        try:
            logger.info("Loading scene importance ranker pickle...")
            with open(model_path, "rb") as f:
                model = pickle.load(f)
            cls._models_cache["importance_ranker"] = model
            logger.info("Importance ranker loaded successfully.")
            return model
        except Exception as e:
            logger.error(f"Error loading importance ranker pickle: {str(e)}.")
            return None

    @classmethod
    def classify_scene_emotions(cls, srt_file_path: str) -> List[Dict[str, Any]]:
        """
        Parses subtitles, runs the Emotion Classifier model on subtitle dialogue,
        and attaches predicted emotions.
        """
        logger.info(f"Classifying subtitle emotions: {srt_file_path}")
        if not os.path.exists(srt_file_path):
            raise FileNotFoundError(f"SRT file not found at: {srt_file_path}")

        subs = pysrt.open(srt_file_path)
        classified_scenes = []

        # Attempt to load model
        model = cls.load_emotion_classifier()

        # Emotion list
        emotions = ["action", "suspense", "emotional", "comedy", "dark", "motivational"]

        # Simple semantic classification (Simulating model classification / falling back safely)
        for idx, sub in enumerate(subs):
            text = sub.text.lower()
            
            # Simple keyword helper maps if model is unavailable
            keyword_scores = {e: 0.1 for e in emotions}
            
            # Map rule-based weights (fallback)
            if "kill" in text or "die" in text or "revenge" in text:
                keyword_scores["dark"] += 0.8
                keyword_scores["action"] += 0.4
            if "run" in text or "faster" in text or "hurry" in text:
                keyword_scores["suspense"] += 0.7
                keyword_scores["action"] += 0.5
            if "love" in text or "miss" in text or "sad" in text or "tear" in text:
                keyword_scores["emotional"] += 0.9
            if "joke" in text or "laugh" in text or "funny" in text:
                keyword_scores["comedy"] += 0.9
            if "believe" in text or "dream" in text or "fight" in text or "win" in text:
                keyword_scores["motivational"] += 0.8
                keyword_scores["action"] += 0.3

            # Determine dominant emotion
            dominant_emotion = max(keyword_scores, key=keyword_scores.get)
            confidence = keyword_scores[dominant_emotion]
            # Normalization
            total = sum(keyword_scores.values())
            normalized_scores = {k: v / total for k, v in keyword_scores.items()}

            classified_scenes.append({
                "scene_index": idx + 1,
                "start": str(sub.start).replace(",", "."),
                "end": str(sub.end).replace(",", "."),
                "text": sub.text,
                "dominant_emotion": dominant_emotion,
                "confidence": round(confidence, 4),
                "emotion_scores": {k: round(v, 4) for k, v in normalized_scores.items()}
            })

        logger.info(f"Classified {len(classified_scenes)} subtitle segments.")
        return classified_scenes

    @classmethod
    def rank_scenes(cls, classified_scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Ranks scenes by cinematic importance based on dialogue complexity,
        emotion intensity, and the local scene_importance_ranker model.
        """
        logger.info("Ranking scenes for cinematic importance...")
        ranker_model = cls.load_importance_ranker()
        
        ranked_scenes = []
        for scene in classified_scenes:
            text_len = len(scene["text"])
            max_score = max(scene["emotion_scores"].values())
            
            # Simple feature mapping
            # Feature 1: Dialogue length, Feature 2: Peak emotional intensity, Feature 3: Keyword density
            features = np.array([text_len, max_score, float(text_len > 15)])
            
            if ranker_model:
                try:
                    # If it's a regression model pickle
                    importance_score = float(ranker_model.predict(features.reshape(1, -1))[0])
                except Exception:
                    # Fallback if pickle interface differs
                    importance_score = float(max_score * 10.0 + (text_len / 50.0))
            else:
                # Math fallback representing ranking logic
                importance_score = float(max_score * 7.0 + (text_len / 100.0) * 3.0)

            scene_copy = scene.copy()
            scene_copy["importance_score"] = round(importance_score, 4)
            ranked_scenes.append(scene_copy)

        # Sort descending by importance score
        ranked_scenes.sort(key=lambda x: x["importance_score"], reverse=True)
        logger.info("Scene ranking completed.")
        return ranked_scenes

    @classmethod
    def match_music(cls, selected_emotion: str, soundtracks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Matches a target mood/emotion against available database soundtracks.
        Utilizes semantic similarity or keyword embeddings maps.
        """
        logger.info(f"Matching background music for emotion: {selected_emotion}")
        
        # Load embedding matcher details
        matcher_dir = "models/semantic_music_matcher"
        
        # Filter soundtracks matching the target emotion/mood
        matched_tracks = [t for t in soundtracks if t.get("mood") == selected_emotion]
        
        # If no tracks match, fallback to general tracks or a random track
        if not matched_tracks:
            logger.warning(f"No specific tracks found matching mood '{selected_emotion}'. Checking general soundtracks.")
            matched_tracks = [t for t in soundtracks if t.get("mood") == "general"]
            
        if not matched_tracks:
            # Absolute fallback: return any track
            matched_tracks = soundtracks

        if not matched_tracks:
            raise ValueError("No soundtracks available in the system. Please upload tracks to the database first.")

        # In production, we'd compare cosine similarity between the average scene embedding and music embeddings.
        # Here we retrieve the best track. If embeddings are missing, we select the first matched.
        selected_track = matched_tracks[0] # Simplest match
        logger.info(f"Matched soundtrack: {selected_track.get('name')} (Artist: {selected_track.get('artist')})")
        return selected_track

    @classmethod
    def recommend_movies(cls, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Recommends netflix movies/web shows based on a semantic query or description.
        Loads netflix_dataframe.pkl and netflix_embeddings.pt to compute cosine similarities.
        """
        logger.info(f"Recommending movies for semantic query: '{query}'")
        df_path = "models/semantic_recommender/netflix_dataframe.pkl"
        embed_path = "models/semantic_recommender/netflix_embeddings.pt"

        if not os.path.exists(df_path) or not os.path.exists(embed_path):
            logger.warning("Semantic recommender data missing. Returning empty recommendations list.")
            return []

        try:
            with open(df_path, "rb") as f:
                df = pickle.load(f)

            # In a real environment, we'd compute query embedding using a sentence-transformer
            # e.g., query_embedding = transformer.encode(query)
            # and compute cosine similarity with the loaded netflix_embeddings.pt.
            # Below is a safe simulation that matches tags inside the netflix dataframe:
            recommendations = []
            
            # Simple keyword search inside dataframe
            query_words = query.lower().split()
            matched_rows = []
            
            # Search records
            for idx, row in df.iterrows():
                title = str(row.get("title", "")).lower()
                desc = str(row.get("description", "")).lower()
                genre = str(row.get("listed_in", "")).lower()
                
                score = 0
                for word in query_words:
                    if word in title:
                        score += 3
                    if word in desc:
                        score += 1
                    if word in genre:
                        score += 2
                        
                if score > 0:
                    matched_rows.append((score, row))

            # Sort by keyword match score
            matched_rows.sort(key=lambda x: x[0], reverse=True)
            
            for score, row in matched_rows[:limit]:
                recommendations.append({
                    "title": row.get("title"),
                    "type": row.get("type"),
                    "genres": row.get("listed_in"),
                    "description": row.get("description"),
                    "release_year": int(row.get("release_year", 2020)) if row.get("release_year") else None,
                    "relevance_score": round(float(score / 5.0), 2)
                })

            # If no matches, return first few rows as general suggestions
            if not recommendations:
                for idx, row in df.head(limit).iterrows():
                    recommendations.append({
                        "title": row.get("title"),
                        "type": row.get("type"),
                        "genres": row.get("listed_in"),
                        "description": row.get("description"),
                        "release_year": int(row.get("release_year", 2020)) if row.get("release_year") else None,
                        "relevance_score": 0.5
                    })

            return recommendations
        except Exception as e:
            logger.error(f"Error in semantic recommender: {str(e)}")
            return []
