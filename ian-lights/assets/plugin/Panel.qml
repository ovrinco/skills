import QtQuick
import QtQuick.Controls as C
import QtQuick.Dialogs as D
import Quickshell
import Quickshell.Io
import qs.Ui
import qs.Commons

Panel {
    id: root
    moduleName: "ian.ovrin-rgb"
    ipcTarget: "ian.ovrin-rgb"
    implicitWidth: Style.bar.iconSlot
    implicitHeight: bar ? bar.barSize : Style.space(26)
    property var snapshot: ({lights: [], presets: []})
    property string error: ""
    property string editingLight: ""
    property string pendingAction: ""
    function request(payload) {
        if (worker.running) return
        error = ""
        pendingAction = payload.action
        worker.command = ["/usr/bin/python3", Qt.resolvedUrl("control.py").toString().replace("file://", ""), JSON.stringify(payload)]
        worker.running = true
    }
    function choose(light) {
        editingLight = light.key
        picker.title = light.name
        picker.selectedColor = light.color
        picker.open()
    }
    Process {
        id: worker
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    let reply = JSON.parse(text)
                    if (reply.ok) {
                        root.snapshot = reply
                        if (root.pendingAction === "save-preset") presetName.text = ""
                    } else root.error = reply.error
                } catch (e) { root.error = "Could not update the lights. Try again." }
            }
        }
        stderr: StdioCollector {}
    }
    Component.onCompleted: request({action: "status"})
    onOpenedChanged: if (opened) request({action: "status"})
    D.ColorDialog {
        id: picker
        options: D.ColorDialog.NoEyeDropperButton
        onAccepted: {
            root.request({action: "color", light: root.editingLight, color: selectedColor.toString()})
            root.open()
        }
        onRejected: root.open()
    }
    BarIconButton {
        id: lamp
        anchors.fill: parent
        bar: root.bar
        text: "󰏘"
        foreground: root.barForeground
        tooltipText: "Lights"
        onPressed: function(b) { root.toggle() }
    }
    KeyboardPanel {
        anchorItem: lamp
        owner: root
        bar: root.bar
        open: root.opened
        contentWidth: fittedContentWidth(Style.space(340))
        contentHeight: fittedContentHeight(body.implicitHeight, Style.space(560))
        focusTarget: presetName
        C.ScrollView {
            id: scroll
            anchors.fill: parent
            clip: true
            C.ScrollBar.horizontal.policy: C.ScrollBar.AlwaysOff
            Keys.onEscapePressed: root.close()
            Column {
                id: body
                width: scroll.availableWidth
                spacing: Style.space(12)
                Text { text: "Lights"; color: Color.foreground; font.family: Style.font.family; font.pixelSize: Style.font.title; font.bold: true }
                Repeater {
                    model: root.snapshot.lights
                    Row {
                        required property var modelData
                        width: body.width
                        spacing: Style.space(12)
                        Text {
                            width: parent.width - swatch.width - parent.spacing
                            anchors.verticalCenter: parent.verticalCenter
                            text: parent.modelData.name
                            color: Color.foreground
                            font.family: Style.font.family
                            font.pixelSize: Style.font.body
                        }
                        Button {
                            id: swatch
                            width: Style.space(68)
                            height: Style.space(32)
                            background: parent.modelData.color
                            bordered: true
                            focusable: true
                            enabled: !worker.running
                            tooltipText: "Change " + parent.modelData.name.toLowerCase()
                            onClicked: root.choose(parent.modelData)
                        }
                    }
                }
                Rectangle { width: parent.width; height: 1; color: Qt.alpha(Color.muted, .25) }
                Text { text: "Presets"; color: Color.foreground; font.family: Style.font.family; font.pixelSize: Style.font.body; font.bold: true }
                Row {
                    width: parent.width
                    spacing: Style.space(8)
                    TextField {
                        id: presetName
                        width: parent.width - saveButton.implicitWidth - parent.spacing
                        placeholderText: "Preset name"
                        maximumLength: 40
                        onAccepted: if (text.trim() && !worker.running) root.request({action: "save-preset", name: text})
                    }
                    Button {
                        id: saveButton
                        text: "Save"
                        bordered: true
                        focusable: true
                        enabled: presetName.text.trim().length > 0 && !worker.running
                        onClicked: root.request({action: "save-preset", name: presetName.text})
                    }
                }
                Repeater {
                    model: root.snapshot.presets
                    Row {
                        required property var modelData
                        width: body.width
                        spacing: Style.space(8)
                        Button {
                            width: parent.width - deleteButton.width - parent.spacing
                            text: parent.modelData.name
                            leftAlign: true
                            bordered: true
                            focusable: true
                            enabled: !worker.running
                            onClicked: root.request({action: "load-preset", id: parent.modelData.id})
                        }
                        Button {
                            id: deleteButton
                            iconText: "󰆴"
                            tooltipText: "Delete " + parent.modelData.name
                            focusable: true
                            enabled: !worker.running
                            onClicked: root.request({action: "delete-preset", id: parent.modelData.id})
                        }
                    }
                }
                Text {
                    width: parent.width
                    visible: root.error.length > 0
                    text: root.error
                    wrapMode: Text.WordWrap
                    color: Color.urgent
                    font.family: Style.font.family
                    font.pixelSize: Style.font.bodySmall
                }
            }
        }
    }
}
