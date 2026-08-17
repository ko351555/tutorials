from ystick.stages.stage5_scene_planning import _build_scenes


def _sentence(text, start_ms, end_ms):
    return {"text": text, "start_ms": start_ms, "end_ms": end_ms}


def test_short_sentences_merge_until_min_duration():
    sentences = [_sentence(f"s{i}", i * 1000, (i + 1) * 1000) for i in range(10)]
    words = []
    scenes = _build_scenes(sentences, words, min_ms=4000, max_ms=12000)
    assert all(s["duration_ms"] >= 4000 for s in scenes[:-1])
    total_duration = sum(s["duration_ms"] for s in scenes)
    assert total_duration == sentences[-1]["end_ms"] - sentences[0]["start_ms"]


def test_oversized_sentence_is_split():
    sentences = [_sentence("very long sentence", 0, 20000)]
    words = [{"word": f"w{i}", "start_ms": i * 1000, "end_ms": (i + 1) * 1000} for i in range(20)]
    scenes = _build_scenes(sentences, words, min_ms=4000, max_ms=8000)
    assert len(scenes) > 1
    assert all(s["duration_ms"] <= 8000 + 1000 for s in scenes)
