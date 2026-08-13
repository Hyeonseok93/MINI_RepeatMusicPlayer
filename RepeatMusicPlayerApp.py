# -*- coding: utf-8 -*-
# RepeatMusicPlayerApp.py
# Tier 1: 엔트리포인트, 프로세스 생명주기, 단일 인스턴스 잠금, 전역 예외 처리

import argparse
import os
import sys
import tempfile
import traceback

from PySide6 import QtGui, QtWidgets
from PySide6.QtCore import QLockFile, QTimer

import RepeatMusicPlayerCore as Core
from RepeatMusicPlayerUi import MainWindow

# ---- PyInstaller 부트 스플래시 연동 ----
_boot_splash = None
try:
    import pyi_splash

    _boot_splash = pyi_splash
except Exception:
    _boot_splash = None


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repeat Music Player - MINI Series")
    parser.add_argument("--debug", action="store_true", help="디버그 모드 활성화")
    parser.add_argument("--multi", action="store_true", help="중복 실행 차단 해제")
    return parser.parse_args(argv[1:])


def load_app_icon() -> QtGui.QIcon:
    for cand in ("assets/app.ico", "assets/app.png"):
        p = Core.resource_path(cand)
        if os.path.exists(p):
            return QtGui.QIcon(p)
    return QtGui.QIcon()


def setup_exception_hook(debug_mode: bool = False):
    """미처리 예외를 포착하여 에러 팝업을 띄우는 전역 예외 훅"""

    def exception_hook(exctype, value, tb):
        err_msg = "".join(traceback.format_exception(exctype, value, tb))
        print(f"[CRITICAL UNHANDLED EXCEPTION]\n{err_msg}", file=sys.stderr)

        if not debug_mode:
            dialog = QtWidgets.QMessageBox()
            dialog.setIcon(QtWidgets.QMessageBox.Critical)
            dialog.setWindowTitle("오류 발생 - Repeat Music Player")
            dialog.setText("예기치 않은 치명적 오류가 발생했습니다.")
            dialog.setInformativeText(str(value))
            dialog.setDetailedText(err_msg)
            dialog.exec()
        else:
            sys.__excepthook__(exctype, value, tb)

    sys.excepthook = exception_hook


class App(QtWidgets.QApplication):

    def __init__(self, argv: list[str]):
        super().__init__(argv)
        self.setApplicationName("Repeat Music Player")
        self.setApplicationVersion("2.0.0")

        icon = load_app_icon()
        if not icon.isNull():
            self.setWindowIcon(icon)

        # Font Database Loading (Pretendard) — 다른 MINI 앱과 동일
        for font_name in ("Pretendard-Medium.ttf", "Pretendard-Bold.ttf"):
            font_path = Core.resource_path(os.path.join("assets", "fonts", font_name))
            if os.path.exists(font_path):
                QtGui.QFontDatabase.addApplicationFont(font_path)

        app_font = QtGui.QFont("Pretendard", 10)
        app_font.setStyleHint(QtGui.QFont.SansSerif)
        self.setFont(app_font)

        self.win = MainWindow()
        if not icon.isNull():
            self.win.setWindowIcon(icon)
        self.win.show()

        # 스플래시 화면 지연 닫기
        if _boot_splash is not None:
            QTimer.singleShot(100, lambda: _boot_splash.close())


def main() -> int:
    args = parse_args(sys.argv)
    setup_exception_hook(debug_mode=args.debug)

    # 단일 인스턴스: 창을 띄우기 전에 잠금 (실패 시에만 임시 QApplication으로 안내)
    lock_file = None
    if not args.multi:
        lock_path = os.path.join(tempfile.gettempdir(), "mini_repeat_music_player.lock")
        lock_file = QLockFile(lock_path)
        lock_file.setStaleLockTime(0)
        if not lock_file.tryLock(100):
            if _boot_splash is not None:
                try:
                    _boot_splash.close()
                except Exception:
                    pass
            dummy = QtWidgets.QApplication([sys.argv[0]])
            QtWidgets.QMessageBox.information(
                None, "안내", "Repeat Music Player가 이미 실행 중입니다.\n기존 프로세스를 확인해 주세요."
            )
            del dummy
            return 0

    # 커스텀 CLI 플래그를 Qt로 넘기지 않음
    app = App([sys.argv[0]])

    try:
        ret = app.exec()
    finally:
        if lock_file and lock_file.isLocked():
            lock_file.unlock()

    return ret


if __name__ == "__main__":
    sys.exit(main())
