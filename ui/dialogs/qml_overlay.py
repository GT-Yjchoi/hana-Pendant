"""시퀀스 편집기 팝업 GPU(QML) 공용 프레임워크.

설계 원칙(사용자 합의): 각 팝업의 Python 계약(생성자 인자 · .exec()
반환값 · 선택값 속성)을 100% 그대로 두고, **내부 렌더만 QML(GPU)** 로
바꾼다. 모달 인프라는 QDialog 그대로(.exec()/accept/reject/deleteLater)
→ sequence_editor_dialog.py 호출부·PLC 전송 로직 무수정.

- 기존 OverlayDialog 와 동일하게: 프레임리스 풀스크린, 부모 윈도우
  그랩을 어둡게 깐 위에 중앙 프레임, .exec() 모달, 닫힐 때 deleteLater.
- 배경 그랩+딤은 QML 안에서 그림 → QQuickWidget 은 불투명 사용
  (Mali alpha=0 환경의 투명 합성 함정 회피).
"""
import os

from PySide6.QtCore import Qt, QUrl, QObject, Signal, Slot, Property
from PySide6.QtGui import QColor, QImage
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import QDialog, QVBoxLayout

_QML_DIR = os.path.join(os.path.dirname(__file__), "qml")


class _BgProvider(QQuickImageProvider):
    """부모 윈도우 그랩(딤 배경)을 QML image://ovbg/bg 로 제공."""

    def __init__(self, image):
        super().__init__(QQuickImageProvider.Image)
        if image is None or image.isNull():
            image = QImage(8, 8, QImage.Format_RGB32)
            image.fill(QColor("#141923"))
        self._img = image

    def requestImage(self, _id, size, _requested):
        if size is not None:
            size.setWidth(self._img.width())
            size.setHeight(self._img.height())
        return self._img


class QmlOverlayDialog(QDialog):
    """OverlayDialog 와 동일 계약(.exec()/accept/reject/deleteLater),
    내부 렌더만 QML. 서브클래스는 _setup(ctx)에서 context property 를
    설정한 뒤 _load(qml_file) 를 호출한다."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog
                            | Qt.WindowStaysOnTopHint)
        self.setWindowState(Qt.WindowFullScreen)

        pm = parent.window().grab() if parent else None
        bg = pm.toImage() if pm is not None else None

        self._view = QQuickWidget(self)
        self._view.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self._view.setClearColor(QColor("#141923"))
        self._view.engine().addImageProvider("ovbg", _BgProvider(bg))

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._view)

    def _load(self, qml_file):
        self._view.setSource(QUrl.fromLocalFile(os.path.join(_QML_DIR, qml_file)))

    def exec(self):
        # OverlayDialog 와 동일: 닫힌 뒤 명시적 삭제(터치 인식기 누적 방지).
        result = super().exec()
        self.deleteLater()
        return result


class _MsgBackend(QObject):
    changed = Signal()

    def __init__(self, dlg, title, message, accent, two_buttons, fw, fh):
        super().__init__(dlg)
        self._dlg = dlg
        self._title = title
        self._message = message
        self._accent = accent
        self._two = two_buttons
        self._fw = fw
        self._fh = fh

    title = Property(str, lambda s: s._title, notify=changed)
    message = Property(str, lambda s: s._message, notify=changed)
    accent = Property(str, lambda s: s._accent, notify=changed)
    twoButtons = Property(bool, lambda s: s._two, notify=changed)
    frameW = Property(int, lambda s: s._fw, notify=changed)
    frameH = Property(int, lambda s: s._fh, notify=changed)

    @Slot()
    def accept(self):
        self._dlg.accept()

    @Slot()
    def reject(self):
        self._dlg.reject()


class QmlMessageDialog(QmlOverlayDialog):
    """메시지/확인 공용. two_buttons=False → 확인만, True → 취소+확인.
    .exec() 는 QDialog.Accepted/Rejected 반환(기존과 동일 계약)."""

    def __init__(self, title, message, accent="#468CFF",
                 two_buttons=False, frame_w=440, frame_h=240, parent=None):
        super().__init__(parent)
        self._be = _MsgBackend(self, title, message, accent,
                               two_buttons, frame_w, frame_h)
        self._view.rootContext().setContextProperty("ov", self._be)
        self._load("MessageOverlay.qml")
