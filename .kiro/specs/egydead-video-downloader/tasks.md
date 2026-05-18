# EgyDead Video Downloader - Tasks

## Task 1: Create Video Resolver Module
- **Status**: not_started
- **Description**: Create `api/video_resolver.py` with yt-dlp integration for extracting direct video URLs from embed players
- **Sub-tasks**:
  - [x] Implement `VideoResolver` class with yt-dlp backend
  - [x] Add `resolve()` async method for URL resolution
  - [x] Add `_select_best_format()` for quality selection
  - [x] Add `_fallback_resolve()` using streamlink
  - [x] Add caching for resolved URLs
  - [x] Handle errors gracefully

## Task 2: Add Resolve Embed Endpoint
- **Status**: not_started
- **Description**: Add `/api/resolve-embed` endpoint to extract direct video URLs from embed players
- **Sub-tasks**:
  - [x] Add `ResolveEmbedRequest` model
  - [x] Implement endpoint in `api/index.py`
  - [x] Return resolved video info (URL, quality, formats)

## Task 3: Add Download Endpoint
- **Status**: not_started
- **Description**: Add `/api/egydead/download` endpoint for direct video downloads
- **Sub-tasks**:
  - [x] Add `DownloadRequest` model
  - [x] Implement streaming download response
  - [x] Set proper Content-Disposition header for filename

## Task 4: Update Dependencies
- **Status**: not_started
- **Description**: Add yt-dlp and streamlink to requirements.txt
- **Sub-tasks**:
  - [ ] Add `yt-dlp>=2024.0.0`
  - [~] Add `streamlink>=6.0.0`

## Task 5: Update Frontend
- **Status**: not_started
- **Description**: Add download button and handlers to the frontend
- **Sub-tasks**:
  - [~] Add download button to video player UI in `app.js`
  - [~] Implement `downloadVideo()` function
  - [~] Add quality selection dropdown
  - [~] Show download progress/loading state

## Task 6: Test Integration
- **Status**: not_started
- **Description**: Test the download feature with various embed hosts
- **Sub-tasks**:
  - [~] Test uqload resolution
  - [~] Test doodstream resolution
  - [~] Test streamtape resolution
  - [~] Test voe.sx resolution
  - [~] Test download streaming
  - [~] Test ad-blocking (no popups/redirects)
