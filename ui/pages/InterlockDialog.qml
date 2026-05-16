// 인터록 그룹 설정 QML(GPU). 로직(그룹순환·배타·필수·전체해제)은
// Python(backend)에서 page_mode.InterlockDialog 와 동일(verbatim).
import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    color: "#111827"

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 8

        // ── 헤더 ──
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: false
            Layout.preferredHeight: 40
            Text { text: "인터록 그룹 설정"; color: "#00E5FF"
                   font.pixelSize: 20; font.bold: true }
            Item { Layout.fillWidth: true }
            Rectangle {
                Layout.preferredWidth: 110; Layout.preferredHeight: 34
                radius: 6; color: clrMa.pressed ? "#66FF4646" : "#33FF4646"
                border.color: "#FF4646"; border.width: 1
                Text { anchors.centerIn: parent; text: "전체 해제"
                       color: "#FF4646"; font.pixelSize: 13; font.bold: true }
                MouseArea { id: clrMa; anchors.fill: parent
                    onClicked: if (ilBackend) ilBackend.clearAll() }
            }
        }
        Rectangle { Layout.fillWidth: true; height: 1; color: "#374151" }

        // ── 그룹 옵션 카드 ──
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: false
            Layout.preferredHeight: 96
            spacing: 8
            Repeater {
                model: ilGroupModel
                delegate: Rectangle {
                    Layout.preferredWidth: 112; Layout.fillHeight: true
                    radius: 8; color: model.gcardbg
                    border.color: model.gcardborder; border.width: 1
                    ColumnLayout {
                        anchors.fill: parent; anchors.margins: 6; spacing: 4
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 24
                            radius: 5; color: model.glabelbg
                            Text { anchors.centerIn: parent; text: model.glabel
                                   color: "white"; font.pixelSize: 15; font.bold: true }
                        }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 30
                            radius: 5; color: model.exbg
                            border.color: model.exborder; border.width: model.exbw
                            Text { anchors.centerIn: parent; text: model.extext
                                   color: model.exfg; font.pixelSize: 12; font.bold: true }
                            MouseArea { anchors.fill: parent
                                onClicked: if (ilBackend)
                                    ilBackend.toggleExclusive(model.gnum) }
                        }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 30
                            radius: 5; color: model.mnbg
                            border.color: model.mnborder; border.width: model.mnbw
                            Text { anchors.centerIn: parent; text: model.mntext
                                   color: model.mnfg; font.pixelSize: 12; font.bold: true }
                            MouseArea { anchors.fill: parent
                                onClicked: if (ilBackend)
                                    ilBackend.toggleMandatory(model.gnum) }
                        }
                    }
                }
            }
            Item { Layout.fillWidth: true }
        }

        Text {
            Layout.fillWidth: true
            text: "모드 버튼을 탭하면 그룹 순환 (없음 → G1 → … → G8 → 없음).  "
                + "배타: 하나 ON 시 나머지 자동 OFF.  필수: 마지막 하나는 끌 수 없음."
            color: "#9CA3AF"; font.pixelSize: 13; wrapMode: Text.WordWrap
        }

        // ── 모드 그리드 ──
        GridView {
            id: gv
            Layout.fillWidth: true; Layout.fillHeight: true
            clip: true; model: ilModeModel
            cacheBuffer: 2000
            boundsBehavior: Flickable.StopAtBounds
            cellWidth: Math.floor(width / 4)
            cellHeight: 76
            delegate: Item {
                width: gv.cellWidth; height: gv.cellHeight
                Rectangle {
                    anchors.fill: parent; anchors.margins: 5
                    radius: 8; color: model.mbg
                    border.color: model.mborder; border.width: model.mbw
                    Text { anchors.centerIn: parent
                           horizontalAlignment: Text.AlignHCenter
                           text: model.mtext; color: model.mfg
                           font.pixelSize: 13; font.bold: true }
                    MouseArea { anchors.fill: parent
                        onClicked: if (ilBackend) ilBackend.cycleGroup(index) }
                }
            }
        }

        // ── 하단 ──
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: false
            Layout.preferredHeight: 46
            spacing: 10
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true
                radius: 8; color: cxMa.pressed ? "#33FFFFFF" : "#14FFFFFF"
                border.color: "#555555"; border.width: 1
                Text { anchors.centerIn: parent; text: "취소"
                       color: "#CCCCCC"; font.pixelSize: 16; font.bold: true }
                MouseArea { id: cxMa; anchors.fill: parent
                    onClicked: if (ilBackend) ilBackend.reject() }
            }
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true
                radius: 8; color: okMa.pressed ? "#5900E5FF" : "#2600E5FF"
                border.color: "#00E5FF"; border.width: 1
                Text { anchors.centerIn: parent; text: "저장"
                       color: "#00E5FF"; font.pixelSize: 16; font.bold: true }
                MouseArea { id: okMa; anchors.fill: parent
                    onClicked: if (ilBackend) ilBackend.accept() }
            }
        }
    }
}
