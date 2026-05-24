-- ========================================================
-- CINEREC AI - DATABASE MIGRATION & INITIALIZATION
-- ========================================================

-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- 1. USER PROFILES TABLE
-- Extends the default auth.users table in Supabase Auth
create table public.user_profiles (
    id uuid references auth.users on delete cascade primary key,
    full_name text,
    avatar_url text,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable RLS on User Profiles
alter table public.user_profiles enable row level security;

-- RLS Policies for user_profiles
create policy "Users can view their own profile." 
    on public.user_profiles for select 
    using (auth.uid() = id);

create policy "Users can update their own profile." 
    on public.user_profiles for update 
    using (auth.uid() = id);

-- Trigger to automatically create a user profile when a new user signs up in Supabase Auth
create or replace function public.handle_new_user()
returns trigger as $$
begin
    insert into public.user_profiles (id, full_name, avatar_url)
    values (
        new.id,
        coalesce(new.raw_user_meta_data->>'full_name', new.email),
        new.raw_user_meta_data->>'avatar_url'
    );
    return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
    after insert on auth.users
    for each row execute procedure public.handle_new_user();


-- 2. PROJECTS TABLE
create table public.projects (
    id uuid default gen_random_uuid() primary key,
    user_id uuid references public.user_profiles(id) on delete cascade not null,
    name text not null,
    description text,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable RLS on Projects
alter table public.projects enable row level security;

-- RLS Policies for projects
create policy "Users can perform all operations on their own projects."
    on public.projects for all
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);


-- 3. MOVIES TABLE
create table public.movies (
    id uuid default gen_random_uuid() primary key,
    project_id uuid references public.projects(id) on delete cascade not null,
    name text not null,
    video_storage_path text, -- Path in 'movies' storage bucket
    srt_storage_path text,   -- Path in 'movies' storage bucket
    duration_seconds double precision,
    status text default 'uploaded' check (status in ('uploaded', 'processing_subtitles', 'processed', 'failed')),
    metadata jsonb default '{}'::jsonb,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable RLS on Movies
alter table public.movies enable row level security;

-- RLS Policies for movies (via subquery checking project ownership)
create policy "Users can perform all operations on movies in their projects."
    on public.movies for all
    using (
        exists (
            select 1 from public.projects
            where projects.id = movies.project_id
            and projects.user_id = auth.uid()
        )
    );


-- 4. SOUNDTRACKS TABLE
create table public.soundtracks (
    id uuid default gen_random_uuid() primary key,
    name text not null,
    artist text,
    genre text,
    mood text not null check (mood in ('action', 'suspense', 'emotional', 'comedy', 'dark', 'motivational', 'general')),
    audio_storage_path text not null, -- Path in 'soundtracks' bucket
    duration_seconds double precision,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable RLS on Soundtracks
alter table public.soundtracks enable row level security;

-- RLS Policies for soundtracks
create policy "Authenticated users can read soundtracks."
    on public.soundtracks for select
    using (auth.role() = 'authenticated');

create policy "Admins can perform write operations on soundtracks."
    on public.soundtracks for all
    using (false) -- Bypassed by database service role key / server processes
    with check (false);


-- 5. REELS TABLE
create table public.reels (
    id uuid default gen_random_uuid() primary key,
    project_id uuid references public.projects(id) on delete cascade not null,
    movie_id uuid references public.movies(id) on delete cascade not null,
    soundtrack_id uuid references public.soundtracks(id) on delete set null,
    name text not null,
    selected_emotion text not null check (selected_emotion in ('action', 'suspense', 'emotional', 'comedy', 'dark', 'motivational')),
    target_duration_seconds integer default 60 not null,
    status text default 'queued' check (status in ('queued', 'processing_subtitles', 'analyzing_emotions', 'extracting_clips', 'matching_music', 'composing_reel', 'completed', 'failed')),
    error_message text,
    video_storage_path text, -- Path in 'reels' storage bucket
    metadata jsonb default '{}'::jsonb, -- Stores scene timestamps, rank lists, and matching indexes
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable RLS on Reels
alter table public.reels enable row level security;

-- RLS Policies for reels (via subquery checking project ownership)
create policy "Users can perform all operations on reels in their projects."
    on public.reels for all
    using (
        exists (
            select 1 from public.projects
            where projects.id = reels.project_id
            and projects.user_id = auth.uid()
        )
    );


-- ========================================================
-- AUTOMATION & HELPER INDICES
-- ========================================================

-- Speed up relational lookups
create index idx_projects_user_id on public.projects(user_id);
create index idx_movies_project_id on public.movies(project_id);
create index idx_reels_project_id on public.reels(project_id);
create index idx_reels_movie_id on public.reels(movie_id);
create index idx_reels_soundtrack_id on public.reels(soundtrack_id);
create index idx_soundtracks_mood on public.soundtracks(mood);

-- Trigger for auto updated_at timestamps
create or replace function update_modified_column()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger update_user_profiles_modtime
    before update on public.user_profiles
    for each row execute procedure update_modified_column();

create trigger update_projects_modtime
    before update on public.projects
    for each row execute procedure update_modified_column();

create trigger update_movies_modtime
    before update on public.movies
    for each row execute procedure update_modified_column();

create trigger update_reels_modtime
    before update on public.reels
    for each row execute procedure update_modified_column();
