/* ========================================================
   CINEREC AI - SINGLE PAGE APPLICATION CORE CLIENT DRIVER
   ======================================================== */

const BACKEND_API_URL = "http://127.0.0.1:8000/api/v1";

// Global Application State
let appState = {
    user: null,
    authToken: null,
    projects: [],
    activeProjectId: null,
    movies: [],
    reels: [],
    activePollInterval: null,
    supabaseClient: null
};

// 1. CONSTRUCTORS & DOM INITIALIZATION
document.addEventListener("DOMContentLoaded", async () => {
    await fetchAuthConfig();
    initApp();
    setupEventListeners();
});

async function fetchAuthConfig() {
    try {
        const response = await fetch(`${BACKEND_API_URL}/auth/config`);
        if (!response.ok) throw new Error("Failed to fetch config");
        const data = await response.json();
        if (data.supabase_url && data.supabase_anon_key) {
            appState.supabaseClient = supabase.createClient(data.supabase_url, data.supabase_anon_key);
        }
    } catch (e) {
        console.error("Failed to initialize Supabase client:", e);
    }
}

async function autoLoginLocalDeveloper() {
    try {
        console.log("Attempting automatic local developer authentication bypass...");
        const response = await fetch(`${BACKEND_API_URL}/auth/bypass`, {
            method: "POST"
        });
        if (response.ok) {
            const data = await response.json();
            const token = data.access_token;
            const email = data.email;
            
            localStorage.setItem("cinerec_token", token);
            localStorage.setItem("cinerec_user_email", email);
            
            appState.authToken = token;
            appState.user = { email };
            
            document.getElementById("user-display").innerText = email;
            document.getElementById("auth-gateway-btn").innerText = "Log Out";
            
            console.log("Local developer automatically authenticated!");
            await loadProjects();
            return true;
        }
    } catch (e) {
        console.error("Automatic local developer login failed:", e);
    }
    return false;
}

async function initApp() {
    // Check local storage for cached JWT token
    const cachedToken = localStorage.getItem("cinerec_token");
    const cachedUserEmail = localStorage.getItem("cinerec_user_email");
    
    if (cachedToken) {
        appState.authToken = cachedToken;
        appState.user = { email: cachedUserEmail || "Authenticated User" };
        document.getElementById("user-display").innerText = appState.user.email;
        document.getElementById("auth-gateway-btn").innerText = "Log Out";
        
        // Load projects catalog
        loadProjects();
    } else {
        openAuthModal();
    }
}

// 2. AUTHENTICATION & SUPABASE INTEGRATIONS
function openAuthModal() {
    document.getElementById("auth-modal").classList.add("active");
}

function closeAuthModal() {
    document.getElementById("auth-modal").classList.remove("active");
}

function switchAuthTab(tabId) {
    document.querySelectorAll(".auth-modal-tab-content").forEach(el => el.classList.add("hidden"));
    document.querySelectorAll("#auth-modal .tab-btn").forEach(el => el.classList.remove("active"));
    
    if (tabId === "demo") {
        document.getElementById("auth-tab-demo").classList.remove("hidden");
    } else if (tabId === "token") {
        document.getElementById("auth-tab-token").classList.remove("hidden");
    } else if (tabId === "email") {
        document.getElementById("auth-tab-email").classList.remove("hidden");
    }
    event.target.classList.add("active");
}

// REST API Request Wrapper with automatic Bearer Token injection
async function apiRequest(endpoint, options = {}) {
    const headers = {
        "Content-Type": "application/json",
        ...(appState.authToken && { "Authorization": `Bearer ${appState.authToken}` }),
        ...options.headers
    };
    
    const response = await fetch(`${BACKEND_API_URL}${endpoint}`, {
        ...options,
        headers
    });
    
    if (response.status === 401) {
        // Auth failed or token expired
        logout();
        openAuthModal();
        throw new Error("Session expired. Please log in again.");
    }
    
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "API request failed");
    }
    
    if (response.status === 204) return null;
    return response.json();
}

function logout() {
    localStorage.removeItem("cinerec_token");
    localStorage.removeItem("cinerec_user_email");
    appState.authToken = null;
    appState.user = null;
    appState.projects = [];
    appState.activeProjectId = null;
    
    document.getElementById("user-display").innerText = "Not Authenticated";
    document.getElementById("auth-gateway-btn").innerText = "Authentication";
    
    document.getElementById("project-selector").innerHTML = '<option value="">-- No Projects Found --</option>';
    document.getElementById("movies-catalog-grid").innerHTML = '<p style="color: var(--text-muted); font-size: 0.9rem; text-align: center; grid-column: 1/-1; padding: 2rem 0;">No active project.</p>';
    document.getElementById("reels-catalog-list").innerHTML = '<p style="color: var(--text-muted); font-size: 0.85rem; text-align: center; margin-top: 3rem;">No active project.</p>';
}

// 3. EVENT BINDING LAYERS
function setupEventListeners() {
    // Auth trigger
    document.getElementById("auth-gateway-btn").addEventListener("click", () => {
        if (appState.authToken) {
            logout();
            openAuthModal();
        } else {
            openAuthModal();
        }
    });

    // JWT token paste authenticate
    document.getElementById("btn-save-jwt").addEventListener("click", () => {
        const token = document.getElementById("auth-jwt-token").value.trim();
        if (!token) return alert("Please paste a valid JWT token.");
        
        // Simple client side parse to read email claim
        let email = "Authenticated Session";
        try {
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const payload = JSON.parse(window.atob(base64));
            if (payload.email) email = payload.email;
        } catch(e) {}
        
        localStorage.setItem("cinerec_token", token);
        localStorage.setItem("cinerec_user_email", email);
        
        appState.authToken = token;
        appState.user = { email };
        
        document.getElementById("user-display").innerText = email;
        document.getElementById("auth-gateway-btn").innerText = "Log Out";
        closeAuthModal();
        
        loadProjects();
    });

    // Demo Login button click
    document.getElementById("btn-supabase-demo").addEventListener("click", async () => {
        const btn = document.getElementById("btn-supabase-demo");
        btn.disabled = true;
        btn.innerText = "Launching Demo...";
        try {
            // Directly fetch local signed bypass token from FastAPI
            const response = await fetch(`${BACKEND_API_URL}/auth/bypass`, {
                method: "POST"
            });
            if (!response.ok) throw new Error("Failed to contact FastAPI authentication bypass gateway.");
            const data = await response.json();
            
            const token = data.access_token;
            localStorage.setItem("cinerec_token", token);
            localStorage.setItem("cinerec_user_email", "arav@gmail.com");
            
            appState.authToken = token;
            appState.user = { email: "arav@gmail.com" };
            
            document.getElementById("user-display").innerText = "arav@gmail.com";
            document.getElementById("auth-gateway-btn").innerText = "Log Out";
            
            closeAuthModal();
            alert("Logged in as demo user arav@gmail.com successfully!");
            await loadProjects();
        } catch (e) {
            alert(`Demo login failed: ${e.message}`);
        } finally {
            btn.disabled = false;
            btn.innerText = "Launch Demo Session";
        }
    });

    // Sign In with email and password
    document.getElementById("btn-supabase-signin").addEventListener("click", async () => {
        const email = document.getElementById("auth-email").value.trim();
        const password = document.getElementById("auth-password").value;
        
        if (!email || !password) return alert("Please fill in both email and password.");
        
        const btn = document.getElementById("btn-supabase-signin");
        btn.disabled = true;
        btn.innerText = "Signing In...";
        
        try {
            // Check if it is the local demo developer login
            if (email === "arav@gmail.com" && password === "arav") {
                const response = await fetch(`${BACKEND_API_URL}/auth/bypass`, {
                    method: "POST"
                });
                if (!response.ok) throw new Error("Failed to authenticate demo session");
                const data = await response.json();
                
                const token = data.access_token;
                localStorage.setItem("cinerec_token", token);
                localStorage.setItem("cinerec_user_email", "arav@gmail.com");
                
                appState.authToken = token;
                appState.user = { email: "arav@gmail.com" };
                
                document.getElementById("user-display").innerText = "arav@gmail.com";
                document.getElementById("auth-gateway-btn").innerText = "Log Out";
                closeAuthModal();
                
                alert("Logged in as arav@gmail.com successfully!");
                await loadProjects();
                return;
            }
            
            if (!appState.supabaseClient) {
                return alert("Supabase auth client not initialized. Check backend connection.");
            }
            
            const { data, error } = await appState.supabaseClient.auth.signInWithPassword({
                email: email,
                password: password,
            });
            
            if (error) throw error;
            
            const token = data.session.access_token;
            localStorage.setItem("cinerec_token", token);
            localStorage.setItem("cinerec_user_email", email);
            
            appState.authToken = token;
            appState.user = { email };
            
            document.getElementById("user-display").innerText = email;
            document.getElementById("auth-gateway-btn").innerText = "Log Out";
            closeAuthModal();
            
            alert("Signed in successfully!");
            await loadProjects();
        } catch (err) {
            alert(`Sign in failed: ${err.message}`);
        } finally {
            btn.disabled = false;
            btn.innerText = "Log In";
        }
    });

    // Sign Up with email and password
    document.getElementById("btn-supabase-signup").addEventListener("click", async () => {
        const email = document.getElementById("auth-email").value.trim();
        const password = document.getElementById("auth-password").value;
        
        if (!email || !password) return alert("Please fill in both email and password.");
        if (password.length < 6) return alert("Password must be at least 6 characters.");
        if (!appState.supabaseClient) {
            return alert("Supabase auth client not initialized. Check backend connection.");
        }
        
        const btn = document.getElementById("btn-supabase-signup");
        btn.disabled = true;
        btn.innerText = "Signing Up...";
        
        try {
            const { data, error } = await appState.supabaseClient.auth.signUp({
                email: email,
                password: password,
            });
            
            if (error) throw error;
            
            // Check if confirmation is required
            if (data.session) {
                const token = data.session.access_token;
                localStorage.setItem("cinerec_token", token);
                localStorage.setItem("cinerec_user_email", email);
                
                appState.authToken = token;
                appState.user = { email };
                
                document.getElementById("user-display").innerText = email;
                document.getElementById("auth-gateway-btn").innerText = "Log Out";
                closeAuthModal();
                
                alert("Sign up successful and logged in!");
                await loadProjects();
            } else {
                alert("Sign up successful! Please check your email for confirmation link.");
            }
        } catch (err) {
            alert(`Sign up failed: ${err.message}`);
        } finally {
            btn.disabled = false;
            btn.innerText = "Sign Up";
        }
    });

    // Switch tabs
    document.querySelectorAll(".tab-btn[data-tab]").forEach(btn => {
        btn.addEventListener("click", (e) => {
            const tabId = e.target.getAttribute("data-tab");
            
            document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
            
            e.target.classList.add("active");
            document.getElementById(tabId).classList.add("active");
        });
    });

    // Project selection
    document.getElementById("project-selector").addEventListener("change", (e) => {
        const projId = e.target.value;
        if (projId) {
            appState.activeProjectId = projId;
            loadMovies();
            loadReels();
        }
    });

    // Create project
    document.getElementById("btn-new-project").addEventListener("click", async () => {
        const name = prompt("Enter Project Name:");
        if (!name) return;
        
        try {
            const res = await apiRequest("/projects/", {
                method: "POST",
                body: JSON.stringify({ name, description: "CineRec AI Production Space" })
            });
            alert(`Project '${res.name}' created successfully.`);
            await loadProjects();
            // Auto select newly created project
            document.getElementById("project-selector").value = res.id;
            appState.activeProjectId = res.id;
            loadMovies();
            loadReels();
        } catch (err) {
            alert(`Project creation failed: ${err.message}`);
        }
    });

    // Vibe match recommendations search
    document.getElementById("btn-search-recs").addEventListener("click", async () => {
        const query = document.getElementById("rec-search-query").value.trim();
        if (!query) return alert("Please type a description of the movie vibe.");
        
        const container = document.getElementById("rec-results-container");
        container.innerHTML = '<div class="text-center" style="padding: 2rem 0;"><div class="spinner" style="margin: 0 auto 0.8rem;"></div><span style="color: var(--text-muted); font-size: 0.8rem;">Querying vector space...</span></div>';
        
        try {
            const recs = await apiRequest(`/reels/search/recommendations?query=${encodeURIComponent(query)}`);
            container.innerHTML = "";
            
            if (!recs || recs.length === 0) {
                container.innerHTML = '<p style="color: var(--text-muted); font-size: 0.8rem; text-align: center; margin-top: 2rem;">No matching films found.</p>';
                return;
            }
            
            recs.forEach(rec => {
                const card = document.createElement("div");
                card.className = "rec-card";
                card.innerHTML = `
                    <div class="rec-header">
                        <span class="rec-title">${rec.title}</span>
                        <span class="rec-match">${Math.round(rec.relevance_score * 100)}% Match</span>
                    </div>
                    <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.4rem;">
                        ${rec.type} • ${rec.release_year || 'N/A'} • ${rec.genres}
                    </div>
                    <p class="rec-description">${rec.description}</p>
                `;
                container.appendChild(card);
            });
        } catch (err) {
            container.innerHTML = `<p style="color: var(--error); font-size: 0.8rem; text-align: center; margin-top: 2rem;">Error: ${err.message}</p>`;
        }
    });

    // 4. MOVIE FILE UPLOAD TRIGGERS (DIRECT MOCK CHUNKED)
    let uploadFlowData = null;
    let videoUploaded = false;
    let srtUploaded = false;

    document.getElementById("btn-register-upload").addEventListener("click", async () => {
        if (!appState.activeProjectId) return alert("Please select or create a project first.");
        const name = document.getElementById("movie-name").value.trim();
        if (!name) return alert("Please provide a movie title.");
        
        try {
            uploadFlowData = await apiRequest("/movies/upload", {
                method: "POST",
                body: JSON.stringify({ project_id: appState.activeProjectId, name })
            });
            
            // Show action panel
            document.getElementById("upload-action-panel").classList.remove("hidden");
            document.getElementById("upload-status-title").innerText = `⏳ Pipeline for: ${name}`;
            
            // Reset upload states
            videoUploaded = false;
            srtUploaded = false;
            updateUploadBadge("video-upload-badge", "queued", "Waiting");
            updateUploadBadge("srt-upload-badge", "queued", "Waiting");
            document.getElementById("btn-confirm-movie-processed").disabled = true;
            
        } catch(err) {
            alert(`Failed to initialize upload flow: ${err.message}`);
        }
    });

    // Simulate video S3 direct upload
    document.getElementById("btn-upload-video-mock").addEventListener("click", () => {
        if (!uploadFlowData) return;
        const btn = document.getElementById("btn-upload-video-mock");
        const badge = document.getElementById("video-upload-badge");
        
        btn.disabled = true;
        updateUploadBadge("video-upload-badge", "processing", "Uploading...");
        
        // Simulate high-speed file transfer
        let progress = 0;
        const iv = setInterval(() => {
            progress += 25;
            btn.innerText = `Transferring: ${progress}%`;
            if (progress >= 100) {
                clearInterval(iv);
                videoUploaded = true;
                btn.innerText = "Simulated Upload Complete";
                updateUploadBadge("video-upload-badge", "completed", "S3 Secure Link Ready");
                checkUploadsFinished();
            }
        }, 400);
    });

    // Simulate subtitles SRT S3 direct upload
    document.getElementById("btn-upload-srt-mock").addEventListener("click", () => {
        if (!uploadFlowData) return;
        const btn = document.getElementById("btn-upload-srt-mock");
        const badge = document.getElementById("srt-upload-badge");
        
        btn.disabled = true;
        updateUploadBadge("srt-upload-badge", "processing", "Uploading...");
        
        // Simulate srt upload
        setTimeout(() => {
            srtUploaded = true;
            btn.innerText = "Simulated Upload Complete";
            updateUploadBadge("srt-upload-badge", "completed", "S3 Secure Link Ready");
            checkUploadsFinished();
        }, 1000);
    });

    function checkUploadsFinished() {
        if (videoUploaded && srtUploaded) {
            document.getElementById("btn-confirm-movie-processed").removeAttribute("disabled");
        }
    }

    function updateUploadBadge(id, state, text) {
        const el = document.getElementById(id);
        el.className = `status-badge ${state}`;
        el.innerText = text;
    }

    // Confirm movie upload processing
    document.getElementById("btn-confirm-movie-processed").addEventListener("click", async () => {
        if (!uploadFlowData) return;
        const btn = document.getElementById("btn-confirm-movie-processed");
        btn.disabled = true;
        btn.innerText = "Processing Metadata on FastAPI Gateway...";
        
        try {
            await apiRequest(`/movies/${uploadFlowData.movie_id}/confirm-processed`, {
                method: "POST"
            });
            alert("Movie upload verified and processed successfully.");
            
            // Clean up panel
            document.getElementById("upload-action-panel").classList.add("hidden");
            document.getElementById("movie-name").value = "";
            document.getElementById("btn-upload-video-mock").disabled = false;
            document.getElementById("btn-upload-video-mock").innerText = "Simulate Video Upload (Direct-to-S3)";
            document.getElementById("btn-upload-srt-mock").disabled = false;
            document.getElementById("btn-upload-srt-mock").innerText = "Simulate Subtitle Upload (Direct-to-S3)";
            
            // Reload movies
            loadMovies();
        } catch (err) {
            alert(`Confirm processing failed: ${err.message}`);
            btn.disabled = false;
            btn.innerText = "Confirm Upload & Process Metadata";
        }
    });

    // 5. REEL GENERATION PIPELINE DISPATCH
    document.getElementById("btn-trigger-generation").addEventListener("click", async () => {
        if (!appState.activeProjectId) return alert("Please select a project first.");
        
        const name = document.getElementById("reel-compose-name").value.trim();
        const movieId = document.getElementById("reel-movie-selector").value;
        const emotion = document.getElementById("reel-emotion-selector").value;
        const duration = parseInt(document.getElementById("reel-duration").value);
        
        if (!name) return alert("Provide an export name for this reel.");
        if (!movieId) return alert("Select a target movie source.");
        
        try {
            const res = await apiRequest("/reels/generate", {
                method: "POST",
                body: JSON.stringify({
                    project_id: appState.activeProjectId,
                    movie_id: movieId,
                    name: name,
                    selected_emotion: emotion,
                    target_duration_seconds: duration
                })
            });
            
            // Display tracking panel
            document.getElementById("composition-progress-panel").classList.remove("hidden");
            startReelStatusPolling(res.id);
            
        } catch(err) {
            alert(`Worker dispatch failed: ${err.message}`);
        }
    });
}

// 4. GET DATA CATALOGS
async function loadProjects() {
    try {
        const projs = await apiRequest("/projects/");
        appState.projects = projs;
        
        const selector = document.getElementById("project-selector");
        selector.innerHTML = "";
        
        if (projs.length === 0) {
            selector.innerHTML = '<option value="">-- No Projects Found --</option>';
            return;
        }
        
        projs.forEach(p => {
            const opt = document.createElement("option");
            opt.value = p.id;
            opt.innerText = p.name;
            selector.appendChild(opt);
        });
        
        // Auto select first
        appState.activeProjectId = projs[0].id;
        loadMovies();
        loadReels();
    } catch (err) {
        console.error(err.message);
    }
}

async function loadMovies() {
    if (!appState.activeProjectId) return;
    
    try {
        const list = await apiRequest(`/movies/project/${appState.activeProjectId}`);
        appState.movies = list;
        
        // Update selectors
        const reelMovieSelector = document.getElementById("reel-movie-selector");
        reelMovieSelector.innerHTML = '<option value="">-- Select Movie --</option>';
        
        // Update catalog grids
        const grid = document.getElementById("movies-catalog-grid");
        grid.innerHTML = "";
        
        const processedMovies = list.filter(m => m.status === "processed");
        processedMovies.forEach(m => {
            const opt = document.createElement("option");
            opt.value = m.id;
            opt.innerText = m.name;
            reelMovieSelector.appendChild(opt);
        });
        
        if (list.length === 0) {
            grid.innerHTML = '<p style="color: var(--text-muted); font-size: 0.9rem; text-align: center; grid-column: 1/-1; padding: 2rem 0;">No movies registered in this project.</p>';
            return;
        }
        
        list.forEach(m => {
            const card = document.createElement("div");
            card.className = "asset-card";
            card.innerHTML = `
                <div>
                    <h3>${m.name}</h3>
                    <p style="font-size: 0.78rem; color: var(--text-muted); margin-top: 4px;">ID: ${m.id.substring(0,8)}...</p>
                </div>
                <div class="asset-card-meta">
                    <span class="status-badge ${m.status === 'processed' ? 'completed' : 'queued'}">${m.status}</span>
                    <span>${m.metadata.video_file_size ? Math.round(m.metadata.video_file_size / 1024 / 1024) + ' MB' : 'Pending'}</span>
                </div>
            `;
            grid.appendChild(card);
        });
    } catch (err) {
        console.error(err.message);
    }
}

async function loadReels() {
    if (!appState.activeProjectId) return;
    
    try {
        const list = await apiRequest(`/reels/project/${appState.activeProjectId}`);
        appState.reels = list;
        
        const container = document.getElementById("reels-catalog-list");
        container.innerHTML = "";
        
        if (list.length === 0) {
            container.innerHTML = '<p style="color: var(--text-muted); font-size: 0.85rem; text-align: center; margin-top: 3rem;">No reels generated in this project.</p>';
            return;
        }
        
        list.forEach(r => {
            const card = document.createElement("div");
            card.className = "asset-card";
            card.style.height = "auto";
            card.style.flexDirection = "column";
            card.style.gap = "0.5rem";
            card.innerHTML = `
                <div>
                    <h3 style="font-size: 1rem; margin-bottom: 2px;">${r.name}</h3>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">Mood: <b>${r.selected_emotion}</b> • Length: ${r.target_duration_seconds}s</div>
                </div>
                <div class="asset-card-meta" style="margin-top: 0.5rem;">
                    <span class="status-badge ${r.status === 'completed' ? 'completed' : r.status === 'failed' ? 'failed' : 'processing'}">${r.status}</span>
                    ${r.status === 'completed' ? `<button class="btn btn-secondary btn-sm" onclick="playReel('${r.id}')" style="padding: 3px 8px; font-size: 0.75rem;">Play Reel</button>` : ''}
                </div>
            `;
            container.appendChild(card);
        });
    } catch (err) {
        console.error(err.message);
    }
}

// 5. WORKER STATUS POLLING LOOP
function startReelStatusPolling(reelId) {
    if (appState.activePollInterval) clearInterval(appState.activePollInterval);
    
    const stageLabel = document.getElementById("comp-stage-label");
    const badge = document.getElementById("comp-status-badge");
    const progressBar = document.getElementById("comp-progress-bar");
    const progressDesc = document.getElementById("comp-progress-desc");
    
    appState.activePollInterval = setInterval(async () => {
        try {
            const res = await apiRequest(`/reels/${reelId}/status`);
            
            const state = res.status;
            const progress = res.progress_percentage;
            
            // Update UI components
            badge.innerText = state;
            badge.className = `status-badge ${state === 'completed' ? 'completed' : state === 'failed' ? 'failed' : 'processing'}`;
            progressBar.style.width = `${progress}%`;
            
            // Custom messages for worker levels
            const labels = {
                "queued": "Enqueued in Celery broker queue...",
                "processing_subtitles": "Pipeline step 1: Parsing subtitles SRT transcript...",
                "analyzing_emotions": "Pipeline step 2: Running Transformers Emotion Classifiers & Importance Ranker...",
                "extracting_clips": "Pipeline step 3: Splitting movie files into scene clips using FFmpeg...",
                "matching_music": "Pipeline step 4: Running NLP Music embeddings matcher...",
                "composing_reel": "Pipeline step 5: Sticking cuts & soundtracks via MoviePy rendering...",
                "completed": "Reel composition succeeded! Exporting pre-signed URL...",
                "failed": "Worker process crashed."
            };
            
            stageLabel.innerText = labels[state] || "Running worker...";
            progressDesc.innerText = `Completed: ${progress}%. Task reference ID: ${reelId}`;
            
            if (state === "completed") {
                clearInterval(appState.activePollInterval);
                alert("Worker pipeline finished successfully!");
                document.getElementById("composition-progress-panel").classList.add("hidden");
                
                // Reload list
                await loadReels();
                
                // Automatically route player
                playReel(reelId);
            } else if (state === "failed") {
                clearInterval(appState.activePollInterval);
                alert(`Reel generation failed: ${res.error_message}`);
                document.getElementById("composition-progress-panel").classList.add("hidden");
                loadReels();
            }
        } catch (err) {
            console.error(err.message);
            clearInterval(appState.activePollInterval);
        }
    }, 2000);
}

// 6. VIDEO PLAYBACK CONTROLLER
async function playReel(reelId) {
    try {
        const res = await apiRequest(`/reels/${reelId}/status`);
        
        if (res.status !== "completed") {
            return alert("This reel is still compiling. Please wait for completion.");
        }
        
        const reelDetails = await apiRequest(`/reels/${reelId}`);
        
        // Set tab active
        document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
        document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
        
        document.querySelector('.tab-btn[data-tab="tab-player"]').classList.add("active");
        document.getElementById("tab-player").classList.add("active");
        
        // Update Player elements
        document.getElementById("playing-reel-title").innerText = reelDetails.name;
        document.getElementById("playing-reel-desc").innerText = `Mood: ${reelDetails.selected_emotion} • Duration: ${reelDetails.target_duration_seconds}s • Source ID: ${reelDetails.movie_id}`;
        
        const player = document.getElementById("reel-video-player");
        player.src = res.download_url;
        player.load();
        player.play().catch(e => {
            console.log("Auto play prevented, waiting for user click interaction.");
        });
        
    } catch(err) {
        alert(`Failed to load reel for playback: ${err.message}`);
    }
}

// Globally bind playing helper so click callbacks inside dynamic HTML work
window.playReel = playReel;
window.closeAuthModal = closeAuthModal;
window.switchAuthTab = switchAuthTab;
