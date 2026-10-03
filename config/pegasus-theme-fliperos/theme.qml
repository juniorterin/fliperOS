// FliperOS 240p: tema do Pegasus para tubo de 15 kHz. O tema padrao (Grid)
// desenha para 720 linhas e escala tudo: em 320x240 o texto fica com 4
// pixels. Aqui as medidas sao em pixels de uma tela de 240 linhas (px), com
// texto de 12 pixels na lista: o nome do sistema em cima, a lista dos jogos
// a esquerda e a imagem do jogo (captura, senao a capa) com os dados dele a
// direita. Esquerda/direita (ou L/R) trocam de sistema, cima/baixo de jogo,
// L2/R2 pulam dez. Cores do Dracula, como o resto do FliperOS.
import QtQuick 2.7

FocusScope {
    id: root

    // Em 480 linhas tudo dobra; nunca menor que em 240.
    readonly property real s: Math.max(1, height / 240)
    function px(v) { return Math.round(v * s); }

    readonly property color cBg: "#282a36"
    readonly property color cBar: "#44475a"
    readonly property color cText: "#f8f8f2"
    readonly property color cDim: "#6272a4"
    readonly property color cPurple: "#bd93f9"
    readonly property color cPink: "#ff79c6"
    readonly property color cCyan: "#8be9fd"
    readonly property color cYellow: "#f1fa8c"

    property int collectionIndex: 0
    readonly property var collection: api.collections.count > 0 ? api.collections.get(collectionIndex) : null
    readonly property var game: collection && collection.games.count > 0
        ? collection.games.get(list.currentIndex) : null

    function setCollection(index) {
        var n = api.collections.count;
        if (n === 0)
            return;
        collectionIndex = (index % n + n) % n;
        list.currentIndex = 0;
    }

    function launch() {
        if (!game)
            return;
        // Ao voltar do jogo, o mesmo sistema e o mesmo jogo.
        api.memory.set("collection", collectionIndex);
        api.memory.set("game", list.currentIndex);
        game.launch();
    }

    Component.onCompleted: {
        var c = api.memory.get("collection") || 0;
        collectionIndex = c < api.collections.count ? c : 0;
        var g = api.memory.get("game") || 0;
        list.currentIndex = collection && g < collection.games.count ? g : 0;
        list.positionViewAtIndex(list.currentIndex, ListView.Center);
    }

    Rectangle {
        anchors.fill: parent
        color: cBg
    }

    // O sistema e a posicao na lista.
    Rectangle {
        id: header
        anchors { top: parent.top; left: parent.left; right: parent.right }
        height: px(24)
        color: cBar

        Text {
            anchors { left: parent.left; leftMargin: px(8); right: counter.left; rightMargin: px(6)
                      verticalCenter: parent.verticalCenter }
            text: collection ? collection.name : "No games"
            color: cPurple
            font { family: globalFonts.sans; pixelSize: px(14); bold: true }
            elide: Text.ElideRight
        }
        Text {
            id: counter
            anchors { right: parent.right; rightMargin: px(8); verticalCenter: parent.verticalCenter }
            text: collection && collection.games.count > 0
                ? (list.currentIndex + 1) + "/" + collection.games.count : ""
            color: cCyan
            font { family: globalFonts.sans; pixelSize: px(11) }
        }
    }

    ListView {
        id: list
        anchors { top: header.bottom; topMargin: px(4); bottom: footer.top; bottomMargin: px(2)
                  left: parent.left; leftMargin: px(4) }
        width: px(158)
        clip: true
        focus: true
        model: collection ? collection.games : 0
        keyNavigationWraps: true
        highlightMoveDuration: 0
        preferredHighlightBegin: height / 2 - px(8)
        preferredHighlightEnd: height / 2 + px(8)
        highlightRangeMode: ListView.ApplyRange

        delegate: Rectangle {
            width: ListView.view.width
            height: px(16)
            color: ListView.isCurrentItem ? cPurple : "transparent"

            Text {
                anchors { left: parent.left; leftMargin: px(4); right: parent.right; rightMargin: px(3)
                          verticalCenter: parent.verticalCenter }
                text: modelData.title
                color: parent.ListView.isCurrentItem ? cBg : cText
                font { family: globalFonts.sans; pixelSize: px(12); bold: parent.ListView.isCurrentItem }
                elide: Text.ElideRight
            }
        }

        Keys.onLeftPressed: setCollection(collectionIndex - 1)
        Keys.onRightPressed: setCollection(collectionIndex + 1)
        Keys.onPressed: {
            if (api.keys.isAccept(event)) {
                event.accepted = true;
                if (!event.isAutoRepeat)
                    launch();
            } else if (api.keys.isPrevPage(event)) {
                event.accepted = true;
                setCollection(collectionIndex - 1);
            } else if (api.keys.isNextPage(event)) {
                event.accepted = true;
                setCollection(collectionIndex + 1);
            } else if (api.keys.isPageUp(event)) {
                event.accepted = true;
                currentIndex = Math.max(0, currentIndex - 10);
            } else if (api.keys.isPageDown(event)) {
                event.accepted = true;
                currentIndex = Math.min(count - 1, currentIndex + 10);
            }
        }
    }

    // A imagem do jogo e os dados dele.
    Item {
        id: info
        anchors { top: header.bottom; topMargin: px(6); bottom: footer.top; bottomMargin: px(2)
                  left: list.right; leftMargin: px(6); right: parent.right; rightMargin: px(6) }

        Rectangle {
            id: frame
            anchors { top: parent.top; left: parent.left; right: parent.right }
            height: Math.round(width * 3 / 4)
            color: "#21222c"

            Image {
                id: picture
                anchors.fill: parent
                source: game ? (game.assets.screenshot || game.assets.boxFront || game.assets.logo) : ""
                sourceSize { width: px(320); height: px(240) }
                fillMode: Image.PreserveAspectFit
                asynchronous: true
                smooth: true
            }
            Text {
                anchors { fill: parent; margins: px(4) }
                visible: picture.status !== Image.Ready
                text: game ? game.title : ""
                color: cDim
                font { family: globalFonts.sans; pixelSize: px(12); bold: true }
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }
        Text {
            id: title
            anchors { top: frame.bottom; topMargin: px(5); left: parent.left; right: parent.right }
            text: game ? game.title : ""
            color: cPink
            font { family: globalFonts.sans; pixelSize: px(11); bold: true }
            wrapMode: Text.WordWrap
            maximumLineCount: 2
            elide: Text.ElideRight
        }
        Text {
            id: facts
            anchors { top: title.bottom; topMargin: px(2); left: parent.left; right: parent.right }
            text: {
                if (!game)
                    return "";
                var parts = [];
                if (game.releaseYear > 0)
                    parts.push(game.releaseYear);
                if (game.developer)
                    parts.push(game.developer);
                if (game.players > 1)
                    parts.push(game.players + "P");
                return parts.join(" - ");
            }
            color: cYellow
            font { family: globalFonts.sans; pixelSize: px(10) }
            elide: Text.ElideRight
        }
        Text {
            anchors { top: facts.bottom; topMargin: px(3); bottom: parent.bottom; left: parent.left; right: parent.right }
            text: game ? game.description : ""
            color: cText
            font { family: globalFonts.sans; pixelSize: px(10) }
            wrapMode: Text.WordWrap
            elide: Text.ElideRight
            clip: true
        }
    }

    Rectangle {
        id: footer
        anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
        height: px(14)
        color: cBar

        Text {
            anchors { left: parent.left; leftMargin: px(8); verticalCenter: parent.verticalCenter }
            text: "< > System    A Start    B Menu"
            color: cText
            font { family: globalFonts.sans; pixelSize: px(9) }
        }
    }
}
