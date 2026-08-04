from __future__ import annotations
import os
import re
import sys
import unicodedata
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Deque, List, Optional, Set, Tuple

SUPPORTED_EXTS: Set[str] = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma"}


def resource_path(rel: str) -> str:
    """PyInstaller --onefile 환경 및 개발 환경 리소스 경로 추적 유틸리티"""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(getattr(sys, "_MEIPASS"), rel)
    # 개발 환경 (현재 스크립트 기준 절대 경로)
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, rel)


def find_ffmpeg_bin() -> str:
    """내장 또는 시스템 FFmpeg 실행 파일 경로를 반환합니다."""
    exe_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    cand = resource_path(os.path.join("assets", "ffmpeg", exe_name))
    if os.path.exists(cand):
        return cand
    return "ffmpeg"


def find_ffprobe_bin() -> str:
    """내장 또는 시스템 FFprobe 실행 파일 경로를 반환합니다."""
    exe_name = "ffprobe.exe" if os.name == "nt" else "ffprobe"
    cand = resource_path(os.path.join("assets", "ffmpeg", exe_name))
    if os.path.exists(cand):
        return cand
    return "ffprobe"


def safe_filename(name: str) -> str:
    """Windows 파일 시스템 호환 안전한 파일명 생성"""
    if not name:
        return "merged_audio.mp3"
    s = unicodedata.normalize("NFKC", name)
    s = "".join(ch for ch in s if ch not in r'\/:*?"<>|').strip(" .")
    reserved = {"CON", "PRN", "AUX", "NUL"}
    reserved.update({f"COM{i}" for i in range(1, 10)})
    reserved.update({f"LPT{i}" for i in range(1, 10)})

    stem = s.split(".")[0].upper()
    if stem in reserved:
        s = f"_{s}"
    return s[:120] if s else "merged_audio.mp3"


def natural_sort_key(s: str) -> list:
    """숫자가 포함된 문자열을 사람이 직관적으로 정렬하도록 파싱"""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"([0-9]+)", s)]


@dataclass
class Track:
    """오디오 트랙 데이터 모델"""

    path: Path
    repeats: int = 1
    duration_ms: int = 0

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def total_repeats_duration_ms(self) -> int:
        return self.duration_ms * max(0, self.repeats)


def scan_folder(folder_path: str) -> List[Track]:
    """지정한 폴더 내 지원 오디오 파일들을 내추럴 정렬하여 트랙 리스트로 반환"""
    p = Path(folder_path)
    if not p.exists() or not p.is_dir():
        return []
    tracks: List[Track] = []
    file_list = sorted([f for f in p.iterdir() if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS], key=lambda x: natural_sort_key(x.name))
    for f in file_list:
        tracks.append(Track(path=f, repeats=1))
    return tracks


def scan_paths(paths: List[str]) -> List[Track]:
    """파일 및 폴더 경로 목록에서 개별 오디오 트랙 스캔"""
    tracks: List[Track] = []
    for path_str in paths:
        p = Path(path_str)
        if p.is_dir():
            tracks.extend(scan_folder(str(p)))
        elif p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
            tracks.append(Track(path=p, repeats=1))
    return tracks


def format_ms(ms: int) -> str:
    """밀리초(ms) 단위를 MM:SS 또는 HH:MM:SS 시각적 텍스트로 변환"""
    if ms <= 0:
        return "00:00"
    s = ms // 1000
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"


def build_concat_manifest(tracks: List[Track]) -> Tuple[str, List[Path]]:
    """FFmpeg concat 모듈용 임시 텍스트 매니페스트 생성"""
    import tempfile

    seq: List[Path] = []
    for t in tracks:
        reps = max(0, int(t.repeats))
        if reps > 0:
            seq.extend([t.path] * reps)

    if not seq:
        raise ValueError("합칠 오디오 트랙이 없습니다 (모든 트랙의 반복 횟수가 0).")

    tmp = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
    with tmp as f:
        for p in seq:
            clean_p = str(p.resolve()).replace("\\", "/").replace("'", r"'\''")
            f.write(f"file '{clean_p}'\n")

    return tmp.name, seq


class PlayQueue:
    """
    재생 큐 관리자
    - order: UI에서 정렬된 트랙 리스트
    - build_queue(): 각 트랙의 repeats 횟수만큼 재생 큐 생성
    - pop_next(): 다음 재생 파일 반환
    """

    def __init__(self):
        self.order: List[Track] = []
        self._q: Deque[Path] = deque()

    def set_order(self, tracks: List[Track]):
        self.order = tracks

    def build_queue(self):
        self._q.clear()
        for t in self.order:
            reps = max(0, int(t.repeats))
            for _ in range(reps):
                self._q.append(t.path)

    def clear(self):
        self._q.clear()

    def has_next(self) -> bool:
        return len(self._q) > 0

    def pop_next(self) -> Optional[Path]:
        if not self._q:
            return None
        return self._q.popleft()

    def remaining_count(self) -> int:
        return len(self._q)

    def total_expected_duration_ms(self) -> int:
        """반복 횟수가 반영된 총 예정 재생 시간 계산"""
        return sum(t.total_repeats_duration_ms for t in self.order)
