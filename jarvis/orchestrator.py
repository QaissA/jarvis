import logging
import queue
import re
from enum import Enum

import numpy as np
import sounddevice as sd

from jarvis.audio.mic import RATE, Mic
from jarvis.audio.stt import STT
from jarvis.audio.tts import TTS
from jarvis.audio.vad import EndOfSpeech
from jarvis.audio.wakeword import WakeWord
from jarvis.config import Config
from jarvis.tools import claude, timers

log = logging.getLogger("jarvis")
State = Enum("State", "IDLE LISTENING TRANSCRIBING THINKING SPEAKING")
_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def split_images(text: str) -> tuple[str, list[str]]:
    """Pull markdown images out of a reply: they are shown, never spoken."""
    return _IMAGE.sub("", text).strip(), _IMAGE.findall(text)


_YES = set("yes yeah yep yup sure ok okay go proceed do please confirm confirmed affirmative absolutely certainly".split())
_NO = set("no nope not don't dont stop cancel never wait".split())


def is_yes(answer: str) -> bool:
    """A spoken or typed answer approves only if it has a yes word and no no word: unclear means no."""
    words = set(re.findall(r"[a-z']+", answer.lower()))
    return bool(words & _YES) and not words & _NO


CHIME = (np.sin(2 * np.pi * 880 * np.arange(int(RATE * 0.12)) / RATE) * 8000).astype(np.int16)


def run(cfg: Config, build_agent, ptt: bool = False, emit=lambda kind, text: None,
        inbox: queue.Queue | None = None) -> None:
    """emit(kind, text) reports "state", "you", "jarvis" and "image" events to a UI.
    inbox feeds typed text in; an empty string means "listen now" without the wake word."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    tts, stt, vad, mic = TTS(cfg.piper_voice), STT(cfg.whisper_model, cfg.language), EndOfSpeech(), Mic()
    wake = None if ptt else WakeWord(cfg.wake_threshold)

    def enter(state: State) -> None:
        log.info(state.name)
        emit("state", state.name)

    def say(text: str) -> None:
        enter(State.SPEAKING)
        log.info("Jarvis: %s", text)
        text, images = split_images(text)
        emit("jarvis", text)
        for src in images:
            emit("image", src)
        tts.speak(text)
        mic.flush()  # the mic stays open while speaking, so throw away our own voice
        if wake:
            wake.reset()

    def listen() -> str:
        enter(State.LISTENING)
        audio = vad.record(mic.read, cfg.silence_seconds, cfg.max_record_seconds, cfg.followup_seconds)
        enter(State.TRANSCRIBING)
        text = stt.transcribe(audio)
        log.info("You: %s", text)
        if text:
            emit("you", text)
        return text

    def confirm(question: str, detail: str = "") -> bool:
        if detail:
            emit("jarvis", detail)  # the exact command or file goes on screen, only the question is spoken
        say(question)
        answer = listen()
        if not answer and inbox:  # nothing heard (or no mic): take a typed answer
            try:
                answer = inbox.get(timeout=20)
                emit("you", answer)
            except queue.Empty:
                pass
        return is_yes(answer)

    agent = build_agent(cfg, confirm)
    if mic.is_silent():
        log.warning("microphone is silent")
        emit("jarvis", "I can't hear anything. Allow Jarvis under System Settings, Privacy and Security, Microphone, "
                       "then reopen me. Typing still works.")
    timers.on_fire = claude.announce = say
    followup = False
    while True:
        typed = ""
        if not followup:
            enter(State.IDLE)
            if ptt:
                input("Press Enter, then speak… ")
                mic.flush()
            else:
                while not wake.heard(mic.read()):
                    if inbox and not inbox.empty():
                        typed = inbox.get()
                        break
        if typed:
            emit("you", typed)
        elif not followup:
            sd.play(CHIME, RATE)
            sd.wait()
            # Drop the tail of "Hey Jarvis" and the chime: the recorder took them for the command,
            # stopped after 0.8 s of quiet and went back to IDLE before the user had spoken.
            mic.flush()
            if wake:
                wake.reset()  # or the wake word still in its buffer fires a second time
        text = typed or listen()
        if not text:
            followup = False
            continue
        enter(State.THINKING)
        reply = agent.reply(text)
        say(reply)
        followup = split_images(reply)[0].endswith("?")  # Jarvis asked something: listen again without the wake word
