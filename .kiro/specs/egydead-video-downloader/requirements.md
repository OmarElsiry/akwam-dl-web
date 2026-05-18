# EgyDead Video Downloader - Requirements

## Problem Statement

Users cannot download videos from EgyDead embed servers. When streaming through embed players, they encounter:
- Multiple popup ads
- Redirect spam
- Annoying overlays during playback
- No direct download option

## Goals

1. Enable video downloading from EgyDead embed servers
2. Eliminate ads during streaming/downloading
3. Provide quality selection when multiple formats are available

## Functional Requirements

### FR-1: Video Resolution
**Given** an embed player URL from EgyDead (uqload, doodstream, streamtape, etc.)
**When** the user requests to download
**Then** the system extracts the direct video URL

### FR-2: Ad-Free Download
**Given** a resolved video URL
**When** the user downloads the video
**Then** no ads are shown (server-side extraction bypasses ad scripts)

### FR-3: Quality Selection
**Given** a video with multiple quality options
**When** the user views download options
**Then** they can select preferred quality (720p, 1080p, etc.)

### FR-4: Format Support
**Given** various video formats (MP4, MKV, M3U8/HLS)
**When** downloading or streaming
**Then** all common formats are handled correctly

## Non-Functional Requirements

### NFR-1: Performance
- Video resolution should complete within 5 seconds for most embed URLs
- Download speed should match the server's maximum throughput

### NFR-2: Reliability
- Fallback mechanisms for failed resolutions
- Cache resolved URLs to avoid repeated extraction

### NFR-3: Security
- Validate URLs to prevent SSRF attacks
- Block access to internal network resources

## Constraints

1. Must work with existing FastAPI backend
2. Must not require user-side ad-blockers
3. Must support at least the embed hosts currently recognized by EgyDeadAPI

## Out of Scope

- Downloading from paid/premium content
- Bulk episode downloads (already handled by `/api/bulk-resolve`)
- Subtitle extraction
