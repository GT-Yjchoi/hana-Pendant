"""
인터록 그룹 설정 QML(GPU) — page_mode.InterlockDialog drop-in.

생성자/메서드 동일: (groups, mandatory, exclusive, get_name_fn,
group_colors, parent) / exec()→1|0 / get_groups/get_mandatory/get_exclusive.
그룹순환·배타·필수·전체해제 로직은 page_mode.InterlockDialog 와
문자 단위 동일(verbatim). QQuickWidget 위 top-level 모달.
"""
from PySide6.QtCore import (Qt, QObject, Signal, Slot, QUrl, QEventLoop,
                            QAbstractListModel, QModelIndex, QByteArray)
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtQuickWidgets import QQuickWidget
import os

from ui.pages.page_mode import TOTAL_SLOTS

_QML_PATH = os.path.join(os.path.dirname(__file__), "InterlockDialog.qml")


def _alpha(hex_color, aa):
    """'#RRGGBB' + 'AA' → '#AARRGGBB' (QML 색)."""
    return "#" + aa + hex_color[1:]


class _LM(QAbstractListModel):
    def __init__(self, roles, parent=None):
        super().__init__(parent)
        self._roles = {Qt.UserRole + 1 + i: QByteArray(r.encode())
                       for i, r in enumerate(roles)}
        self._rn = list(roles)
        self._rows = []

    def rowCount(self, p=QModelIndex()):
        return len(self._rows)

    def roleNames(self):
        return self._roles

    def data(self, ix, role):
        i = ix.row()
        if 0 <= i < len(self._rows):
            return self._rows[i].get(self._rn[role - (Qt.UserRole + 1)])
        return None

    def reset(self, rows):
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def update_row(self, i, d):
        if 0 <= i < len(self._rows):
            self._rows[i].update(d)
            self.dataChanged.emit(self.index(i, 0), self.index(i, 0),
                                  list(self._roles.keys()))


class _ILBackend(QObject):
    def __init__(self, dlg):
        super().__init__(dlg)
        self._d = dlg

    @Slot(int)
    def cycleGroup(self, idx):
        self._d._cycle_group(idx)

    @Slot(int)
    def toggleExclusive(self, g):
        self._d._toggle_exclusive(g)

    @Slot(int)
    def toggleMandatory(self, g):
        self._d._toggle_mandatory(g)

    @Slot()
    def clearAll(self):
        self._d._clear_all()

    @Slot()
    def accept(self):
        self._d.accept()

    @Slot()
    def reject(self):
        self._d.reject()


class InterlockDialogQml(QWidget):
    Accepted = 1
    Rejected = 0

    def __init__(self, groups, mandatory, exclusive, get_name_fn,
                 group_colors, parent=None):
        super().__init__(parent)
        self._groups = groups[:]
        self._mandatory = mandatory[:]
        self._exclusive = exclusive[:]
        self._get_name = get_name_fn
        self._colors = group_colors
        self._max_group = len(group_colors) - 1
        self._result = self.Rejected
        self._loop = None

        # QQuickWidget 위 자식 입력 가로채임 방지 — top-level 모달
        self._bg = parent.window().grab() if parent else None
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog
                            | Qt.WindowStaysOnTopHint)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowState(Qt.WindowFullScreen)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._mode_m = _LM(["mtext", "mbg", "mborder", "mbw", "mfg"], self)
        self._grp_m = _LM(["gnum", "glabel", "gcardbg", "gcardborder",
                           "glabelbg", "extext", "exbg", "exborder", "exbw",
                           "exfg", "mntext", "mnbg", "mnborder", "mnbw",
                           "mnfg"], self)
        self._be = _ILBackend(self)

        self._view = QQuickWidget(self)
        self._view.setResizeMode(QQuickWidget.SizeRootObjectToView)
        ctx = self._view.rootContext()
        ctx.setContextProperty("ilModeModel", self._mode_m)
        ctx.setContextProperty("ilGroupModel", self._grp_m)
        ctx.setContextProperty("ilBackend", self._be)
        self._view.setSource(QUrl.fromLocalFile(_QML_PATH))

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._view)

        self._build_group_rows()
        self._refresh_all()

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter, QColor
        p = QPainter(self)
        if self._bg:
            p.drawPixmap(0, 0, self._bg)
        p.fillRect(self.rect(), QColor(0, 0, 0, 150))

    # ---- 표시 계산 (page_mode 의 _refresh_* 와 동일 결과) ----
    def _mode_cell(self, idx):
        grp = self._groups[idx]
        name = self._get_name(idx)
        if grp > 0:
            tags = []
            if self._exclusive[grp]:
                tags.append("⊗")
            if self._mandatory[grp]:
                tags.append("★")
            suffix = " " + "".join(tags) if tags else ""
        else:
            suffix = ""
        if grp == 0:
            return {"mtext": f"{name}\n—", "mbg": "#0DFFFFFF",
                    "mborder": "#26FFFFFF", "mbw": 1, "mfg": "#9CA3AF"}
        c = self._colors[grp]
        return {"mtext": f"{name}\nG{grp}{suffix}", "mbg": _alpha(c, "33"),
                "mborder": c, "mbw": 2, "mfg": c}

    def _grp_card(self, g):
        c = self._colors[g]
        ex_on = self._exclusive[g]
        mn_on = self._mandatory[g]
        d = {"gnum": g, "glabel": f"G{g}",
             "gcardbg": _alpha(c, "22"), "gcardborder": _alpha(c, "66"),
             "glabelbg": c}
        if ex_on:
            d.update(extext="배타 ON ⊗", exbg=c, exborder=c, exbw=0,
                     exfg="white")
        else:
            d.update(extext="배타 OFF", exbg="#14FFFFFF", exborder="#555555",
                     exbw=1, exfg="#777777")
        if mn_on:
            d.update(mntext="필수 ON ★", mnbg=c, mnborder=c, mnbw=0,
                     mnfg="white")
        else:
            d.update(mntext="필수 OFF", mnbg="#14FFFFFF", mnborder="#555555",
                     mnbw=1, mnfg="#777777")
        return d

    def _build_group_rows(self):
        self._grp_m.reset([self._grp_card(g)
                           for g in range(1, self._max_group + 1)])

    def _refresh_group(self, g):
        # grp_m 행 인덱스 = g-1
        self._grp_m.update_row(g - 1, self._grp_card(g))

    def _refresh_all(self):
        self._mode_m.reset([self._mode_cell(i) for i in range(TOTAL_SLOTS)])

    def _refresh_btn(self, idx):
        self._mode_m.update_row(idx, self._mode_cell(idx))

    # ---- 로직 (page_mode.InterlockDialog 와 동일) ----
    def _cycle_group(self, idx):
        self._groups[idx] = (self._groups[idx] + 1) % (self._max_group + 1)
        self._refresh_btn(idx)

    def _clear_all(self):
        self._groups = [0] * TOTAL_SLOTS
        self._refresh_all()

    def _toggle_exclusive(self, g):
        self._exclusive[g] = not self._exclusive[g]
        self._refresh_group(g)
        self._refresh_all()  # 모드 버튼 suffix 갱신 (원본과 동일)

    def _toggle_mandatory(self, g):
        self._mandatory[g] = not self._mandatory[g]
        self._refresh_group(g)  # 원본은 mandatory 토글 시 grid suffix 갱신 안 함

    def get_groups(self):
        return self._groups[:]

    def get_mandatory(self):
        return self._mandatory[:]

    def get_exclusive(self):
        return self._exclusive[:]

    # ---- 모달 exec ----
    def accept(self):
        self._result = self.Accepted
        if self._loop:
            self._loop.quit()
        self.close()

    def reject(self):
        self._result = self.Rejected
        if self._loop:
            self._loop.quit()
        self.close()

    def exec(self):
        self.show()
        self.raise_()
        self.activateWindow()
        self._loop = QEventLoop()
        self._loop.exec()
        self.deleteLater()
        return self._result
