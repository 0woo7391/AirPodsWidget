from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer


class AlertService(QObject):
    playingChanged = Signal(bool)
    playbackError = Signal(str)

    def __init__(self, audio_file: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._audio = QAudioOutput(self)
        self._player = QMediaPlayer(self)
        self._player.setAudioOutput(self._audio)
        self._player.setSource(QUrl.fromLocalFile(str(audio_file.resolve())))
        self._player.playbackStateChanged.connect(self._on_state_changed)
        self._player.errorOccurred.connect(lambda _code, text: self.playbackError.emit(text))
        self.set_volume(60)

    def set_volume(self, percent: int) -> None:
        self._audio.setVolume(max(0.0, min(1.0, percent / 100.0)))

    def play(self) -> None:
        self._player.stop()
        self._player.setPosition(0)
        self._player.play()

    def stop(self) -> None:
        self._player.stop()

    def _on_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        self.playingChanged.emit(state == QMediaPlayer.PlayingState)
