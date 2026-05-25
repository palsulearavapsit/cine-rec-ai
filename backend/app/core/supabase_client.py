import uuid
from datetime import datetime
from supabase import Client

class MockStorageBucket:
    def get_metadata(self, path):
        return {
            "size": 15240294,
            "mime_type": "video/mp4"
        }

    def remove(self, paths):
        return []

    def create_signed_upload_url(self, path):
        return {
            "signedUrl": f"http://localhost:8000/api/v1/movies/mock-upload?path={path}"
        }

    def create_signed_url(self, path, expires_in):
        # Always serve the local movie.mp4 to play the uploaded file in the browser
        return {
            "signedURL": "/movie.mp4"
        }

    def download(self, remote_path):
        return b"mock-file-content"

    def upload(self, path, file, file_options=None):
        return []

class MockStorage:
    def from_(self, bucket_name):
        return MockStorageBucket()

    def list_buckets(self):
        class MockBucket:
            def __init__(self, name):
                self.name = name
        return [MockBucket("movies"), MockBucket("extracted-clips"), MockBucket("soundtracks"), MockBucket("reels")]

    def create_bucket(self, *args, **kwargs):
        return []

class MockQueryBuilder:
    def __init__(self, table_name, data_store):
        self.table_name = table_name
        self.data_store = data_store
        self.filters = []
        self.single_flag = False
        self.order_field = None
        self.order_desc = False

    def select(self, *args, **kwargs):
        return self

    def order(self, field, desc=False, *args, **kwargs):
        self.order_field = field
        self.order_desc = desc
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def single(self):
        self.single_flag = True
        return self

    def execute(self):
        items = self.data_store.get(self.table_name, [])
        filtered = []
        for item in items:
            match = True
            for field, val in self.filters:
                if str(item.get(field)) != str(val):
                    match = False
                    break
            if match:
                filtered.append(item)

        if self.order_field:
            # Sort with secondary sort on created_at or name if field doesn't exist
            filtered.sort(key=lambda x: x.get(self.order_field, ""), reverse=self.order_desc)

        class MockResponse:
            def __init__(self, data):
                self._data = data
            @property
            def data(self):
                return self._data

        if self.single_flag:
            res_data = filtered[0] if filtered else None
        else:
            res_data = filtered

        return MockResponse(res_data)

    def insert(self, data):
        if isinstance(data, dict):
            new_item = {"id": str(uuid.uuid4()), "created_at": datetime.utcnow().isoformat(), **data}
            self.data_store.setdefault(self.table_name, []).append(new_item)
            return MockInsertResponse([new_item])
        elif isinstance(data, list):
            new_items = []
            for d in data:
                new_item = {"id": str(uuid.uuid4()), "created_at": datetime.utcnow().isoformat(), **d}
                self.data_store.setdefault(self.table_name, []).append(new_item)
                new_items.append(new_item)
            return MockInsertResponse(new_items)
        return MockInsertResponse([])

    def update(self, update_data):
        items = self.data_store.get(self.table_name, [])
        updated_items = []
        for item in items:
            match = True
            for field, val in self.filters:
                if str(item.get(field)) != str(val):
                    match = False
                    break
            if match:
                item.update(update_data)
                updated_items.append(item)
        return MockInsertResponse(updated_items)

    def delete(self):
        items = self.data_store.get(self.table_name, [])
        remaining = []
        deleted = []
        for item in items:
            match = True
            for field, val in self.filters:
                if str(item.get(field)) != str(val):
                    match = False
                    break
            if match:
                deleted.append(item)
            else:
                remaining.append(item)
        self.data_store[self.table_name] = remaining
        return MockInsertResponse(deleted)

class MockInsertResponse:
    def __init__(self, data):
        self._data = data
    @property
    def data(self):
        return self._data

class MockClient:
    def __init__(self):
        self.storage = MockStorage()
        self.postgrest = self
        
        # Prepopulate with high-quality database mockup records for immediate rich demo load
        self.data_store = {
            "projects": [
                {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "name": "CineRec AI Demo Workspace",
                    "description": "Premium showcase workspace for cinematic movie processing.",
                    "user_id": "00000000-0000-0000-0000-000000000000",
                    "created_at": datetime.utcnow().isoformat()
                },
                {
                    "id": "22222222-2222-2222-2222-222222222222",
                    "name": "Marvel Trailers Compositor",
                    "description": "Production space for action trailer emotion cuts.",
                    "user_id": "00000000-0000-0000-0000-000000000000",
                    "created_at": datetime.utcnow().isoformat()
                }
            ],
            "movies": [
                {
                    "id": "33333333-3333-3333-3333-333333333333",
                    "project_id": "11111111-1111-1111-1111-111111111111",
                    "name": "Interstellar (2014) - Wormhole Scene",
                    "status": "processed",
                    "video_storage_path": "11111111-1111-1111-1111-111111111111/33333333-3333-3333-3333-333333333333/movie.mp4",
                    "srt_storage_path": "11111111-1111-1111-1111-111111111111/33333333-3333-3333-3333-333333333333/subtitles.srt",
                    "metadata": {
                        "video_file_size": 15240294,
                        "srt_file_size": 4204,
                        "mime_type": "video/mp4"
                    },
                    "created_at": datetime.utcnow().isoformat()
                }
            ],
            "reels": [
                {
                    "id": "55555555-5555-5555-5555-555555555555",
                    "project_id": "11111111-1111-1111-1111-111111111111",
                    "movie_id": "33333333-3333-3333-3333-333333333333",
                    "name": "Interstellar - Epic Suspense Cut",
                    "selected_emotion": "suspense",
                    "target_duration_seconds": 60,
                    "status": "completed",
                    "video_storage_path": "reels/epic_suspense_cut.mp4",
                    "metadata": {},
                    "created_at": datetime.utcnow().isoformat()
                }
            ],
            "user_profiles": [
                {
                    "id": "00000000-0000-0000-0000-000000000000",
                    "email": "arav@gmail.com",
                    "full_name": "Arav Palsule",
                    "avatar_url": None,
                    "created_at": datetime.utcnow().isoformat()
                }
            ]
        }

    def table(self, table_name):
        return MockQueryBuilder(table_name, self.data_store)

    def auth(self, *args, **kwargs):
        return self

# Shared Mock client instance
_mock_client_instance = MockClient()

supabase_client: Client = _mock_client_instance
supabase_admin_client: Client = _mock_client_instance

def get_supabase_user_client(access_token: str) -> Client:
    """Returns the mock client scoped to the demo developer privileges."""
    return _mock_client_instance
