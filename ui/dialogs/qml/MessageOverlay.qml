// 시퀀스 편집기 팝업 공용 QML(GPU). 메시지/확인 다이얼로그 렌더.
// 배경(부모 윈도우 그랩)+딤도 여기서 그림 → QQuickWidget 불투명 사용
// (Mali alpha=0 환경에서 투명 합성 함정 회피).
import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root
    color: "#141923"

    // 부모 윈도우 그랩 배경 + 어둡게(딤)
    Image {
        anchors.fill: parent
        source: "image://ovbg/bg"
        fillMode: Image.Stretch
        asynchronous: false
        cache: false
    }
    Rectangle { anchors.fill: parent; color: "#96000000" }

    // 중앙 컨텐츠 프레임
    Rectangle {
        id: frame
        anchors.centerIn: parent
        width: ov ? ov.frameW : 440
        height: ov ? ov.frameH : 240
        radius: 12
        color: "#1E232D"
        border.width: 2
        border.color: ov ? ov.accent : "#468CFF"

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 14

            Text {
                Layout.fillWidth: true
                text: ov ? ov.title : ""
                color: ov ? ov.accent : "#468CFF"
                font.pixelSize: 22; font.bold: true
                wrapMode: Text.WordWrap
            }
            Text {
                Layout.fillWidth: true
                Layout.fillHeight: true
                text: ov ? ov.message : ""
                color: "white"
                font.pixelSize: 18; font.bold: true
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
            RowLayout {
                Layout.fillWidth: true
                Layout.preferredHeight: 52
                spacing: 12

                // 취소(2버튼 모드에서만)
                Rectangle {
                    visible: ov ? ov.twoButtons : false
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 8
                    color: noMa.pressed ? "#50FF4646" : "#28FF4646"
                    border.width: 1; border.color: "#64FF4646"
                    Text { anchors.centerIn: parent; text: "취소"
                           color: "white"; font.pixelSize: 17; font.bold: true }
                    MouseArea { id: noMa; anchors.fill: parent
                        onClicked: if (ov) ov.reject() }
                }
                // 확인
                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 8
                    color: okMa.pressed ? "#50468CFF" : "#28468CFF"
                    border.width: 1; border.color: "#64468CFF"
                    Text { anchors.centerIn: parent; text: "확인"
                           color: "white"; font.pixelSize: 17; font.bold: true }
                    MouseArea { id: okMa; anchors.fill: parent
                        onClicked: if (ov) ov.accept() }
                }
            }
        }
    }
}
