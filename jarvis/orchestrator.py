import logging
from enum import Enum

import numpy as np
import sounddevice as sd

from jarvis.audio.mic import RATE, Mic
from jarvis.audio.stt import STT
from jarvis.audio.tts import TTS
from jarvis.audio.vad import EndOfSpeech
from jarvis.audio.wakeword import WakeWord
from jarvis.config import Config
from jarvis.tools import timers

log = logging.getLogger("jarvis")
State = Enum("State", "IDLE LISTENING TRANSCRIBING THINKING SPEAKING")
CHIME = (np.sin(2 * np.pi * 880 * np.arange(int(RATE * 0.12)) / RATE) * 8000).astype(np.int16)


def run(cfg: Config, build_agent, ptt: bool = False) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    tts, stt, vad, mic = TTS(cfg.piper_voice), STT(cfg.whisper_model, cfg.language), EndOfSpeech(), Mic()
    wake = None if ptt else WakeWord(cfg.wake_threshold)

    def enter(state: State) -> None:
        log.info(state.name)

    def say(text: str) -> None:
        enter(State.SPEAKING)
        log.info("Jarvis: %s", text)
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
        return text

    def confirm(question: str) -> bool:
        say(question)
        return "yes" in listen().lower()

    agent = build_agent(cfg, confirm)
    timers.on_fire = say
    followup = False
    while True:
        if not followup:
            enter(State.IDLE)
            if ptt:
                input("Press Enter, then speak… ")
                mic.flush()
            else:
                while not wake.heard(mic.read()):
                    pass
            sd.play(CHIME, RATE)
        text = listen()
        if not text:
            followup = False
            continue
        enter(State.THINKING)
        reply = agent.reply(text)
        say(reply)
        followup = reply.rstrip().endswith("?")  # Jarvis asked something: listen again without the wake word
