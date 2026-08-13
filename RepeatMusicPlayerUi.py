# RepeatMusicPlayerUi.py
# Windows 11 / PySide6 Glassmorphism Dark Theme UI
from __future__ import annotations

import os
from collections import Counter
from pathlib import Path
from typing import List, Optional

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPoint,
    QProcess,
    QPropertyAnimation,
    QSize,
    Qt,
    QUrl,
)
from PySide6.QtGui import QFontMetrics, QKeySequence, QShortcut
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from shiboken6 import isValid

import RepeatMusicPlayerCore as Core


# ----------------- 🎨 디자인 시스템 QSS 및 스타일 정밀 제어 -----------------
DARK_GLASS_STYLE = """
QWidget {
    color: #EDEFF5;
    font-family: "Pretendard", "Malgun Gothic", "Segoe UI", sans-serif;
    font-size: 13px;
}

MainWindow, QDialog {
    background-color: #141720;
}

QLabel {
    background: transparent;
}

QToolTip {
    background-color: #232734;
    color: #EDEFF5;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 6px;
    padding: 6px 10px;
}

QGroupBox {
    background-color: #1C202C;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    color: #94A3B8;
}

QSpinBox {
    background-color: #262B3A;
    color: #38BDF8;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 6px;
    padding: 3px 8px;
    font-weight: bold;
}
QSpinBox::up-button, QSpinBox::down-button {
    width: 0px;
}

QSlider::groove:horizontal {
    height: 6px;
    background: #282E3E;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #60A5FA);
    border-radius: 3px;
}
QSlider::handle:horizontal {
    width: 14px;
    height: 14px;
    background: #FFFFFF;
    border: 2px solid #3B82F6;
    border-radius: 7px;
    margin: -4px 0;
}
QSlider::handle:horizontal:hover {
    background: #60A5FA;
}
"""


# ----------------- 🔔 커스텀 100% 불투명 상단 알림 캡슐 -----------------
class ToastNotification(QtWidgets.QWidget):
    """화면 상단 중앙에 슬라이드 애니메이션으로 떠올랐다 사라지는 100% 불투명 알림 카드"""

    def __init__(self, parent: QtWidgets.QWidget, message: str, icon_symbol: str = "ℹ️"):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        root_layout = QtWidgets.QHBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)

        # 100% 불투명 솔리드 배경을 칠하는 QFrame 컨테이너
        self.container = QtWidgets.QFrame(self)
        self.container.setObjectName("ToastContainer")
        self.container.setStyleSheet("""
            QFrame#ToastContainer {
                background-color: #1E2436;
                border: 1.5px solid #6366F1;
                border-radius: 18px;
            }
            QLabel {
                color: #FFFFFF;
                font-weight: 600;
                font-size: 13px;
                background: transparent;
                border: none;
            }
        """)

        layout = QtWidgets.QHBoxLayout(self.container)
        layout.setContentsMargins(18, 9, 22, 9)
        layout.setSpacing(10)

        lbl_icon = QtWidgets.QLabel(icon_symbol)
        lbl_icon.setStyleSheet("font-size: 16px; background: transparent; border: none;")
        lbl_text = QtWidgets.QLabel(message)

        layout.addWidget(lbl_icon)
        layout.addWidget(lbl_text)

        root_layout.addWidget(self.container)

        # 은은한 그림자 효과
        shadow = QtWidgets.QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setColor(QtGui.QColor(0, 0, 0, 220))
        shadow.setOffset(0, 5)
        self.container.setGraphicsEffect(shadow)

        self.adjustSize()
        self.timer = QtCore.QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._fade_out)

    def show_toast(self, duration_ms: int = 2500):
        if not self.parentWidget():
            return
        parent_rect = self.parentWidget().rect()
        w, h = self.width(), self.height()

        # 화면 상단 중앙 위치 계산 (y=72)
        x = (parent_rect.width() - w) // 2
        y_start = 45
        y_end = 72

        self.move(x, y_start)
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()

        # 위치 이동 + 투명도 병렬 애니메이션 (Slide Down + Fade In)
        self.anim_group = QParallelAnimationGroup(self)

        anim_pos = QPropertyAnimation(self, b"pos")
        anim_pos.setDuration(280)
        anim_pos.setStartValue(QPoint(x, y_start))
        anim_pos.setEndValue(QPoint(x, y_end))
        anim_pos.setEasingCurve(QEasingCurve.OutCubic)

        anim_fade = QPropertyAnimation(self, b"windowOpacity")
        anim_fade.setDuration(280)
        anim_fade.setStartValue(0.0)
        anim_fade.setEndValue(1.0)

        self.anim_group.addAnimation(anim_pos)
        self.anim_group.addAnimation(anim_fade)
        self.anim_group.start()

        self.timer.start(duration_ms)

    def _fade_out(self):
        if not self.parentWidget():
            self.close()
            return

        x = self.x()
        y_cur = self.y()
        y_end = y_cur - 12

        self.anim_out_group = QParallelAnimationGroup(self)

        anim_pos = QPropertyAnimation(self, b"pos")
        anim_pos.setDuration(250)
        anim_pos.setStartValue(QPoint(x, y_cur))
        anim_pos.setEndValue(QPoint(x, y_end))
        anim_pos.setEasingCurve(QEasingCurve.InCubic)

        anim_fade = QPropertyAnimation(self, b"windowOpacity")
        anim_fade.setDuration(250)
        anim_fade.setStartValue(self.windowOpacity())
        anim_fade.setEndValue(0.0)

        self.anim_out_group.addAnimation(anim_pos)
        self.anim_out_group.addAnimation(anim_fade)
        self.anim_out_group.finished.connect(self._on_anim_finished)
        self.anim_out_group.start()

    def _on_anim_finished(self):
        self.close()
        self.deleteLater()


# ----------------- 🏷️ 말줄임표 자동 처리 라벨 -----------------
class ElidedLabel(QtWidgets.QLabel):
    """긴 텍스트가 라벨 크기를 이탈하지 않도록 우측 끝 말줄임(...) 자동 처리"""

    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self._full_text = text

    def setText(self, text: str):
        self._full_text = text
        self.setToolTip(text)
        super().setText(self._elided_text(text))

    def resizeEvent(self, event):
        super().setText(self._elided_text(self._full_text))
        super().resizeEvent(event)

    def _elided_text(self, text: str) -> str:
        if not text:
            return ""
        fm = QFontMetrics(self.font())
        avail_w = max(10, self.width() - 4)
        if fm.horizontalAdvance(text) <= avail_w:
            return text
        return fm.elidedText(text, Qt.ElideRight, avail_w)


class StatusElidedLabel(QtWidgets.QLabel):
    """
    트랙명과 반복 횟수 접미사(• 반복 k/n회)를 받아,
    접미사는 우측 끝에 100% 절대 노출을 보장하고 파일명만 필요한 만큼 우측(...) 말줄임 처리하는 전용 라벨
    """

    def __init__(self, file_text: str = "", suffix_text: str = "", parent=None):
        super().__init__(parent)
        self._file_text = file_text
        self._suffix_text = suffix_text

    def setStatusText(self, file_text: str, suffix_text: str = ""):
        self._file_text = file_text
        self._suffix_text = suffix_text
        self.setToolTip(f"{file_text}{suffix_text}")
        self._update_text()

    def resizeEvent(self, event):
        self._update_text()
        super().resizeEvent(event)

    def _update_text(self):
        if not self._file_text:
            super().setText("")
            return

        fm = QFontMetrics(self.font())
        avail_w = max(10, self.width() - 4)

        suffix_w = fm.horizontalAdvance(self._suffix_text) if self._suffix_text else 0
        file_w = fm.horizontalAdvance(self._file_text)

        # 전체 길이가 공간 안에 모두 들어가면 말줄임 없이 100% 전체 노출
        if file_w + suffix_w <= avail_w:
            super().setText(f"{self._file_text}{self._suffix_text}")
        else:
            # 파일명이 공간을 넘칠 때만 파일명 오른쪽 끝(...) 처리하여 접미사(반복 횟수) 폭을 100% 보장
            file_avail_w = max(10, avail_w - suffix_w)
            elided_file = fm.elidedText(self._file_text, Qt.ElideRight, file_avail_w)
            super().setText(f"{elided_file}{self._suffix_text}")


# ----------------- ❓ 도움말 모달 대화상자 (F1) -----------------
class HelpDialog(QtWidgets.QDialog):
    """F1 키 및 도움말 버튼으로 표시되는 세부 가이드 모달"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Repeat Music Player 사용 가이드")
        self.setMinimumSize(520, 420)
        self.setStyleSheet("""
            QDialog { background-color: #1A1D27; }
            QLabel { color: #EDEFF5; }
            QTextEdit {
                background-color: #141720;
                color: #CBD5E1;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 12px;
                font-size: 13px;
                line-height: 1.5;
            }
            QPushButton {
                background-color: #3B82F6;
                color: #FFFFFF;
                border-radius: 8px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2563EB; }
        """)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QtWidgets.QLabel("🎧 MINI Repeat Music Player 가이드")
        title.setStyleSheet("font-size: 17px; font-weight: bold; color: #60A5FA;")
        layout.addWidget(title)

        text = QtWidgets.QTextEdit()
        text.setReadOnly(True)
        text.setHtml("""
        <h3>✨ 주요 기능 및 사용법</h3>
        <ul>
            <li><b>트랙별 구간 반복 횟수 지정</b>: 목록의 각 곡마다 반복 횟수(0~999회)를 자유롭게 지정할 수 있습니다.</li>
            <li><b>드래그 앤 드롭 지원</b>: 탐색기에서 음악 파일이나 폴더를 플레이어 창으로 직접 드래그해서 추가하세요.</li>
            <li><b>트랙 순서 변경</b>: 목록 항목을 마우스로 드래그하거나 ⬆️/⬇️ 버튼으로 순서를 조정할 수 있습니다.</li>
            <li><b>📎 파일 합치기 (FFmpeg 연동)</b>: 현재 설정된 반복 횟수와 순서대로 하나의 완성된 파일(MP3, WAV 등)로 내보냅니다.</li>
            <li><b>⏱️ 총 예정 재생 시간 실시간 계산</b>: 반복 횟수가 반영된 총 플레이 타임을 상단 태그에서 확인하세요.</li>
        </ul>

        <h3>⌨️ 단축키 안내</h3>
        <ul>
            <li><b>[Space]</b> : 재생 / 일시정지</li>
            <li><b>[Left / Right]</b> : 5초 뒤로 / 5초 앞으로 이동</li>
            <li><b>[Up / Down]</b> : 볼륨 키우기 / 줄이기</li>
            <li><b>[F1]</b> : 도움말 열기</li>
        </ul>
        <hr>
        <p style='color:#94A3B8; font-size:12px;'>제작자: 김현석 (houndscorporation@gmail.com) | MINI Utility Series</p>
        """)
        layout.addWidget(text)

        btn_box = QtWidgets.QHBoxLayout()
        btn_box.addStretch(1)
        btn_close = QtWidgets.QPushButton("확인")
        btn_close.clicked.connect(self.accept)
        btn_box.addWidget(btn_close)

        layout.addLayout(btn_box)


# ----------------- 🎵 개별 트랙 카드 행 위젯 -----------------
class TrackRow(QtWidgets.QWidget):
    """트랙 카드 위젯 (트랙명, 재생 시간, 반복 횟수 SpinBox, 위/아래/삭제 버튼)"""

    repeats_changed = QtCore.Signal(int)
    request_move_up = QtCore.Signal(QtWidgets.QWidget)
    request_move_down = QtCore.Signal(QtWidgets.QWidget)
    request_delete = QtCore.Signal(QtWidgets.QWidget)

    def __init__(self, track: Core.Track, index: int, parent=None):
        super().__init__(parent)
        self.track = track
        self.index = index

        self.setStyleSheet("""
            TrackRow {
                background-color: #1E2330;
                border: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
            }
            TrackRow:hover {
                background-color: #252B3C;
                border: 1px solid rgba(96, 165, 250, 0.3);
            }
            TrackRow QLabel {
                background: transparent;
            }
        """)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        # 인덱스 & 아이콘
        self.lbl_idx = QtWidgets.QLabel(f"{index + 1:02d}")
        self.lbl_idx.setStyleSheet("color: #64748B; font-weight: bold; font-size: 11px;")
        self.lbl_idx.setFixedWidth(20)

        self.lbl_icon = QtWidgets.QLabel("🎵")
        self.lbl_icon.setFixedWidth(20)
        self.lbl_icon.setAlignment(Qt.AlignCenter)

        # 파일명
        self.lbl_name = ElidedLabel(track.path.name)
        self.lbl_name.setStyleSheet("font-weight: 600; color: #F1F5F9;")

        # 재생 시간 (추정/측정된 경우)
        self.lbl_dur = QtWidgets.QLabel(Core.format_ms(track.duration_ms) if track.duration_ms > 0 else "")
        self.lbl_dur.setStyleSheet("color: #64748B; font-size: 11px;")
        self.lbl_dur.setFixedWidth(50)
        self.lbl_dur.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # 반복 횟수 조절 영역 (개별 ➖ / 숫자 박스 / ➕ 버튼)
        lbl_rpt = QtWidgets.QLabel("반복:")
        lbl_rpt.setStyleSheet("color: #94A3B8; font-size: 12px; border: none; background: transparent;")

        self.btn_dec_rpt = QtWidgets.QToolButton()
        self.btn_dec_rpt.setText("➖")
        self.btn_dec_rpt.setToolTip("반복 횟수 1 차감")
        self._style_tool_btn(self.btn_dec_rpt)
        self.btn_dec_rpt.clicked.connect(lambda: self.spin_repeats.setValue(max(0, self.spin_repeats.value() - 1)))

        self.spin_repeats = QtWidgets.QSpinBox()
        self.spin_repeats.setButtonSymbols(QtWidgets.QAbstractSpinBox.NoButtons)
        self.spin_repeats.setRange(0, 999)
        self.spin_repeats.setValue(track.repeats)
        self.spin_repeats.setFixedWidth(46)
        self.spin_repeats.setAlignment(Qt.AlignCenter)
        self.spin_repeats.setStyleSheet("""
            QSpinBox {
                color: #F8FAFC;
                background-color: #141824;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 2px 0px;
                font-weight: 700;
                font-size: 13px;
            }
        """)
        self.spin_repeats.valueChanged.connect(self._on_spin_changed)

        self.btn_inc_rpt = QtWidgets.QToolButton()
        self.btn_inc_rpt.setText("➕")
        self.btn_inc_rpt.setToolTip("반복 횟수 1 증가")
        self._style_tool_btn(self.btn_inc_rpt)
        self.btn_inc_rpt.clicked.connect(lambda: self.spin_repeats.setValue(self.spin_repeats.value() + 1))

        # 이동 및 삭제 버튼들
        self.btn_up = QtWidgets.QToolButton()
        self.btn_up.setText("▲")
        self.btn_up.setToolTip("위로 이동")
        self._style_tool_btn(self.btn_up)
        self.btn_up.clicked.connect(lambda: self.request_move_up.emit(self))

        self.btn_down = QtWidgets.QToolButton()
        self.btn_down.setText("▼")
        self.btn_down.setToolTip("아래로 이동")
        self._style_tool_btn(self.btn_down)
        self.btn_down.clicked.connect(lambda: self.request_move_down.emit(self))

        self.btn_del = QtWidgets.QToolButton()
        self.btn_del.setText("🗑️")
        self.btn_del.setToolTip("목록에서 삭제")
        self._style_tool_btn(self.btn_del, is_danger=True)
        self.btn_del.clicked.connect(lambda: self.request_delete.emit(self))

        layout.addWidget(self.lbl_idx)
        layout.addWidget(self.lbl_icon)
        layout.addWidget(self.lbl_name, 1)
        layout.addWidget(self.lbl_dur)
        layout.addWidget(lbl_rpt)
        layout.addWidget(self.btn_dec_rpt)
        layout.addWidget(self.spin_repeats)
        layout.addWidget(self.btn_inc_rpt)
        layout.addWidget(self.btn_up)
        layout.addWidget(self.btn_down)
        layout.addWidget(self.btn_del)

    def update_index(self, index: int):
        self.index = index
        self.lbl_idx.setText(f"{index + 1:02d}")

    def set_duration(self, duration_ms: int):
        self.track.duration_ms = duration_ms
        self.lbl_dur.setText(Core.format_ms(duration_ms) if duration_ms > 0 else "")

    def _on_spin_changed(self, val: int):
        self.track.repeats = val
        self.repeats_changed.emit(val)

    def _style_tool_btn(self, btn: QtWidgets.QToolButton, is_danger: bool = False):
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setFixedSize(24, 24)
        if is_danger:
            btn.setStyleSheet("""
                QToolButton { background-color: rgba(239, 68, 68, 0.15); color: #EF4444; border: 0; border-radius: 4px; }
                QToolButton:hover { background-color: #EF4444; color: #FFFFFF; }
            """)
        else:
            btn.setStyleSheet("""
                QToolButton { background-color: #2D3446; color: #94A3B8; border: 0; border-radius: 4px; font-size: 10px; }
                QToolButton:hover { background-color: #3B82F6; color: #FFFFFF; }
            """)


# ----------------- 📋 커스텀 트랙 QListWidget (외부 드래그&드롭 지원) -----------------
class TrackList(QtWidgets.QListWidget):
    """드래그 앤 드롭 파일 수용 및 내부 정렬이 가능한 리스트 위젯"""

    files_dropped = QtCore.Signal(list)
    order_changed = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setAcceptDrops(True)
        self.setSpacing(4)
        self.setStyleSheet("""
            QListWidget {
                background-color: #181B26;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 6px;
            }
            QListWidget::item {
                background: transparent;
                border-radius: 8px;
            }
            QListWidget::item:selected {
                background-color: rgba(59, 130, 246, 0.2);
                border: 1px solid #3B82F6;
            }
            QScrollBar:vertical {
                background: #141720;
                width: 10px;
                margin: 4px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #33394B;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #4B556D;
            }
        """)

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QtGui.QDropEvent):
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
            if paths:
                self.files_dropped.emit(paths)
                event.acceptProposedAction()
        else:
            super().dropEvent(event)
            self.order_changed.emit()

    def items_in_order(self) -> List[Core.Track]:
        tracks = []
        for i in range(self.count()):
            it = self.item(i)
            w: TrackRow = self.itemWidget(it)
            if w:
                tracks.append(w.track)
        return tracks

    def refresh_indices(self):
        for i in range(self.count()):
            it = self.item(i)
            w: TrackRow = self.itemWidget(it)
            if w:
                w.update_index(i)

    def highlight_track(self, target: Optional[Core.Track]):
        for i in range(self.count()):
            it = self.item(i)
            w: TrackRow = self.itemWidget(it)
            if w and target is not None and w.track.uid == target.uid:
                it.setSelected(True)
                w.setStyleSheet("""
                    TrackRow {
                        background-color: rgba(59, 130, 246, 0.25);
                        border: 1px solid #3B82F6;
                        border-radius: 8px;
                    }
                    TrackRow QLabel {
                        background: transparent;
                    }
                """)
            elif w:
                w.setStyleSheet("""
                    TrackRow {
                        background-color: #1E2330;
                        border: 1px solid rgba(255, 255, 255, 0.05);
                        border-radius: 8px;
                    }
                    TrackRow:hover {
                        background-color: #252B3C;
                        border: 1px solid rgba(96, 165, 250, 0.3);
                    }
                    TrackRow QLabel {
                        background: transparent;
                    }
                """)


# ----------------- 🖥️ 메인 윈도우 UI -----------------
class MainWindow(QtWidgets.QWidget):
    """PySide6 Glassmorphism 메인 윈도우"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Repeat Music Player - MINI Series")
        self.setMinimumSize(820, 680)
        self.resize(880, 720)
        self.setStyleSheet(DARK_GLASS_STYLE)

        # 상태 제어 변수
        self.queue = Core.PlayQueue()
        self.current_track: Optional[Core.Track] = None
        self._history: List[Core.Track] = []
        self._scrubbing: bool = False
        self._totals: Counter[str] = Counter()
        self._sofar: Counter[str] = Counter()

        # FFmpeg 병합 상태
        self._merge_proc: Optional[QProcess] = None
        self._merge_progress: Optional[QtWidgets.QProgressDialog] = None
        self._merge_canceled: bool = False

        # 미디어 변경 및 비동기 재생 보장 플래그
        self._is_changing_source: bool = False
        self._pending_play: bool = False

        # 뷰 구축
        self._init_ui()

        # Qt Multimedia 플레이어
        self.audio = QAudioOutput(self)
        self.audio.setVolume(0.8)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio)

        # 시그널 바인딩
        self._connect_signals()

        # 단축키 설정
        self._setup_shortcuts()

        # 드래그 앤 드롭 활성화
        self.setAcceptDrops(True)

    def _init_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        # ===== 1. 헤더 레이아웃 (제목, 폴더선택, 파일추가, 총재생시간, 도움말) =====
        header = QtWidgets.QHBoxLayout()
        header.setSpacing(10)

        self.lbl_folder = ElidedLabel("🎼 폴더: (미선택)")
        self.lbl_folder.setStyleSheet("font-size: 15px; font-weight: bold; color: #F8FAFC;")
        header.addWidget(self.lbl_folder, 1)

        # 총 예정 재생시간 태그
        self.lbl_total_time = QtWidgets.QLabel("⏱️ 총 예정: 00:00")
        self.lbl_total_time.setStyleSheet("""
            background-color: rgba(59, 130, 246, 0.15);
            color: #60A5FA;
            border: 1px solid rgba(96, 165, 250, 0.3);
            border-radius: 8px;
            padding: 5px 12px;
            font-weight: bold;
        """)
        header.addWidget(self.lbl_total_time)

        self.btn_choose = QtWidgets.QPushButton("📂 폴더 열기")
        self._style_btn(self.btn_choose)
        self.btn_choose.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_choose.clicked.connect(self.choose_folder)

        self.btn_add_files = QtWidgets.QPushButton("➕ 파일 추가")
        self._style_btn(self.btn_add_files)
        self.btn_add_files.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_add_files.clicked.connect(self.add_files)

        self.btn_help = QtWidgets.QPushButton("❓ 도움말(F1)")
        self._style_btn(self.btn_help)
        self.btn_help.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_help.clicked.connect(self.show_help)

        header.addWidget(self.btn_choose)
        header.addWidget(self.btn_add_files)
        header.addWidget(self.btn_help)
        root.addLayout(header)

        # ===== 2. 스마트 프리셋 & 파일 합치기 바 =====
        preset_bar = QtWidgets.QHBoxLayout()
        preset_bar.setSpacing(10)

        self.btn_merge = QtWidgets.QPushButton("📎 파일 합치기")
        self._style_btn(self.btn_merge, primary=True)
        self.btn_merge.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_merge.setToolTip("현재 UI 순서와 트랙별 반복 횟수를 적용하여 하나의 음원 파일로 병합 내보내기합니다.")
        self.btn_merge.clicked.connect(self.combine_files)
        preset_bar.addWidget(self.btn_merge)

        preset_bar.addStretch(1)

        # 세그먼트 툴 카드 컨테이너 (고급화 일체형 알약 캡슐)
        preset_card = QtWidgets.QFrame()
        preset_card.setObjectName("PresetCard")
        preset_card.setStyleSheet("""
            QFrame#PresetCard {
                background-color: #191E2B;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 12px;
            }
        """)
        card_layout = QtWidgets.QHBoxLayout(preset_card)
        card_layout.setContentsMargins(4, 4, 4, 4)
        card_layout.setSpacing(2)

        self.btn_reset_1 = QtWidgets.QPushButton("🎯 전체 1회")
        self.btn_reset_1.setToolTip("모든 트랙의 반복 횟수를 1회로 설정")
        self.btn_reset_1.clicked.connect(lambda: self._set_all_repeats(1))

        self.btn_reset_0 = QtWidgets.QPushButton("⭕ 전체 0회")
        self.btn_reset_0.setToolTip("모든 트랙의 반복 횟수를 0회로 설정")
        self.btn_reset_0.clicked.connect(lambda: self._set_all_repeats(0))

        self.btn_inc = QtWidgets.QPushButton("➕ 1회 증가")
        self.btn_inc.setToolTip("모든 트랙의 반복 횟수를 1씩 증가")
        self.btn_inc.clicked.connect(lambda: self._bulk_adjust(+1))

        self.btn_dec = QtWidgets.QPushButton("➖ 1회 차감")
        self.btn_dec.setToolTip("모든 트랙의 반복 횟수를 1씩 감소")
        self.btn_dec.clicked.connect(lambda: self._bulk_adjust(-1))

        for b in (self.btn_reset_1, self.btn_reset_0, self.btn_inc, self.btn_dec):
            self._style_preset_btn(b)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            card_layout.addWidget(b)

        # 구분선
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.VLine)
        sep.setStyleSheet("border: none; background-color: rgba(255, 255, 255, 0.12); width: 1px; margin: 4px 6px;")
        card_layout.addWidget(sep)

        self.btn_shuffle = QtWidgets.QPushButton("🔀 순서 셔플")
        self.btn_shuffle.setToolTip("트랙 재생 순서를 무작위로 섞습니다")
        self._style_preset_btn(self.btn_shuffle, accent=True)
        self.btn_shuffle.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_shuffle.clicked.connect(self._shuffle_list)
        card_layout.addWidget(self.btn_shuffle)

        preset_bar.addWidget(preset_card)
        root.addLayout(preset_bar)

        # ===== 3. 중앙 트랙 리스트 =====
        self.list = TrackList()
        self.list.files_dropped.connect(self.handle_dropped_paths)
        self.list.order_changed.connect(self._on_list_reordered)
        root.addWidget(self.list, 1)

        # ===== 4. 시크바 & 재생 시간 표시 =====
        seek_box = QtWidgets.QHBoxLayout()
        seek_box.setSpacing(10)

        self.seek_slider = QtWidgets.QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.setSingleStep(1000)
        self.seek_slider.setPageStep(5000)
        self.seek_slider.setCursor(Qt.PointingHandCursor)

        self.lbl_time = QtWidgets.QLabel("00:00 / 00:00")
        self.lbl_time.setStyleSheet("color: #94A3B8; font-weight: bold; font-family: monospace;")
        self.lbl_time.setFixedWidth(130)
        self.lbl_time.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        seek_box.addWidget(self.seek_slider, 1)
        seek_box.addWidget(self.lbl_time)
        root.addLayout(seek_box)

        # ===== 5. 플레이 컨트롤 바 (재생/일시정지/이전/다음 & 볼륨 슬라이더 & 횟수 업데이트) =====
        ctrl_bar = QtWidgets.QHBoxLayout()
        ctrl_bar.setSpacing(10)

        self.btn_update = QtWidgets.QPushButton("🔄 반복 설정 새로고침")
        self._style_btn(self.btn_update, primary=True)
        self.btn_update.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_update.setToolTip("변경된 반복/순서를 재생 큐에 반영하고 처음부터 다시 재생합니다.")
        self.btn_update.clicked.connect(self.update_repeats_and_restart)
        ctrl_bar.addWidget(self.btn_update)

        ctrl_bar.addStretch(1)

        self.btn_prev = QtWidgets.QPushButton("⏮ 이전")
        self.btn_play = QtWidgets.QPushButton("▶ 재생")
        self.btn_pause = QtWidgets.QPushButton("⏸ 일시정지")
        self.btn_next = QtWidgets.QPushButton("⏭ 다음")

        for b in (self.btn_prev, self.btn_play, self.btn_pause, self.btn_next):
            self._style_btn(b)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setFixedWidth(112)

        ctrl_bar.addWidget(self.btn_prev)
        ctrl_bar.addWidget(self.btn_play)
        ctrl_bar.addWidget(self.btn_pause)
        ctrl_bar.addWidget(self.btn_next)

        ctrl_bar.addStretch(1)

        # 볼륨 영역
        self.btn_mute = QtWidgets.QToolButton()
        self.btn_mute.setText("🔊")
        self.btn_mute.setToolTip("음소거 토글")
        self._style_mute_btn(self.btn_mute)
        self.btn_mute.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_mute.clicked.connect(self._toggle_mute)

        self.vol_slider = QtWidgets.QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(80)
        self.vol_slider.setFixedWidth(90)
        self.vol_slider.setToolTip("볼륨 조절 (0~100)")
        self.vol_slider.valueChanged.connect(self._on_vol_changed)

        ctrl_bar.addWidget(self.btn_mute)
        ctrl_bar.addWidget(self.vol_slider)

        root.addLayout(ctrl_bar)

        # ===== 6. 하단 상태 표시 바 (글래스 캡슐 모던 카키 바) =====
        self.status_frame = QtWidgets.QFrame()
        self.status_frame.setObjectName("StatusFrame")
        self.status_frame.setStyleSheet("""
            QFrame#StatusFrame {
                background-color: #131722;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
            }
        """)
        status_layout = QtWidgets.QHBoxLayout(self.status_frame)
        status_layout.setContentsMargins(10, 6, 12, 6)
        status_layout.setSpacing(10)

        # 상태 배지
        self.lbl_status_badge = QtWidgets.QLabel("⏹️ 대기")
        self.lbl_status_badge.setStyleSheet("""
            color: #818CF8;
            background-color: rgba(99, 102, 241, 0.15);
            border: 1px solid rgba(99, 102, 241, 0.3);
            border-radius: 12px;
            padding: 2px 10px;
            font-size: 11px;
            font-weight: 700;
        """)

        # 상세 상태 설명 (StatusElidedLabel - 접미사 보장 라벨)
        self.lbl_status_text = StatusElidedLabel("선택된 트랙이 없습니다. 폴더를 열거나 파일들을 추가해 주세요.", "")
        self.lbl_status_text.setStyleSheet("""
            QLabel {
                color: #CBD5E1;
                font-size: 12.5px;
                font-weight: 500;
                border: none;
                background: transparent;
            }
        """)

        # 우측 트랙 개수 요약 - 테두리 완전 제거
        self.lbl_queue_stats = QtWidgets.QLabel("🎵 0개 트랙")
        self.lbl_queue_stats.setStyleSheet("""
            QLabel {
                color: #64748B;
                font-size: 11.5px;
                font-weight: 600;
                border: none;
                background: transparent;
            }
        """)

        status_layout.addWidget(self.lbl_status_badge)
        status_layout.addWidget(self.lbl_status_text, 1)
        status_layout.addWidget(self.lbl_queue_stats)

        root.addWidget(self.status_frame)

    def _style_btn(self, btn: QtWidgets.QPushButton, primary: bool = False):
        btn.setCursor(Qt.PointingHandCursor)
        if primary:
            btn.setStyleSheet("""
                QPushButton {
                    color: #FFFFFF;
                    background-color: #3B82F6;
                    border: 0;
                    border-radius: 8px;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #2563EB; }
                QPushButton:pressed { background-color: #1D4ED8; }
            """)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    color: #EDEFF5;
                    background-color: #232734;
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                    padding: 8px 14px;
                    font-weight: 500;
                }
                QPushButton:hover { background-color: #2E3446; border-color: rgba(255, 255, 255, 0.2); }
                QPushButton:pressed { background-color: #1C202C; }
            """)

    def _style_preset_btn(self, btn: QtWidgets.QPushButton, accent: bool = False):
        btn.setCursor(Qt.PointingHandCursor)
        if accent:
            btn.setStyleSheet("""
                QPushButton {
                    color: #A5B4FC;
                    background-color: rgba(99, 102, 241, 0.18);
                    border: none;
                    border-radius: 8px;
                    padding: 6px 14px;
                    font-size: 12px;
                    font-weight: 700;
                }
                QPushButton:hover {
                    color: #FFFFFF;
                    background-color: rgba(99, 102, 241, 0.38);
                }
                QPushButton:pressed {
                    background-color: rgba(79, 70, 229, 0.5);
                }
            """)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    color: #CBD5E1;
                    background-color: transparent;
                    border: none;
                    border-radius: 8px;
                    padding: 6px 14px;
                    font-size: 12px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    color: #FFFFFF;
                    background-color: rgba(255, 255, 255, 0.08);
                }
                QPushButton:pressed {
                    background-color: rgba(255, 255, 255, 0.04);
                }
            """)

    def _style_mute_btn(self, btn: QtWidgets.QToolButton):
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedSize(30, 30)
        btn.setStyleSheet("""
            QToolButton { background-color: #232734; color: #EDEFF5; border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; }
            QToolButton:hover { background-color: #2E3446; }
        """)

    def _connect_signals(self):
        # 플레이어 이벤트
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)
        self.player.errorOccurred.connect(self._on_player_error)

        # 시크바
        self.seek_slider.sliderPressed.connect(self._on_seek_pressed)
        self.seek_slider.sliderReleased.connect(self._on_seek_released)
        self.seek_slider.valueChanged.connect(self._on_seek_value_changed)

        # 버튼
        self.btn_play.clicked.connect(self.play)
        self.btn_pause.clicked.connect(self.pause)
        self.btn_next.clicked.connect(self.play_next)
        self.btn_prev.clicked.connect(self.play_prev)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Space"), self, activated=self._toggle_play_pause)
        QShortcut(QKeySequence("Left"), self, activated=lambda: self._nudge(-5000))
        QShortcut(QKeySequence("Right"), self, activated=lambda: self._nudge(+5000))
        QShortcut(QKeySequence("Up"), self, activated=lambda: self._on_volume_shortcut(+5))
        QShortcut(QKeySequence("Down"), self, activated=lambda: self._on_volume_shortcut(-5))
        QShortcut(QKeySequence("F1"), self, activated=self.show_help)

    def _on_volume_shortcut(self, delta: int):
        """리스트/스핀박스 포커스 중에는 ↑↓를 볼륨으로 가로채지 않음"""
        fw = self.focusWidget()
        if isinstance(fw, (QtWidgets.QAbstractItemView, QtWidgets.QAbstractSpinBox)):
            return
        self._adjust_volume(delta)

    def show_toast(self, message: str, symbol: str = "ℹ️"):
        if not hasattr(self, "_active_toasts"):
            self._active_toasts = []
        toast = ToastNotification(self, message, symbol)
        self._active_toasts.append(toast)

        def _drop(_obj=None, t=toast):
            try:
                self._active_toasts.remove(t)
            except (ValueError, AttributeError):
                pass

        toast.destroyed.connect(_drop)
        toast.show_toast()

    def show_help(self):
        dlg = HelpDialog(self)
        dlg.exec()

    # ===== 드래그 앤 드롭 처리 =====
    def dragEnterEvent(self, event: QtGui.QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QtGui.QDropEvent):
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
            if paths:
                self.handle_dropped_paths(paths)

    def handle_dropped_paths(self, paths: List[str]):
        tracks = Core.scan_paths(paths)
        if not tracks:
            self.show_toast("지원되는 오디오 파일이 없습니다.", "⚠️")
            return

        for t in tracks:
            self._add_track_to_list(t)

        self._integrate_new_tracks(tracks)
        self.show_toast(f"{len(tracks)}개 오디오 트랙 추가됨", "🎵")

    # ===== 트랙 리스트 관리 =====
    def _add_track_to_list(self, track: Core.Track):
        it = QtWidgets.QListWidgetItem()
        idx = self.list.count()
        row = TrackRow(track, idx, parent=self.list)
        row.repeats_changed.connect(self._on_track_repeat_changed)
        row.request_move_up.connect(self._move_track_up)
        row.request_move_down.connect(self._move_track_down)
        row.request_delete.connect(self._delete_track)

        it.setSizeHint(QSize(400, 46))
        self.list.addItem(it)
        self.list.setItemWidget(it, row)

    def _move_track_up(self, row_widget: QtWidgets.QWidget):
        QtCore.QTimer.singleShot(0, lambda: self._do_move_track_up(row_widget))

    def _do_move_track_up(self, row_widget: QtWidgets.QWidget):
        if not isValid(row_widget):
            return
        tracks = self.list.items_in_order()
        row = -1
        for i in range(self.list.count()):
            if self.list.itemWidget(self.list.item(i)) == row_widget:
                row = i
                break
        if row > 0:
            tracks[row], tracks[row - 1] = tracks[row - 1], tracks[row]
            self.list.clear()
            for t in tracks:
                self._add_track_to_list(t)
            self.list.refresh_indices()
            self._on_structure_changed()

    def _move_track_down(self, row_widget: QtWidgets.QWidget):
        QtCore.QTimer.singleShot(0, lambda: self._do_move_track_down(row_widget))

    def _do_move_track_down(self, row_widget: QtWidgets.QWidget):
        if not isValid(row_widget):
            return
        tracks = self.list.items_in_order()
        row = -1
        for i in range(self.list.count()):
            if self.list.itemWidget(self.list.item(i)) == row_widget:
                row = i
                break
        if 0 <= row < len(tracks) - 1:
            tracks[row], tracks[row + 1] = tracks[row + 1], tracks[row]
            self.list.clear()
            for t in tracks:
                self._add_track_to_list(t)
            self.list.refresh_indices()
            self._on_structure_changed()

    def _delete_track(self, row_widget: QtWidgets.QWidget):
        QtCore.QTimer.singleShot(0, lambda: self._do_delete_track(row_widget))

    def _do_delete_track(self, row_widget: QtWidgets.QWidget):
        if not isValid(row_widget):
            return
        tracks = self.list.items_in_order()
        row = -1
        for i in range(self.list.count()):
            if self.list.itemWidget(self.list.item(i)) == row_widget:
                row = i
                break
        if row >= 0:
            tracks.pop(row)
            self.list.clear()
            for t in tracks:
                self._add_track_to_list(t)
            self.list.refresh_indices()
            self._on_structure_changed()
            self.show_toast("트랙 삭제됨", "🗑️")

    def _shuffle_list(self):
        import random

        tracks = self.list.items_in_order()
        if not tracks:
            return
        random.shuffle(tracks)
        self.list.clear()
        for t in tracks:
            self._add_track_to_list(t)
        self._on_structure_changed()
        self.show_toast("트랙 순서 셔플 완료", "🎲")

    def _on_structure_changed(self):
        """순서/삭제/셔플 등 목록 구조가 바뀌면 재생 큐와 동기화"""
        if self._is_playback_active():
            self._stop_playback_reset()
            self._rebuild_queue_state(force_rebuild=True)
            self._update_now_status("목록이 변경되어 재생을 멈췄습니다. 재생을 다시 눌러 주세요")
        else:
            self._rebuild_queue_state(force_rebuild=True)

    def _set_all_repeats(self, val: int):
        for i in range(self.list.count()):
            it = self.list.item(i)
            w: TrackRow = self.list.itemWidget(it)
            if w:
                w.spin_repeats.blockSignals(True)
                w.spin_repeats.setValue(val)
                w.track.repeats = val
                w.spin_repeats.blockSignals(False)
        self._rebuild_queue_state()

    def _bulk_adjust(self, delta: int):
        for i in range(self.list.count()):
            it = self.list.item(i)
            w: TrackRow = self.list.itemWidget(it)
            if w:
                cur = w.spin_repeats.value()
                new_val = max(0, cur + delta)
                w.spin_repeats.blockSignals(True)
                w.spin_repeats.setValue(new_val)
                w.track.repeats = new_val
                w.spin_repeats.blockSignals(False)
        self._rebuild_queue_state()

    def _on_track_repeat_changed(self, _val: int):
        QtCore.QTimer.singleShot(0, self._rebuild_queue_state)

    def _on_list_reordered(self):
        self.list.refresh_indices()
        self._on_structure_changed()

    def _is_playback_active(self) -> bool:
        return self.current_track is not None and self.player.playbackState() != QMediaPlayer.StoppedState

    def _stop_playback_reset(self):
        """재생 중단 및 큐/히스토리 초기화 (폴더 교체·강제 리셋용)"""
        self._pending_play = False
        self._is_changing_source = True
        try:
            self.player.stop()
        finally:
            self._is_changing_source = False
        self.current_track = None
        self._history.clear()
        self._sofar.clear()
        self.queue.clear()
        self.list.highlight_track(None)

    def _planned_totals(self, tracks: List[Core.Track]) -> Counter:
        totals: Counter = Counter()
        for t in tracks:
            reps = max(0, int(t.repeats))
            if reps > 0:
                totals[t.uid] += reps
        return totals

    def _integrate_new_tracks(self, new_tracks: List[Core.Track]):
        """대기 중이면 큐 재빌드, 재생 중이면 새 트랙만 남은 큐 끝에 추가"""
        if self._is_playback_active():
            self.queue.set_order(self.list.items_in_order())
            for t in new_tracks:
                self.queue.append_track_plays(t)
                reps = max(0, int(t.repeats))
                if reps > 0:
                    self._totals[t.uid] += reps
            total_ms = self.queue.total_expected_duration_ms()
            if total_ms > 0:
                self.lbl_total_time.setText(f"⏱️ 총 예정: {Core.format_ms(total_ms)}")
            self.lbl_queue_stats.setText(f"🎵 {self.list.count()}개 트랙")
        else:
            self._rebuild_queue_state(force_rebuild=True)

    def _rebuild_queue_state(self, reset_queue: bool = True, force_rebuild: bool = False):
        tracks = self.list.items_in_order()
        self.queue.set_order(tracks)
        planned = self._planned_totals(tracks)

        # 재생 중에는 남은 큐·반복 카운터를 덮어쓰지 않음 — "반복 설정 새로고침"으로만 반영
        if reset_queue and (force_rebuild or not self._is_playback_active()):
            self.queue.build_queue()
            self._totals = Counter(t.uid for t in self.queue._q)
        # else: keep live _q and _totals; total-time label still previews planned order

        # 총 예정 재생시간 갱신 (UI 미리보기: 목록의 현재 반복 설정 기준)
        total_ms = self.queue.total_expected_duration_ms()
        if total_ms > 0:
            self.lbl_total_time.setText(f"⏱️ 총 예정: {Core.format_ms(total_ms)}")
        else:
            play_units = sum(planned.values()) if planned else self.queue.remaining_count()
            self.lbl_total_time.setText(f"⏱️ 총 예정: {play_units}회 트랙")

        # 트랙 총 수 요약 갱신
        self.lbl_queue_stats.setText(f"🎵 {len(tracks)}개 트랙")

    # ===== 폴더 선택 및 파일 추가 =====
    def choose_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "음악 폴더 선택")
        if not folder:
            return
        self._stop_playback_reset()
        tracks = Core.scan_folder(folder)
        self.list.clear()
        for t in tracks:
            self._add_track_to_list(t)
        self.lbl_folder.setText(f"🎼 폴더: {folder}")
        self._rebuild_queue_state(force_rebuild=True)
        self._update_now_status("큐 대기 준비 완료")
        self.show_toast(f"폴더에서 {len(tracks)}개 파일 불러옴", "📂")

    def add_files(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "오디오 파일 추가", "", "Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a *.aac *.wma)"
        )
        if not files:
            return
        tracks = Core.scan_paths(files)
        for t in tracks:
            self._add_track_to_list(t)
        self._integrate_new_tracks(tracks)
        self.show_toast(f"{len(tracks)}개 파일 추가됨", "➕")

    def update_repeats_and_restart(self):
        self._stop_playback_reset()
        self._rebuild_queue_state(force_rebuild=True)
        self._update_now_status("재생 큐 리셋 완료")
        self.play_next()
        self.show_toast("재생 큐가 리셋되고 처음부터 시작합니다.", "🔄")

    # ===== 재생 제어 메커니즘 =====
    def play(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            return
        if self.current_track is None:
            self.play_next()
        else:
            self.player.play()

    def pause(self):
        self.player.pause()

    def _toggle_play_pause(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.pause()
        else:
            self.play()

    def play_next(self):
        if self.current_track is not None:
            self._history.append(self.current_track)

        if not self.queue.has_next():
            self._pending_play = False
            self.current_track = None
            self._is_changing_source = True
            try:
                self.player.stop()
            finally:
                self._is_changing_source = False
            self._update_now_status("모든 트랙 재생 완료")
            self.list.highlight_track(None)
            return

        self.current_track = self.queue.pop_next()
        if self.current_track is not None:
            self._sofar[self.current_track.uid] += 1

        url = QUrl.fromLocalFile(str(self.current_track.path))
        self._pending_play = True
        self._is_changing_source = True
        try:
            self.player.setSource(url)
            self.player.play()
        finally:
            self._is_changing_source = False

        self.list.highlight_track(self.current_track)
        self._update_now_status("재생중")

    def play_prev(self):
        if not self._history:
            return
        prev_track = self._history.pop()
        if self.current_track is not None:
            self.queue._q.appendleft(self.current_track)
            if self._sofar.get(self.current_track.uid, 0) > 0:
                self._sofar[self.current_track.uid] -= 1

        self.current_track = prev_track
        url = QUrl.fromLocalFile(str(self.current_track.path))
        self._pending_play = True
        self._is_changing_source = True
        try:
            self.player.setSource(url)
            self.player.play()
        finally:
            self._is_changing_source = False

        self.list.highlight_track(self.current_track)
        self._update_now_status("재생중")

    def _update_now_status(self, state_text: str):
        # 트랙 총 수 요약 갱신
        track_cnt = self.list.count()
        self.lbl_queue_stats.setText(f"🎵 {track_cnt}개 트랙")

        # 재생 상태별 뱃지 스타일 & 아이콘 지정
        if state_text == "재생중" or state_text.startswith("재생중"):
            self.lbl_status_badge.setText("🟢 재생 중")
            self.lbl_status_badge.setStyleSheet("""
                color: #34D399;
                background-color: rgba(16, 185, 129, 0.18);
                border: 1px solid rgba(16, 185, 129, 0.35);
                border-radius: 12px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: 700;
            """)
        elif "일시정지" in state_text:
            self.lbl_status_badge.setText("⏸️ 일시정지")
            self.lbl_status_badge.setStyleSheet("""
                color: #FBBF24;
                background-color: rgba(245, 158, 11, 0.18);
                border: 1px solid rgba(245, 158, 11, 0.35);
                border-radius: 12px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: 700;
            """)
        elif "오류" in state_text or "실패" in state_text:
            self.lbl_status_badge.setText("⚠️ 오류 발생")
            self.lbl_status_badge.setStyleSheet("""
                color: #F87171;
                background-color: rgba(239, 68, 68, 0.18);
                border: 1px solid rgba(239, 68, 68, 0.35);
                border-radius: 12px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: 700;
            """)
        elif "모든 트랙 재생 완료" in state_text or state_text.endswith("재생 완료"):
            self.lbl_status_badge.setText("🏁 모든 재생 완료")
            self.lbl_status_badge.setStyleSheet("""
                color: #A78BFA;
                background-color: rgba(139, 92, 246, 0.18);
                border: 1px solid rgba(139, 92, 246, 0.35);
                border-radius: 12px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: 700;
            """)
        else:
            self.lbl_status_badge.setText("⏹️ 대기 중")
            self.lbl_status_badge.setStyleSheet("""
                color: #818CF8;
                background-color: rgba(99, 102, 241, 0.15);
                border: 1px solid rgba(99, 102, 241, 0.3);
                border-radius: 12px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: 700;
            """)

        # 상세 텍스트 정보 표시 (StatusElidedLabel: 파일명과 반복 횟수 접미사 분리 전달)
        if self.current_track is not None:
            k = self._sofar.get(self.current_track.uid, 0)
            n = self._totals.get(self.current_track.uid, 0)
            if n > 0 and k > n:
                k = n
            rpt = f" • 반복 ({k}/{n}회)" if n > 0 else ""
            self.lbl_status_text.setStatusText(self.current_track.path.name, rpt)
        else:
            self.lbl_status_text.setStatusText(state_text, "")

    # ===== 시크바 & 볼륨 컨트롤 =====
    def _on_duration_changed(self, dur_ms: int):
        self.seek_slider.setRange(0, max(0, dur_ms))
        cur = self.player.position()
        self.lbl_time.setText(f"{Core.format_ms(cur)} / {Core.format_ms(dur_ms)}")

        # 현재 실행중인 트랙의 duration 정보 기록
        if self.current_track is not None and dur_ms > 0:
            self.current_track.duration_ms = dur_ms
            for i in range(self.list.count()):
                it = self.list.item(i)
                w: TrackRow = self.list.itemWidget(it)
                if w and w.track.uid == self.current_track.uid:
                    w.set_duration(dur_ms)
                    break
            self._rebuild_queue_state(reset_queue=False)

    def _on_position_changed(self, pos_ms: int):
        if not self._scrubbing:
            self.seek_slider.blockSignals(True)
            self.seek_slider.setValue(pos_ms)
            self.seek_slider.blockSignals(False)
        dur = self.player.duration()
        self.lbl_time.setText(f"{Core.format_ms(pos_ms)} / {Core.format_ms(dur)}")

    def _on_seek_pressed(self):
        self._scrubbing = True

    def _on_seek_released(self):
        self._scrubbing = False
        self.player.setPosition(self.seek_slider.value())

    def _on_seek_value_changed(self, val: int):
        if self._scrubbing:
            dur = self.player.duration()
            self.lbl_time.setText(f"{Core.format_ms(val)} / {Core.format_ms(dur)}")

    def _nudge(self, delta_ms: int):
        new_p = max(0, self.player.position() + delta_ms)
        self.player.setPosition(new_p)

    def _on_vol_changed(self, val: int):
        self.audio.setVolume(val / 100.0)
        self.btn_mute.setText("🔇" if val == 0 else "🔊")

    def _toggle_mute(self):
        if self.vol_slider.value() > 0:
            self._last_vol = self.vol_slider.value()
            self.vol_slider.setValue(0)
        else:
            self.vol_slider.setValue(getattr(self, "_last_vol", 80))

    def _adjust_volume(self, delta: int):
        new_v = max(0, min(100, self.vol_slider.value() + delta))
        self.vol_slider.setValue(new_v)

    # ===== Player 이벤트 콜백 =====
    def _on_playback_state_changed(self, state):
        if state == QMediaPlayer.PlayingState:
            self._update_now_status("재생중")
        elif state == QMediaPlayer.PausedState:
            self._update_now_status("일시정지")
        # Stopped: 플레이리스트 종료/소스 교체 시 "완료·대기" 문구를 덮어쓰지 않음

    def _on_media_status_changed(self, status):
        # 비동기 미디어 로딩 완료 시 재생 보장
        if status in (QMediaPlayer.LoadedMedia, QMediaPlayer.BufferedMedia):
            if getattr(self, "_pending_play", False):
                self._pending_play = False
                if self.player.playbackState() != QMediaPlayer.PlayingState:
                    self.player.play()

        if getattr(self, "_is_changing_source", False):
            return

        if status == QMediaPlayer.EndOfMedia:
            self.play_next()

    def _on_player_error(self, err, *args):
        self._pending_play = False
        self._update_now_status(f"오류: {self.player.errorString()}")

    def closeEvent(self, event: QtGui.QCloseEvent):
        self._pending_play = False
        if self._merge_proc is not None:
            try:
                self._merge_proc.kill()
            except Exception:
                pass
            self._merge_proc = None
        try:
            self.player.stop()
        except Exception:
            pass
        super().closeEvent(event)

    # ===== 📎 FFmpeg 파일 합치기 구현 =====
    def combine_files(self):
        if self._merge_proc is not None and self._merge_proc.state() != QProcess.NotRunning:
            self.show_toast("이미 파일 합치기가 진행 중입니다.", "⚠️")
            return

        tracks = self.list.items_in_order()
        try:
            list_file, _seq = Core.build_concat_manifest(tracks)
        except ValueError as e:
            QtWidgets.QMessageBox.warning(self, "합치기 취소", str(e))
            return

        dlg = QtWidgets.QFileDialog(self, "합친 오디오 파일 저장")
        dlg.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        dlg.setNameFilters(["MP3 (*.mp3)", "WAV (*.wav)", "M4A (*.m4a)", "OGG (*.ogg)", "FLAC (*.flac)"])
        dlg.setDefaultSuffix("mp3")
        if not dlg.exec():
            try:
                os.remove(list_file)
            except Exception:
                pass
            return

        out_path = Path(dlg.selectedFiles()[0])
        safe_out_name = Core.safe_filename(out_path.name)
        out_path = out_path.with_name(safe_out_name)
        ext = out_path.suffix.lower().lstrip(".")

        self._merge_canceled = False
        # 모달 프로그레스 대화상자
        self._merge_progress = QtWidgets.QProgressDialog("FFmpeg 오디오 합치기 진행 중...", "취소", 0, 0, self)
        self._merge_progress.setWindowModality(Qt.ApplicationModal)
        self._merge_progress.canceled.connect(self._on_merge_cancel)
        self._merge_progress.show()

        ff = Core.find_ffmpeg_bin()
        codec_opts = {
            "mp3": ["-c:a", "libmp3lame", "-b:a", "192k"],
            "wav": ["-c:a", "pcm_s16le"],
            "m4a": ["-c:a", "aac", "-b:a", "192k"],
            "aac": ["-c:a", "aac", "-b:a", "192k"],
            "ogg": ["-c:a", "libvorbis", "-q:a", "5"],
            "flac": ["-c:a", "flac"],
        }.get(ext, ["-c:a", "libmp3lame", "-b:a", "192k"])

        args = ["-hide_banner", "-nostats", "-nostdin", "-y", "-f", "concat", "-safe", "0", "-i", list_file, *codec_opts, str(out_path)]

        self._merge_proc = QProcess(self)
        self._merge_proc.finished.connect(lambda code, _sig: self._on_merge_finished(code, list_file, out_path))

        if os.name == "nt":

            def _no_console(mod):
                flags = mod.get("creationFlags", 0) | 0x08000000 | 0x00000008 | 0x00000200
                mod["creationFlags"] = flags
                si = mod.get("startupInfo", {})
                si["dwFlags"] = si.get("dwFlags", 0) | 0x00000001
                si["wShowWindow"] = 0
                mod["startupInfo"] = si

            try:
                self._merge_proc.setCreateProcessArgumentsModifier(_no_console)
            except Exception:
                pass

        self._merge_proc.start(ff, args)
        if not self._merge_proc.waitForStarted(3000):
            self._merge_progress.close()
            QtWidgets.QMessageBox.critical(self, "실행 실패", "FFmpeg 프로세스를 시작할 수 없습니다.")
            try:
                os.remove(list_file)
            except Exception:
                pass
            self._merge_proc = None
            self._merge_canceled = False

    def _on_merge_cancel(self):
        self._merge_canceled = True
        proc = self._merge_proc
        if not proc:
            return
        proc.terminate()

        def _kill_if_still_running(p=proc):
            try:
                if isValid(p) and p.state() != QProcess.NotRunning:
                    p.kill()
            except Exception:
                pass

        QtCore.QTimer.singleShot(1000, _kill_if_still_running)

    def _on_merge_finished(self, code: int, list_file: str, out_path: Path):
        canceled = self._merge_canceled
        self._merge_canceled = False

        if self._merge_progress:
            self._merge_progress.close()
        try:
            os.remove(list_file)
        except Exception:
            pass

        if canceled:
            self.show_toast("파일 합치기가 취소되었습니다.", "ℹ️")
        elif code == 0 and out_path.exists():
            self.show_toast("파일 합치기가 성공적으로 완료되었습니다!", "✅")
            QtWidgets.QMessageBox.information(self, "성공", f"합쳐진 파일이 성공적으로 저장되었습니다:\n{out_path}")
        else:
            self.show_toast("파일 합치기 실패", "❌")
            QtWidgets.QMessageBox.critical(self, "오류", "FFmpeg 합치기 도중 오류가 발생했습니다.")

        self._merge_proc = None
        self._merge_progress = None
