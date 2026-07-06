import json

from meldlane_transcribe.models import Segment, SourceInfo, Transcript, merge_tracks


def test_transcript_json_contract():
    t = Transcript(
        meeting_id="a1b2c3",
        lang="ru",
        duration_sec=12.5,
        source=SourceInfo(type="live"),
        segments=[Segment(start=0.0, end=4.2, speaker="me", text="привет")],
    )
    data = json.loads(t.model_dump_json())
    assert data["meeting_id"] == "a1b2c3"
    assert data["source"]["type"] == "live"
    assert data["segments"][0] == {"start": 0.0, "end": 4.2, "speaker": "me", "text": "привет"}
    assert "created_at" in data


def test_full_text_joins_segments():
    t = Transcript(
        meeting_id="x",
        source=SourceInfo(type="file", path="a.mp3"),
        segments=[
            Segment(start=0, end=1, text="раз"),
            Segment(start=1, end=2, text="два"),
        ],
    )
    assert t.full_text == "раз\nдва"


def test_merge_tracks_sorts_by_start():
    me = [
        Segment(start=0.0, end=2.0, speaker="me", text="алло"),
        Segment(start=5.0, end=7.0, speaker="me", text="да, понял"),
    ]
    others = [Segment(start=2.5, end=4.8, speaker="others", text="привет, слышно?")]

    merged = merge_tracks(me, others)

    assert [s.text for s in merged] == ["алло", "привет, слышно?", "да, понял"]
    assert [s.speaker for s in merged] == ["me", "others", "me"]
