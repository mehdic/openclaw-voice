"""Integration tests for multi-turn STT behaviour.

These tests exercise the LocalSpeechStream._run() coroutine across multiple
consecutive speech turns to guard against:

- `continue` vs `break` scope confusion in the VAD event loop (pre-fix the END
  frame was appended to pre_buffer AND to speech_frames, duplicating audio)
- VAD smoothed-probability state not being reset between turns (post-fix,
  vad.reset() is called after every finalized utterance)
- asyncio.get_event_loop() deprecation on Python 3.10+ (replaced with
  get_running_loop())
- Executor shutdown/reuse lifecycle
"""

from __future__ import annotations

import asyncio
import inspect
import struct
import sys
import types
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers to build fake audio frames
# AudioFrame is the stub class from conftest (_install_livekit_stubs); we get it
# from livekit.rtc at runtime so isinstance checks in _run() pass correctly.
# ---------------------------------------------------------------------------


def _make_audio_frame(
    n_samples: int = 512,
    sample_rate: int = 16000,
    num_channels: int = 1,
) -> Any:
    """Return a stub livekit.rtc.AudioFrame (silence)."""
    import livekit.rtc as rtc

    raw = struct.pack(f"<{n_samples * num_channels}h", *([0] * (n_samples * num_channels)))
    return rtc.AudioFrame(data=raw, samples_per_channel=n_samples, sample_rate=sample_rate, num_channels=num_channels)


def _make_speech_frame(amplitude: int = 16000, n_samples: int = 512, sample_rate: int = 16000) -> Any:
    """Return a stub audio frame with non-zero amplitude (simulates speech)."""
    import livekit.rtc as rtc

    raw = struct.pack(f"<{n_samples}h", *([amplitude] * n_samples))
    return rtc.AudioFrame(data=raw, samples_per_channel=n_samples, sample_rate=sample_rate, num_channels=1)


# ---------------------------------------------------------------------------
# Minimal in-process async channel (replaces livekit aio.Chan)
# ---------------------------------------------------------------------------


class SimpleAsyncChan:
    """A minimal async channel backed by asyncio.Queue."""

    def __init__(self):
        self._q: asyncio.Queue = asyncio.Queue()
        self._closed = False

    def send_nowait(self, item) -> None:
        if not self._closed:
            self._q.put_nowait(item)

    async def __anext__(self):
        try:
            return await asyncio.wait_for(self._q.get(), timeout=0.5)
        except asyncio.TimeoutError:
            raise StopAsyncIteration

    def __aiter__(self):
        return self

    def close(self):
        self._closed = True


class FlushSentinel:
    pass


# ---------------------------------------------------------------------------
# Minimal LocalSpeechStream harness
# (bypasses the real RecognizeStream base class so we can test _run() directly)
# ---------------------------------------------------------------------------


class _BareStream:
    """Minimal shim that exposes only what LocalSpeechStream._run() needs."""

    _FlushSentinel = FlushSentinel

    def __init__(self, stt_instance, language: str = "en"):
        self._stt = stt_instance
        self._language = language
        self._input_ch = SimpleAsyncChan()
        self._event_ch = SimpleAsyncChan()
        self._all_events: list = []

        original_send = self._event_ch.send_nowait

        def capturing_send(ev):
            self._all_events.append(ev)
            original_send(ev)

        self._event_ch.send_nowait = capturing_send

    def push_frame(self, frame) -> None:
        self._input_ch.send_nowait(frame)

    def push_flush(self) -> None:
        self._input_ch.send_nowait(FlushSentinel())

    def close_input(self) -> None:
        self._input_ch.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def stt_mod():
    """Return the whisper module, re-importing to pick up the real livekit stubs."""
    # Force a fresh import so conftest stubs are used correctly
    for key in list(sys.modules.keys()):
        if key.startswith("openclaw_voice.providers.stt"):
            del sys.modules[key]
    from openclaw_voice.providers.stt import whisper as w

    return w


@pytest.fixture
def make_stt(stt_mod):
    """Factory that creates a LocalSTT with a predictable WhisperModel stub."""

    def _factory(text: str = "hello world"):
        inst = stt_mod.LocalSTT(
            model_size="tiny",
            language="en",
            device="cpu",
            compute_type="int8",
        )
        fake_seg = MagicMock()
        fake_seg.text = text
        fake_info = MagicMock()
        fake_info.language_probability = 0.99
        stub_model = MagicMock()
        stub_model.transcribe.return_value = ([fake_seg], fake_info)
        inst._model = stub_model
        return inst

    return _factory


@pytest.fixture
def make_stream(stt_mod):
    """Factory that creates a _BareStream wired to a LocalSpeechStream._run()."""

    def _factory(stt_instance, language: str = "en"):
        from openclaw_voice.providers.stt.whisper import LocalSpeechStream

        bare = _BareStream(stt_instance, language)
        # Patch the stream's attributes onto a mock LocalSpeechStream so _run()
        # can be called as an unbound coroutine with bare as self.
        bare._min_silence_duration = stt_mod.DEFAULT_MIN_SILENCE_DURATION_SECONDS
        bare._activation_threshold = stt_mod.DEFAULT_ACTIVATION_THRESHOLD
        # Bind _finalize so _run() can call self._finalize(...) on the bare shim.
        bare._finalize = LocalSpeechStream._finalize.__get__(bare, type(bare))
        return bare

    return _factory


# ---------------------------------------------------------------------------
# Cycling VAD — emits start on frame 1, end on frame 2, resets on reset()
# ---------------------------------------------------------------------------


def make_cycling_vad_class(stt_mod):
    class CyclingVAD(stt_mod.SileroVAD):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._frame_in_turn = 0

        def load(self) -> None:
            self._model = object()

        def process_frame(self, audio_f32):
            self._frame_in_turn += 1
            if self._frame_in_turn == 1:
                self._speaking = True
                return [{"type": "start"}]
            if self._frame_in_turn == 2:
                self._speaking = False
                return [{"type": "end"}]
            return []

        def reset(self) -> None:
            self._frame_in_turn = 0
            super().reset()

    return CyclingVAD


# ---------------------------------------------------------------------------
# Helper: run _run() on a bare stream for a fixed set of frames
# ---------------------------------------------------------------------------


async def _run_with_frames(stt_mod, bare_stream, frames, vad_class=None):
    """Feed frames into bare_stream and run LocalSpeechStream._run() as an unbound method."""
    from openclaw_voice.providers.stt.whisper import LocalSpeechStream

    ctx_manager = patch.object(stt_mod, "SileroVAD", vad_class) if vad_class else None
    if ctx_manager:
        ctx_manager.__enter__()
    try:
        run_coro = LocalSpeechStream._run(bare_stream)  # type: ignore[arg-type]
        run_task = asyncio.create_task(run_coro)
        await asyncio.sleep(0)  # let _run() start and reach the async-for

        for frame in frames:
            bare_stream._input_ch.send_nowait(frame)
            await asyncio.sleep(0)

        await asyncio.sleep(0.15)  # wait for any pending executor futures
        run_task.cancel()
        try:
            await run_task
        except (asyncio.CancelledError, Exception):
            pass
    finally:
        if ctx_manager:
            ctx_manager.__exit__(None, None, None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLocalSpeechStreamMultiTurn:
    """Multi-turn speech recognition tests."""

    @pytest.mark.asyncio
    async def test_single_turn_produces_events(self, stt_mod, make_stt, make_stream):
        """Baseline: one speech segment emits at least START and END events."""
        from livekit.agents import stt as stt_sdk

        local_stt = make_stt("hello")
        bare = make_stream(local_stt)
        CyclingVAD = make_cycling_vad_class(stt_mod)

        frames = [_make_speech_frame(), _make_speech_frame(), _make_audio_frame()]
        await _run_with_frames(stt_mod, bare, frames, vad_class=CyclingVAD)

        event_types = [e.type for e in bare._all_events]
        assert stt_sdk.SpeechEventType.START_OF_SPEECH in event_types, (
            f"Expected START_OF_SPEECH in {event_types}"
        )
        assert stt_sdk.SpeechEventType.END_OF_SPEECH in event_types, (
            f"Expected END_OF_SPEECH in {event_types}"
        )

    @pytest.mark.asyncio
    async def test_three_turns_all_produce_final_transcripts(self, stt_mod, make_stt, make_stream):
        """Three consecutive speech turns must each produce a FINAL_TRANSCRIPT.

        This is the core regression test: prior to the fix the 2nd and 3rd turns
        would silently fail because:
        1. `continue` in the VAD event `for` loop (not the outer `async for`)
           caused the END frame to also be pushed into pre_buffer, corrupting
           the audio prefix of subsequent turns.
        2. VAD smoothed-probability was never reset between turns so detection
           degraded after turn 1.
        """
        from livekit.agents import stt as stt_sdk

        local_stt = make_stt("hello world")
        bare = make_stream(local_stt)
        CyclingVAD = make_cycling_vad_class(stt_mod)

        n_turns = 3
        # Each turn: 1 start frame + 1 end frame + 2 silence frames
        frames = []
        for _ in range(n_turns):
            frames.append(_make_speech_frame())   # VAD frame 1 → start
            frames.append(_make_speech_frame())   # VAD frame 2 → end
            frames.append(_make_audio_frame())    # silence (drains queue)
            frames.append(_make_audio_frame())

        # Patch MIN_AUDIO_DURATION_SECONDS to 0 so short test frames are not
        # rejected by the duration gate inside _finalize.  The regression under
        # test is about turn management (continue/break scope + VAD reset), not
        # about audio length, so bypassing the gate here is intentional.
        with patch.object(stt_mod, "MIN_AUDIO_DURATION_SECONDS", 0.0):
            await _run_with_frames(stt_mod, bare, frames, vad_class=CyclingVAD)

        finals = [e for e in bare._all_events if e.type == stt_sdk.SpeechEventType.FINAL_TRANSCRIPT]
        assert len(finals) >= n_turns, (
            f"Expected ≥{n_turns} FINAL_TRANSCRIPT events, got {len(finals)}. "
            f"All events: {[e.type for e in bare._all_events]}"
        )

        ends = [e for e in bare._all_events if e.type == stt_sdk.SpeechEventType.END_OF_SPEECH]
        assert len(ends) >= n_turns, (
            f"Expected ≥{n_turns} END_OF_SPEECH events, got {len(ends)}"
        )

    @pytest.mark.asyncio
    async def test_end_frame_not_duplicated_in_prebuffer(self, stt_mod, make_stt, make_stream):
        """The VAD-end frame must NOT appear in the next turn's speech_frames.

        Prior to the fix, `continue` in the inner for-loop fell through to
        `pre_buffer.append(data)`, so the silence bytes at the turn boundary
        were prepended twice to the next utterance's audio.
        """
        from openclaw_voice.providers.stt.whisper import LocalSpeechStream

        local_stt = make_stt("hi")
        bare = make_stream(local_stt)
        captured_turns: list[list] = []

        original_finalize = LocalSpeechStream._finalize

        async def capturing_finalize(self_stream, stt_instance, loop, speech_frames):
            captured_turns.append(list(speech_frames))
            await original_finalize(self_stream, stt_instance, loop, speech_frames)

        bare._finalize = capturing_finalize.__get__(bare)  # type: ignore[attr-defined]

        CyclingVAD = make_cycling_vad_class(stt_mod)

        f_start_1 = _make_speech_frame(amplitude=1000)
        f_end_1 = _make_speech_frame(amplitude=1000)
        f_silence = _make_audio_frame()
        f_start_2 = _make_speech_frame(amplitude=2000)
        f_end_2 = _make_speech_frame(amplitude=2000)

        frames = [f_start_1, f_end_1, f_silence, f_start_2, f_end_2, _make_audio_frame()]
        await _run_with_frames(stt_mod, bare, frames, vad_class=CyclingVAD)

        assert len(captured_turns) >= 2, (
            f"Expected ≥2 finalized turns, got {len(captured_turns)}"
        )
        # The f_end_1 frame must NOT appear in turn-2's frames.
        turn2_frame_ids = {id(f) for f in captured_turns[1]}
        assert id(f_end_1) not in turn2_frame_ids, (
            "The VAD-end frame from turn 1 was incorrectly included in turn 2's "
            "speech_frames — pre_buffer duplication bug is still present."
        )

    @pytest.mark.asyncio
    async def test_vad_reset_called_after_each_turn(self, stt_mod, make_stt, make_stream):
        """vad.reset() must be called once per finalized utterance.

        Without the reset the VAD's smoothed probability and duration counters
        carry stale values from the previous turn, causing detection to degrade.
        """
        from openclaw_voice.providers.stt.whisper import LocalSpeechStream

        reset_calls = [0]

        class TrackingCyclingVAD(make_cycling_vad_class(stt_mod)):
            def reset(self):
                reset_calls[0] += 1
                super().reset()

        local_stt = make_stt("test")
        bare = make_stream(local_stt)

        n_turns = 2
        frames = []
        for _ in range(n_turns):
            frames.append(_make_speech_frame())
            frames.append(_make_speech_frame())
            frames.append(_make_audio_frame())

        await _run_with_frames(stt_mod, bare, frames, vad_class=TrackingCyclingVAD)

        assert reset_calls[0] >= n_turns, (
            f"Expected vad.reset() ≥{n_turns} times (once per turn), "
            f"got {reset_calls[0]}"
        )

    @pytest.mark.asyncio
    async def test_aclose_resets_executor(self, stt_mod, make_stt):
        """aclose() must install a fresh executor so the STT can be reused safely."""
        local_stt = make_stt("test")
        original_executor = local_stt._executor

        await local_stt.aclose()

        assert original_executor._shutdown, (
            "Original executor should be shut down after aclose()"
        )
        assert isinstance(local_stt._executor, ThreadPoolExecutor), (
            "aclose() should install a fresh ThreadPoolExecutor"
        )
        assert not local_stt._executor._shutdown, (
            "The replacement executor must not be shut down"
        )

    def test_get_running_loop_used_not_get_event_loop(self, stt_mod):
        """_run() and _recognize_impl must use asyncio.get_running_loop().

        asyncio.get_event_loop() is deprecated in Python 3.10+ and raises
        RuntimeError in Python 3.12+ when there is no current event loop.
        """
        from openclaw_voice.providers.stt.whisper import LocalSpeechStream, LocalSTT

        run_src = inspect.getsource(LocalSpeechStream._run)
        assert "get_running_loop" in run_src, (
            "LocalSpeechStream._run() must use asyncio.get_running_loop(), not get_event_loop()"
        )
        assert "get_event_loop" not in run_src, (
            "LocalSpeechStream._run() must not use deprecated asyncio.get_event_loop()"
        )

        impl_src = inspect.getsource(LocalSTT._recognize_impl)
        assert "get_running_loop" in impl_src, (
            "LocalSTT._recognize_impl() must use asyncio.get_running_loop()"
        )
        assert "get_event_loop" not in impl_src, (
            "LocalSTT._recognize_impl() must not use deprecated asyncio.get_event_loop()"
        )
