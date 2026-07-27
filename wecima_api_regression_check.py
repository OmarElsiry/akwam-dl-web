"""Focused Wecima parser regressions; run with ``python3 wecima_api_regression_check.py``."""

from unittest.mock import patch

from api import wecima_api as wecima


SERIES_HTML = r'''
<script type="application/ld+json">
{"@context":"https://schema.org","@graph":[
 {"@type":"WebPage","name":"The Boys (2026)"},
 {"@type":"TVSeries","name":"The Boys","numberOfSeasons":2,
  "numberOfEpisodes":16,"aggregateRating":{"ratingValue":8.6}}
]}
</script>
<li data-button="react" data-post="220467"></li>
<a class="selected SeasonsEpisodes" data-id="65498" data-season="season-5">5</a>
<a class="SeasonsEpisodes" data-id="65498" data-season="season-4">4</a>
<a href="/watch/episode-1"><episodetitle>Episode 1</episodetitle></a>
'''


def check_series_page():
    with patch.object(wecima, "_fetch", return_value=SERIES_HTML):
        result = wecima.get_series_detail("https://wecima.cx/series/example")
    assert result["metadata"]["numberOfSeasons"] == 2
    assert result["post_id"] == "65498"
    assert [s["season_number"] for s in result["seasons"]] == [5, 4]
    assert result["episodes"][0]["url"] == "https://wecima.cx/watch/episode-1"


def check_episode_ajax_shape():
    response = '<a href="https://wecima.cx/watch/s5e1"><b>Episode 1</b></a>'
    with patch.object(wecima, "_post_form", return_value=response) as post:
        result = wecima.get_season_episodes("65498", 5)
    post.assert_called_once_with(
        "https://wecima.cx/ajax/Episode",
        {"season": "season-5", "post_id": "65498"},
    )
    assert result == [{"name": "Episode 1", "url": "https://wecima.cx/watch/s5e1"}]


if __name__ == "__main__":
    check_series_page()
    check_episode_ajax_shape()
    print("Wecima regression checks passed")
