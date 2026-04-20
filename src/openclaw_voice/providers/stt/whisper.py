"""Local faster-whisper STT with Silero VAD for OpenClaw Voice."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from faster_whisper import WhisperModel
from livekit import rtc
from livekit.agents import stt
from livekit.agents.types import APIConnectOptions, DEFAULT_API_CONNECT_OPTIONS, NOT_GIVEN, NotGivenOr
from livekit.agents.utils import AudioBuffer

logger = logging.getLogger("stt_local")

_shared_model: WhisperModel | None = None
_shared_model_key: tuple[str, str, str] | None = None
_shared_model_lock = threading.Lock()

_shared_silero_model = None
_shared_silero_lock = threading.Lock()

MIN_AUDIO_DURATION_SECONDS = 0.6
MAX_AUDIO_DURATION_SECONDS = 30.0
WHISPER_SAMPLE_RATE = 16000
INTERIM_INTERVAL_SECONDS = 1.0
SILERO_SAMPLE_RATE = 16000
SILERO_WINDOW_SAMPLES = 512
DEFAULT_MIN_SPEECH_DURATION_SECONDS = 0.05
DEFAULT_MIN_SILENCE_DURATION_SECONDS = 0.6
DEFAULT_ACTIVATION_THRESHOLD = 0.5
DEFAULT_DEACTIVATION_THRESHOLD = 0.35
DEFAULT_DEACTIVATION_DELTA = 0.15
DEFAULT_EXP_FILTER_ALPHA = 0.35
PRE_BUFFER_MAX_SECONDS = 0.5
EXECUTOR_MAX_WORKERS = 1


def get_shared_model(model_size: str, device: str, compute_type: str) -> WhisperModel:
    """Get or create the shared WhisperModel singleton."""

    global _shared_model, _shared_model_key

    requested_key = (model_size, device, compute_type)
    if _shared_model is not None:
        if _shared_model_key != requested_key:
            raise RuntimeError(
                "Shared WhisperModel already initialized with "
                f"{_shared_model_key}, cannot reuse with {requested_key}"
            )
        return _shared_model

    with _shared_model_lock:
        if _shared_model is None:
            logger.info(
                "Loading shared faster-whisper model=%s device=%s compute=%s",
                model_size,
                device,
                compute_type,
            )
            t0 = time.monotonic()
            _shared_model = WhisperModel(
                model_size,
                device=device,
                compute_type=compute_type,
            )
            _shared_model_key = requested_key
            logger.info("Shared model loaded in %.2fs", time.monotonic() - t0)

    return _shared_model


def get_shared_silero_model():
    """Get or create the shared Silero VAD model singleton."""

    global _shared_silero_model

    if _shared_silero_model is not None:
        return _shared_silero_model

    with _shared_silero_lock:
        if _shared_silero_model is None:
            try:
                from livekit.plugins.silero.onnx_model import OnnxModel, new_inference_session

                session = new_inference_session(force_cpu=True)
                _shared_silero_model = OnnxModel(
                    onnx_session=session,
                    sample_rate=SILERO_SAMPLE_RATE,
                )
                logger.info("Shared Silero VAD model loaded from livekit-plugins-silero")
            except Exception:
                logger.exception("Failed to load shared Silero VAD model")
                raise

    return _shared_silero_model


class SileroVAD:
    """Lightweight Silero VAD wrapper using the LiveKit plugin model."""

    def __init__(
        self,
        *,
        activation_threshold: float = DEFAULT_ACTIVATION_THRESHOLD,
        deactivation_threshold: float = DEFAULT_DEACTIVATION_THRESHOLD,
        min_speech_duration: float = DEFAULT_MIN_SPEECH_DURATION_SECONDS,
        min_silence_duration: float = DEFAULT_MIN_SILENCE_DURATION_SECONDS,
        exp_filter_alpha: float = DEFAULT_EXP_FILTER_ALPHA,
    ) -> None:
        self.activation_threshold = activation_threshold
        self.deactivation_threshold = deactivation_threshold
        self.min_speech_duration = min_speech_duration
        self.min_silence_duration = min_silence_duration
        self._alpha = exp_filter_alpha
        self._model = None
        self._smoothed_prob = 0.0
        self._speaking = False
        self._speech_duration = 0.0
        self._silence_duration = 0.0

    def load(self) -> None:
        """Load the Silero ONNX model."""

        self._model = get_shared_silero_model()

    def process_frame(self, audio_f32: np.ndarray) -> list[dict]:
        """Process audio and return start/end speech events."""

        if self._model is None:
            raise RuntimeError("Silero VAD not loaded - call load() first")

        events = []
        window_duration = SILERO_WINDOW_SAMPLES / SILERO_SAMPLE_RATE
        offset = 0
        while offset + SILERO_WINDOW_SAMPLES <= len(audio_f32):
            chunk = audio_f32[offset : offset + SILERO_WINDOW_SAMPLES].reshape(1, -1)
            raw_prob = self._model(chunk)
            self._smoothed_prob = (self._alpha * raw_prob) + ((1 - self._alpha) * self._smoothed_prob)
            probability = self._smoothed_prob

            if probability >= self.activation_threshold or (
                self._speaking and probability > self.deactivation_threshold
            ):
                self._speech_duration += window_duration
                self._silence_duration = 0.0
                if not self._speaking and self._speech_duration >= self.min_speech_duration:
                    self._speaking = True
                    events.append({"type": "start"})
            else:
                self._silence_duration += window_duration
                self._speech_duration = 0.0
                if self._speaking and self._silence_duration >= self.min_silence_duration:
                    self._speaking = False
                    events.append({"type": "end"})

            offset += SILERO_WINDOW_SAMPLES

        return events

    @property
    def is_speaking(self) -> bool:
        """Return whether speech is currently active."""

        return self._speaking

    def reset(self) -> None:
        """Reset all VAD state."""

        self._smoothed_prob = 0.0
        self._speaking = False
        self._speech_duration = 0.0
        self._silence_duration = 0.0


class LocalSTT(stt.STT):
    """LiveKit STT plugin backed by faster-whisper plus Silero VAD."""

    def __init__(
        self,
        *,
        model_size: str = "small",
        language: str = "en",
        device: str = "cpu",
        compute_type: str = "int8",
        beam_size: int = 1,
        min_silence_duration: float = DEFAULT_MIN_SILENCE_DURATION_SECONDS,
        activation_threshold: float = DEFAULT_ACTIVATION_THRESHOLD,
    ) -> None:
        super().__init__(
            capabilities=stt.STTCapabilities(
                streaming=True,
                interim_results=True,
            )
        )
        self._model_size = model_size
        self._language = language
        self._device = device
        self._compute_type = compute_type
        self._beam_size = beam_size
        self._min_silence_duration = min_silence_duration
        self._activation_threshold = activation_threshold
        self._model: WhisperModel | None = None
        self._executor = ThreadPoolExecutor(max_workers=EXECUTOR_MAX_WORKERS)

    def _ensure_model(self) -> WhisperModel:
        if self._model is None:
            self._model = get_shared_model(
                self._model_size,
                self._device,
                self._compute_type,
            )
        return self._model

    def _transcribe_sync(self, audio: np.ndarray, language: str) -> tuple[str, float]:
        model = self._ensure_model()
        t0 = time.monotonic()
        segments, info = model.transcribe(
            audio,
            language=language,
            beam_size=self._beam_size,
            best_of=1,
            vad_filter=False,
            without_timestamps=True,
            condition_on_previous_text=False,
        )
        parts = [segment.text.strip() for segment in segments if segment.text.strip()]
        result = " ".join(parts)
        elapsed = time.monotonic() - t0

        if result:
            duration = len(audio) / WHISPER_SAMPLE_RATE
            logger.debug(
                "Transcribed %.2fs in %.3fs (RTF=%.2f): %r",
                duration,
                elapsed,
                elapsed / max(duration, 0.001),
                result[:100],
            )

        return result, info.language_probability

    @property
    def model(self) -> str:
        """Return the effective model name."""

        return f"faster-whisper-{self._model_size}"

    @property
    def provider(self) -> str:
        """Return the provider name."""

        return "faster-whisper"

    async def _recognize_impl(
        self,
        buffer: AudioBuffer,
        *,
        language: NotGivenOr[str] = NOT_GIVEN,
        conn_options: APIConnectOptions,
    ) -> stt.SpeechEvent:
        lang = language if isinstance(language, str) else self._language
        audio = _audio_buffer_to_numpy(buffer)

        duration = len(audio) / WHISPER_SAMPLE_RATE
        if duration < MIN_AUDIO_DURATION_SECONDS:
            return _empty_event(lang)
        if duration > MAX_AUDIO_DURATION_SECONDS:
            audio = audio[: int(MAX_AUDIO_DURATION_SECONDS * WHISPER_SAMPLE_RATE)]

        loop = asyncio.get_event_loop()
        try:
            text, confidence = await loop.run_in_executor(self._executor, self._transcribe_sync, audio, lang)
        except Exception:
            logger.exception("Transcription failed")
            return _empty_event(lang)

        if not text:
            return _empty_event(lang)

        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[stt.SpeechData(language=lang, text=text, confidence=confidence)],
        )

    def stream(
        self,
        *,
        language: NotGivenOr[str] = NOT_GIVEN,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> "LocalSpeechStream":
        lang = language if isinstance(language, str) else self._language
        return LocalSpeechStream(
            stt=self,
            language=lang,
            conn_options=conn_options,
            min_silence_duration=self._min_silence_duration,
            activation_threshold=self._activation_threshold,
        )

    async def aclose(self) -> None:
        """Close local resources."""

        self._executor.shutdown(wait=False)
        self._model = None


class LocalSpeechStream(stt.RecognizeStream):
    """Streaming STT using Silero VAD endpointing and faster-whisper transcription."""

    def __init__(
        self,
        *,
        stt: LocalSTT,
        language: str,
        conn_options: APIConnectOptions,
        min_silence_duration: float,
        activation_threshold: float,
    ) -> None:
        super().__init__(stt=stt, conn_options=conn_options)
        self._language = language
        self._min_silence_duration = min_silence_duration
        self._activation_threshold = activation_threshold

    async def _run(self) -> None:
        stt_instance: LocalSTT = self._stt  # type: ignore[assignment]
        loop = asyncio.get_event_loop()
        vad = SileroVAD(
            activation_threshold=self._activation_threshold,
            deactivation_threshold=max(self._activation_threshold - DEFAULT_DEACTIVATION_DELTA, 0.01),
            min_speech_duration=DEFAULT_MIN_SPEECH_DURATION_SECONDS,
            min_silence_duration=self._min_silence_duration,
            exp_filter_alpha=DEFAULT_EXP_FILTER_ALPHA,
        )
        vad.load()
        logger.info("Silero VAD initialized for STT endpointing")

        speech_frames: list[rtc.AudioFrame] = []
        pre_buffer: list[rtc.AudioFrame] = []
        pre_buffer_samples = 0
        speaking = False
        last_interim_time = 0.0

        async for data in self._input_ch:
            if isinstance(data, rtc.AudioFrame):
                audio_f32 = _frame_to_float32(data)
                vad_events = vad.process_frame(audio_f32)

                for event in vad_events:
                    if event["type"] == "start" and not speaking:
                        speaking = True
                        speech_frames = list(pre_buffer)
                        pre_buffer.clear()
                        pre_buffer_samples = 0
                        last_interim_time = time.monotonic()
                        self._event_ch.send_nowait(stt.SpeechEvent(type=stt.SpeechEventType.START_OF_SPEECH))
                        logger.debug("VAD: speech started (with %d prefix frames)", len(speech_frames))
                    elif event["type"] == "end" and speaking:
                        speech_frames.append(data)
                        await self._finalize(stt_instance, loop, speech_frames)
                        speaking = False
                        speech_frames.clear()
                        logger.debug("VAD: speech ended -> finalized")
                        continue

                if speaking:
                    speech_frames.append(data)
                else:
                    pre_buffer.append(data)
                    pre_buffer_samples += data.samples_per_channel
                    max_samples = int(PRE_BUFFER_MAX_SECONDS * (data.sample_rate or WHISPER_SAMPLE_RATE))
                    while pre_buffer_samples > max_samples and pre_buffer:
                        removed = pre_buffer.pop(0)
                        pre_buffer_samples -= removed.samples_per_channel

                    now = time.monotonic()
                    if now - last_interim_time >= INTERIM_INTERVAL_SECONDS and len(speech_frames) > 0:
                        last_interim_time = now
                        audio = _frames_to_numpy(speech_frames)
                        duration = len(audio) / WHISPER_SAMPLE_RATE
                        if duration >= MIN_AUDIO_DURATION_SECONDS:
                            try:
                                text, confidence = await loop.run_in_executor(
                                    stt_instance._executor,
                                    stt_instance._transcribe_sync,
                                    audio,
                                    self._language,
                                )
                                if text:
                                    self._event_ch.send_nowait(
                                        stt.SpeechEvent(
                                            type=stt.SpeechEventType.INTERIM_TRANSCRIPT,
                                            alternatives=[
                                                stt.SpeechData(
                                                    language=self._language,
                                                    text=text,
                                                    confidence=confidence,
                                                )
                                            ],
                                        )
                                    )
                            except Exception:
                                logger.exception("Interim transcription error")
            elif isinstance(data, self._FlushSentinel):
                if speaking and speech_frames:
                    await self._finalize(stt_instance, loop, speech_frames)
                    speaking = False
                speech_frames.clear()

        if speaking and speech_frames:
            await self._finalize(stt_instance, loop, speech_frames)

    async def _finalize(
        self,
        stt_instance: LocalSTT,
        loop: asyncio.AbstractEventLoop,
        speech_frames: list[rtc.AudioFrame],
    ) -> None:
        """Run final transcription and emit final transcript events."""

        audio = _frames_to_numpy(speech_frames)
        duration = len(audio) / WHISPER_SAMPLE_RATE

        if duration >= MIN_AUDIO_DURATION_SECONDS:
            if duration > MAX_AUDIO_DURATION_SECONDS:
                audio = audio[: int(MAX_AUDIO_DURATION_SECONDS * WHISPER_SAMPLE_RATE)]

            try:
                text, confidence = await loop.run_in_executor(
                    stt_instance._executor,
                    stt_instance._transcribe_sync,
                    audio,
                    self._language,
                )
                if text:
                    self._event_ch.send_nowait(
                        stt.SpeechEvent(
                            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                            alternatives=[
                                stt.SpeechData(
                                    language=self._language,
                                    text=text,
                                    confidence=confidence,
                                )
                            ],
                        )
                    )
                    logger.info("Final: %r (%.2fs audio)", text, duration)
            except Exception:
                logger.exception("Final transcription error")

        self._event_ch.send_nowait(stt.SpeechEvent(type=stt.SpeechEventType.END_OF_SPEECH))


def _empty_event(language: str) -> stt.SpeechEvent:
    """Return an empty final transcript event."""

    return stt.SpeechEvent(
        type=stt.SpeechEventType.FINAL_TRANSCRIPT,
        alternatives=[stt.SpeechData(language=language, text="", confidence=0.0)],
    )


def _frame_to_float32(frame: rtc.AudioFrame) -> np.ndarray:
    """Convert an audio frame to float32 mono PCM."""

    data = np.frombuffer(frame.data.tobytes(), dtype=np.int16)
    return data.astype(np.float32) / 32768.0


def _audio_buffer_to_numpy(buffer: AudioBuffer) -> np.ndarray:
    """Convert an AudioBuffer to float32 numpy audio."""

    frames = buffer if isinstance(buffer, list) else [buffer]
    return _frames_to_numpy(frames)


def _frames_to_numpy(frames: list[rtc.AudioFrame]) -> np.ndarray:
    """Convert a list of audio frames to float32 mono PCM."""

    if not frames:
        return np.array([], dtype=np.float32)

    all_data = bytearray()
    for frame in frames:
        all_data.extend(frame.data.tobytes())

    if not all_data:
        return np.array([], dtype=np.float32)

    sample_rate = frames[0].sample_rate
    num_channels = frames[0].num_channels if hasattr(frames[0], "num_channels") else 1
    audio = np.frombuffer(bytes(all_data), dtype=np.int16).astype(np.float32) / 32768.0

    if num_channels > 1 and len(audio) >= num_channels:
        audio = audio.reshape(-1, num_channels).mean(axis=1)

    if sample_rate != WHISPER_SAMPLE_RATE and sample_rate > 0:
        target_length = int(len(audio) * WHISPER_SAMPLE_RATE / sample_rate)
        if target_length > 0:
            audio = np.interp(
                np.linspace(0, len(audio) - 1, target_length),
                np.arange(len(audio)),
                audio,
            ).astype(np.float32)

    return audio
