# EgyDead Downloader - Test Report

## Overview
This report documents the manual verification of the `egydead_dl.py` script. The script was updated to remove Playwright dependencies and now functions as a lightweight CLI tool for extracting download links.

**Test Date:** 2025-11-26
**Tester:** Antigravity Agent (via Browser Subagent)

## Test Case 1: Series Episode Download
**Objective:** Verify extraction and resolution of a series episode link.

*   **Input:** `https://egydead.skin/season/%d9%83%d8%b1%d8%aa%d9%88%d9%86-avatar-legend-korra-%d9%85%d9%88%d8%b3%d9%85-1-%d9%85%d8%aa%d8%b1%d8%ac%d9%85-%d9%83%d8%a7%d9%85%d9%84-%d8%a7%d9%88/`
*   **Selection:** Episode 12
*   **Extracted Link (DoodStream):** `https://dsvplay.com/d/fp1ka0v34kzf`
*   **Browser Verification:**
    *   Navigated to DoodStream URL.
    *   Clicked "Download Now" -> "High quality" -> "Download file".
    *   **Result:** SUCCESS.
    *   **Final Download URL:** `https://lo679vd.cloudatacdn.com/u5kjzlsnvte3sdgge4raomagde3fdojemiuh6z2chgjcr5rvqwfyadcd74bq/Avatar.The.Legend.of.Korra.S01E12.EgyDead.CoM.mp4?token=3r61k9b9q0ex3ko5usa5hqar&expiry=1764142096666`

## Test Case 2: Movie Download
**Objective:** Verify extraction and resolution of a movie link.

*   **Input:** Search query "Aladin 2009"
*   **Selection:** Movie "Aladin 2009"
*   **Extracted Link (DoodStream):** `https://dsvplay.com/d/v73hv93j5z4o`
*   **Browser Verification:**
    *   Navigated to DoodStream URL.
    *   Clicked "Download Now" -> "Original" -> "Download file".
    *   **Result:** SUCCESS.
    *   **Final Download URL:** `https://x319o.cloudatacdn.com/u5kj7ku3bxalsdgge7f5iicbdp3b2a5jd2z3t5sfetm5tgimmi5w3afbj47q/Aladin.2009.1080p.WEB-DL.EgyDead.CoM.mp4?token=6arburv81jr9tvc21547xldw&expiry=1764142233403`

## Test Case 3: Quality Selection
**Objective:** Verify that the script identifies and lists available qualities.

*   **Input:** Search query "Avatar The Way of Water"
*   **Result:** Script successfully extracted "1080p" quality for all available mirrors.
    *   *Note: The specific movies tested only had 1080p available on the site, but the extraction logic `Quality: 1080p` confirms the parser is working.*

## Conclusion
The `egydead_dl.py` script correctly extracts valid download links from the EgyDead website. The extracted DoodStream links were manually verified to lead to actual `.mp4` file downloads. The Playwright dependency has been successfully removed.
