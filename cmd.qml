import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.3
import Vedder.vesc.commands 1.0

Item {
    anchors.fill: parent
    anchors.margins: 10

    property Commands mCommands: VescIf.commands()

    function sendCmd(cmd) {
        var buffer = new ArrayBuffer(1)
        var dv = new DataView(buffer)
        dv.setUint8(0, cmd)
        mCommands.sendCustomAppData(buffer)
        console.log("TX CMD:", cmd)
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 10

        Button {
            text: "▶ Forward"
            Layout.fillWidth: true
            onClicked: sendCmd(1)
        }

        Button {
            text: "◀ Reverse"
            Layout.fillWidth: true
            onClicked: sendCmd(2)
        }

        Button {
            text: "■ Stop"
            Layout.fillWidth: true
            onClicked: sendCmd(0)
        }
    }
}
