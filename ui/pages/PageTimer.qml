// 타이머 라이브러리 페이지 QML(GPU). 6열 카드 그리드 GPU 스크롤.
// active 카드 깜빡임/로직은 Python(backend) 그대로.
import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    color: "#660F161E"; radius: 16
    border.color: "#23FFFFFF"; border.width: 1

    property string activeName: timerBackend ? timerBackend.activeName : ""
    property bool blinkOn: timerBackend ? timerBackend.blinkOn : false

    // 빈 상태 안내 (GridView.count 로 판정 — raw QAbstractListModel 은
    //  QML 에 count 프로퍼티 없음. 레이아웃 밖 오버레이로 배치)
    Text {
        anchors.centerIn: parent
        width: parent.width - 40
        visible: gv.count === 0
        horizontalAlignment: Text.AlignHCenter
        text: "타이머가 없습니다.\n시퀀스 편집기 TMR 스텝에서 타이머를 추가하세요."
        color: "#66FFFFFF"; font.pixelSize: 16
        wrapMode: Text.WordWrap
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 8

        GridView {
            id: gv
            Layout.fillWidth: true; Layout.fillHeight: true
            clip: true
            model: timerModel
            cacheBuffer: 2000
            boundsBehavior: Flickable.StopAtBounds
            cellWidth: Math.floor(width / 6)
            cellHeight: 110
            delegate: Item {
                width: gv.cellWidth
                height: gv.cellHeight
                property bool isActive: model.tname === root.activeName
                Rectangle {
                    anchors.fill: parent
                    anchors.margins: 5
                    radius: 12
                    color: isActive ? (root.blinkOn ? "#162A1E" : "#111E16")
                                     : "#1A222C"
                    border.width: isActive ? 2 : 1
                    border.color: isActive ? (root.blinkOn ? "#00FF7F" : "#007A40")
                                            : "#3E4A59"
                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 6
                        spacing: 4
                        RowLayout {
                            Layout.fillWidth: true
                            Text { text: model.tname; color: "#DDDDDD"
                                   font.pixelSize: 17; font.bold: true
                                   elide: Text.ElideRight; Layout.fillWidth: true }
                            Text { text: isActive ? "▶" : ""
                                   color: "#00FF7F"; font.pixelSize: 14
                                   font.bold: true; Layout.preferredWidth: 20 }
                        }
                        Rectangle {
                            Layout.fillWidth: true; Layout.preferredHeight: 50
                            radius: 6
                            color: tMa.pressed ? "#34495E" : "#2C3E50"
                            border.width: 1
                            border.color: tMa.pressed ? "#468CFF" : "#3E4A59"
                            Text { anchors.centerIn: parent
                                   text: model.tsec; color: "#FFFF00"
                                   font.pixelSize: 22; font.bold: true }
                            MouseArea { id: tMa; anchors.fill: parent
                                onClicked: if (timerBackend)
                                    timerBackend.editTimer(model.tname) }
                        }
                    }
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: false
            Layout.preferredHeight: 40; Layout.maximumHeight: 40
            Item { Layout.fillWidth: true }
            Rectangle {
                Layout.preferredWidth: 130; Layout.preferredHeight: 36
                radius: 8
                color: roMa.pressed ? "#594692FF" : "#26468CFF"
                border.width: 1; border.color: "#80468CFF"
                Text { anchors.centerIn: parent; text: "⇄ 순서 변경"
                       color: "#7EB8FF"; font.pixelSize: 14; font.bold: true }
                MouseArea { id: roMa; anchors.fill: parent
                    onClicked: if (timerBackend) timerBackend.reorder() }
            }
        }
    }
}
