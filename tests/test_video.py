"""Video frame extraction + describe_video, with imageio mocked."""

from __future__ import annotations

import io

import imageio.v3 as iio
import numpy as np
import pytest
from PIL import Image

import synthaudience.video as video_mod
from synthaudience.llm import FakeLLMClient


def _fake_frames(n: int = 30, w: int = 320, h: int = 180) -> list[np.ndarray]:
    """A list of fake frames as RGB arrays (synthetic gradient so JPEGs encode validly)."""
    out = []
    for i in range(n):
        arr = np.full((h, w, 3), fill_value=(i * 8) % 256, dtype=np.uint8)
        out.append(arr)
    return out


def test_extract_frames_picks_evenly_spaced(tmp_path, monkeypatch):
    fake_video = tmp_path / "clip.mp4"
    fake_video.write_bytes(b"x")

    frames = _fake_frames(30)
    monkeypatch.setattr(iio, "imiter", lambda _path: iter(frames))

    out = video_mod.extract_frames(fake_video, n_frames=6)
    assert len(out) == 6
    for blob in out:
        assert blob[:2] == b"\xff\xd8"  # JPEG SOI marker
        Image.open(io.BytesIO(blob))  # decodable


def test_extract_frames_handles_short_video(tmp_path, monkeypatch):
    fake_video = tmp_path / "tiny.mp4"
    fake_video.write_bytes(b"x")

    monkeypatch.setattr(iio, "imiter", lambda _path: iter(_fake_frames(3)))
    out = video_mod.extract_frames(fake_video, n_frames=6)
    assert len(out) == 3


def test_extract_frames_empty_video(tmp_path, monkeypatch):
    fake_video = tmp_path / "empty.mp4"
    fake_video.write_bytes(b"x")

    monkeypatch.setattr(iio, "imiter", lambda _path: iter([]))
    assert video_mod.extract_frames(fake_video) == []


def test_extract_frames_raises_on_missing_file():
    with pytest.raises(FileNotFoundError):
        video_mod.extract_frames("/nonexistent/path.mp4")


@pytest.mark.asyncio
async def test_describe_video_calls_vision(tmp_path, monkeypatch):
    fake_video = tmp_path / "clip.mp4"
    fake_video.write_bytes(b"x")

    monkeypatch.setattr(iio, "imiter", lambda _path: iter(_fake_frames(12)))
    monkeypatch.setattr(iio, "immeta", lambda _path: {"duration": 18.5})

    fake_llm = FakeLLMClient(
        responses=["A creator demonstrates a low-bar back squat in a grey gym."]
    )
    desc = await video_mod.describe_video(fake_video, title="Squat cues", llm=fake_llm)
    assert "low-bar back squat" in desc

    assert len(fake_llm.calls) == 1
    call = fake_llm.calls[0]
    assert call["vision"] is True
    assert call["n_images"] == 6
    assert "Squat cues" in call["user"]
    assert "18.5-second" in call["user"]


@pytest.mark.asyncio
async def test_describe_video_handles_missing_duration(tmp_path, monkeypatch):
    fake_video = tmp_path / "clip.mp4"
    fake_video.write_bytes(b"x")

    monkeypatch.setattr(iio, "imiter", lambda _path: iter(_fake_frames(12)))
    monkeypatch.setattr(iio, "immeta", lambda _path: {})

    fake_llm = FakeLLMClient(responses=["a description"])
    desc = await video_mod.describe_video(fake_video, title="x", llm=fake_llm)
    assert desc == "a description"
    assert "short video" in fake_llm.calls[0]["user"]


@pytest.mark.asyncio
async def test_describe_video_raises_on_no_frames(tmp_path, monkeypatch):
    fake_video = tmp_path / "empty.mp4"
    fake_video.write_bytes(b"x")

    monkeypatch.setattr(iio, "imiter", lambda _path: iter([]))

    fake_llm = FakeLLMClient(responses=[])
    with pytest.raises(ValueError, match="Could not extract"):
        await video_mod.describe_video(fake_video, title="x", llm=fake_llm)
