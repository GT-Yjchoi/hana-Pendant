// 자동운전 페이지 QML(GPU). 렌더/스크롤만, 로직 Python.
// 좌:축(2) 중:IO(4) 우:제어+속도+정보(4). 외형 QWidget 판 재현.
// 바인딩은 backend null-guard (context property 초기평가 안전).
import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    color: "#660F161E"; radius: 16
    border.color: "#23FFFFFF"; border.width: 1

    property var bs: autoBackend ? autoBackend.btnStates : []
    property var ss: autoBackend ? autoBackend.subStates : []
    property int spd: autoBackend ? autoBackend.speedLevel : 10
    property string spdCol: autoBackend ? autoBackend.speedColor : "#2ECC71"

    RowLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 20

        // ── LEFT 축 (2) ──
        ColumnLayout {
            Layout.preferredWidth: 2; Layout.fillWidth: true; Layout.fillHeight: true
            spacing: 8
            Text { text: "현재 위치"; color: "#DDDDDD"; font.pixelSize: 18; font.bold: true }
            Repeater {
                model: axisModel
                delegate: RowLayout {
                    visible: model.avisible
                    Layout.fillWidth: true; height: visible ? 44 : 0; spacing: 6
                    Text { text: model.aname; color: "#CCCCCC"; font.pixelSize: 18
                           font.bold: true; Layout.preferredWidth: 36 }
                    Rectangle {
                        Layout.fillWidth: true; height: 40; radius: 6
                        color: "#14FFFFFF"; border.color: "#23FFFFFF"; border.width: 1
                        RowLayout {
                            anchors.fill: parent; anchors.rightMargin: 6
                            Text { Layout.fillWidth: true; horizontalAlignment: Text.AlignRight
                                   text: model.avalue; color: "white"; font.pixelSize: 22; font.bold: true }
                            Text { text: "mm"; color: "#A0E9EEF3"; font.pixelSize: 13
                                   font.bold: true; Layout.preferredWidth: 28 }
                        }
                    }
                }
            }
            Item { Layout.fillHeight: true }
        }

        // ── MIDDLE IO (4) ──
        RowLayout {
            Layout.preferredWidth: 4; Layout.fillWidth: true; Layout.fillHeight: true
            spacing: 14
            ColumnLayout {
                Layout.fillWidth: true; Layout.fillHeight: true
                Text { text: ioBackend ? ioBackend.inTitle : ""; color: "#E9EEF3"
                       font.pixelSize: 16; font.bold: true }
                ListView {
                    Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                    model: ioInModel; cacheBuffer: 1200; spacing: 8
                    boundsBehavior: Flickable.StopAtBounds
                    delegate: Row {
                        spacing: 10
                        Rectangle { width: 34; height: 22; radius: 10
                            color: model.on ? "#F5468CFF" : "#E6000000"
                            border.width: 1; border.color: model.on ? "#DC8CC8FF" : "#23FFFFFF" }
                        Text { text: model.label; color: "#E9EEF3"; font.pixelSize: 15
                               anchors.verticalCenter: parent.verticalCenter }
                    }
                }
            }
            ColumnLayout {
                Layout.fillWidth: true; Layout.fillHeight: true
                Text { text: ioBackend ? ioBackend.outTitle : ""; color: "#E9EEF3"
                       font.pixelSize: 16; font.bold: true }
                ListView {
                    Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                    model: ioOutModel; cacheBuffer: 1200; spacing: 8
                    boundsBehavior: Flickable.StopAtBounds
                    delegate: Row {
                        spacing: 10
                        Rectangle { width: 34; height: 22; radius: 10
                            color: model.on ? "#F5FF6923" : "#E6000000"
                            border.width: 1; border.color: model.on ? "#DCFFAA78" : "#23FFFFFF" }
                        Text { text: model.label; color: "#E9EEF3"; font.pixelSize: 15
                               anchors.verticalCenter: parent.verticalCenter }
                    }
                }
            }
        }

        // ── RIGHT 제어 (4) ──
        ColumnLayout {
            Layout.preferredWidth: 4; Layout.fillWidth: true; Layout.fillHeight: true
            spacing: 12

            RowLayout {
                Layout.fillWidth: true; Layout.fillHeight: false
                Layout.preferredHeight: 90; Layout.maximumHeight: 90
                spacing: 15
                Repeater {
                    model: 3
                    delegate: Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 90; radius: 14
                        property var st: root.bs[index]
                        color: st ? st.bg : "#3E4A59"
                        border.width: 3; border.color: st ? st.bd : "#2C3E50"
                        Text { anchors.centerIn: parent; text: st ? st.text : ""
                               color: st ? st.fg : "#95A5A6"
                               font.pixelSize: 20; font.bold: true }
                        MouseArea { anchors.fill: parent
                            onClicked: if (autoBackend) autoBackend.ctrlClicked(index) }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true; Layout.fillHeight: false
                Layout.preferredHeight: 50; Layout.maximumHeight: 50
                spacing: 10
                visible: autoBackend ? autoBackend.subVisible : false
                Repeater {
                    model: 2
                    delegate: Rectangle {
                        Layout.fillWidth: true; Layout.preferredHeight: 50; radius: 8
                        property var st: root.ss[index]
                        color: st ? st.bg : "#34495E"
                        border.width: 1; border.color: "#555555"
                        Text { anchors.centerIn: parent; text: index === 0 ? "START" : "PAUSE"
                               color: st ? st.fg : "#BBBBBB"; font.pixelSize: 16; font.bold: true }
                        MouseArea { anchors.fill: parent
                            onClicked: if (autoBackend) autoBackend.subClicked(index) }
                    }
                }
            }

            Item { Layout.fillHeight: true }

            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 150
                color: "#0DFFFFFF"; radius: 10
                border.color: "#444444"; border.width: 1
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 15; spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        Text { text: "전체속도"; color: "#DDDDDD"
                               font.pixelSize: 16; font.bold: true }
                        Item { Layout.fillWidth: true }
                        Text { text: root.spd + " / 10"; color: root.spdCol
                               font.pixelSize: 22; font.bold: true }
                    }
                    RowLayout {
                        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 10
                        Rectangle {
                            Layout.preferredWidth: 55; Layout.fillHeight: true
                            radius: 8; color: spdMinus.pressed ? "#2C3E50" : "#34495E"
                            border.color: "#555555"; border.width: 1
                            Text { anchors.centerIn: parent; text: "−"; color: "white"
                                   font.pixelSize: 26; font.bold: true }
                            MouseArea { id: spdMinus; anchors.fill: parent
                                onClicked: if (autoBackend) autoBackend.changeSpeed(-1) }
                        }
                        Row {
                            id: stair
                            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 3
                            Repeater {
                                model: 10
                                delegate: Rectangle {
                                    width: (stair.width - 27) / 10
                                    height: stair.height * (index + 1) / 10
                                    anchors.bottom: parent.bottom
                                    radius: 3
                                    color: index < root.spd ? root.spdCol : "#28303C"
                                    border.width: index < root.spd ? 0 : 1
                                    border.color: "#505A64"
                                }
                            }
                        }
                        Rectangle {
                            Layout.preferredWidth: 55; Layout.fillHeight: true
                            radius: 8; color: spdPlus.pressed ? "#2C3E50" : "#34495E"
                            border.color: "#555555"; border.width: 1
                            Text { anchors.centerIn: parent; text: "+"; color: "white"
                                   font.pixelSize: 26; font.bold: true }
                            MouseArea { id: spdPlus; anchors.fill: parent
                                onClicked: if (autoBackend) autoBackend.changeSpeed(1) }
                        }
                    }
                }
            }

            Item { Layout.fillHeight: true }

            Rectangle {
                Layout.fillWidth: true; Layout.preferredHeight: 150
                color: "transparent"; radius: 12
                border.color: "#33FFFFFF"; border.width: 1
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 18; spacing: 10
                    Text { text: autoBackend ? autoBackend.infoTitle : ""
                           color: "#DDDDDD"; font.pixelSize: 16; font.bold: true }
                    Repeater {
                        model: autoBackend ? autoBackend.infoRows : []
                        delegate: RowLayout {
                            Layout.fillWidth: true
                            Text { text: modelData.name; color: "#CCCCCC"
                                   font.pixelSize: 16; font.bold: true }
                            Item { Layout.fillWidth: true }
                            Text { text: modelData.val; color: "white"
                                   font.pixelSize: 18; font.bold: true }
                        }
                    }
                    Item { Layout.fillHeight: true }
                }
            }
        }
    }
}
