#target photoshop
app.bringToFront();

function getDesktopPath() {
    var desktopPath;
    if ($.os.match(/Windows/)) {
        var f = Folder('~/Desktop');
        desktopPath = f.fsName;
    } else {
        desktopPath = "~/Desktop";
    }
    return desktopPath;
}

function readTxtFile(filePath) {
    var file = new File(filePath);
    file.open('r');
    var content = file.read();
    file.close();
    return content;
}

function extractBarText(content) {
    var bars = [];
    var highlights = [];
    var lines = content.split('\n');
    var barStartFound = false;
    var unclosedQuotesWarnings = [];
    var saveFormat = "";
    var firstLine = lines[0];

    for (var i = 0; i < lines.length; i++) {
        var line = lines[i].replace(/^\s+|\s+$/g, '');  // 使用正則表達式去除首尾空格
        if (line.toLowerCase() === "大bar") {
            barStartFound = true;
            continue;
        }

        if (barStartFound && line !== "") {
            var cleanLine = line.replace(/"/g, '');  // 刪除所有的雙引號
            bars.push(cleanLine);
            var match = line.match(/"(.*?)"/);
            highlights.push(match ? match[1] : "");  // 去除雙引號並存儲

            // 檢查未閉合的引號
            if (hasUnclosedQuotes(line)) {
                var layerName = "大標_" + ("0" + (bars.length)).slice(-2); // 修正圖層名稱
                unclosedQuotesWarnings.push(layerName + " \"" + line + "\" 發現未閉合的引號,請跟發單者確認");
            }
        }

        // 檢查存檔格式
        if (line.toLowerCase().indexOf("png") !== -1) {
            saveFormat = "png";
        } else if (line.toLowerCase().indexOf("tga") !== -1) {
            saveFormat = "tga";
        }
    }
    return { bars: bars, highlights: highlights, warnings: unclosedQuotesWarnings, format: saveFormat, firstLine: firstLine };
}

function replaceTextLayerContent(layer, text) {
    if (layer.kind == LayerKind.TEXT) {
        var textItem = layer.textItem;
        textItem.contents = text;
    } else {
        alert("Layer is not a text layer!");
    }
}

function hasUnclosedQuotes(text) {
    var quoteCount = (text.match(/"/g) || []).length;
    return quoteCount % 2 !== 0;
}

function changeWordProperties(theRegExp) {
    var originalRulerUnits = app.preferences.rulerUnits;
    app.preferences.rulerUnits = Units.PIXELS;
    try {
        var ref = new ActionReference();
        ref.putEnumerated(charIDToTypeID("Lyr "), charIDToTypeID("Ordn"), charIDToTypeID("Trgt"));
        var layerDesc = executeActionGet(ref);
        var textDesc = layerDesc.getObjectValue(stringIDToTypeID('textKey'));
        var theText = textDesc.getString(stringIDToTypeID('textKey'));

        var antiAliasTypeID = stringIDToTypeID('antiAlias');
        var originalAntiAlias = textDesc.hasKey(antiAliasTypeID) ? textDesc.getEnumerationValue(antiAliasTypeID) : null;

        var theIndices = [];
        while ((result = theRegExp.exec(theText)) != null) {
            theIndices.push([result.index, result.index + result[0].length]);
        }

        var paragraphRangeList = textDesc.getList(stringIDToTypeID('paragraphStyleRange'));
        var kernRange = textDesc.getList(stringIDToTypeID('kerningRange'));
        var rangeList = textDesc.getList(stringIDToTypeID('textStyleRange'));

        var theFonts = [];
        var theStyleRanges = [];
        var theStyleRanges2 = [];
        for (var o = 0; o < rangeList.count; o++) {
            var thisList = rangeList.getObjectValue(o);
            var theFrom = thisList.getInteger(stringIDToTypeID('from'));
            var theTo = thisList.getInteger(stringIDToTypeID('to'));
            var styleDesc = thisList.getObjectValue(stringIDToTypeID('textStyle'));
            var aSize = styleDesc.getUnitDoubleValue(charIDToTypeID("Sz  "));
            if (styleDesc.hasKey(stringIDToTypeID('fontPostScriptName')) == true) {
                var aFont = styleDesc.getString(stringIDToTypeID('fontPostScriptName'))
            } else {
                var theDefault = styleDesc.getObjectValue(stringIDToTypeID('baseParentStyle'));
                var aFont = theDefault.getString(stringIDToTypeID('fontPostScriptName'));
            }
            theFonts.push([aFont, aSize, theFrom, theTo]);
            theStyleRanges.push(thisList.getObjectValue(stringIDToTypeID('textStyle')));
            theStyleRanges2.push(thisList.getObjectValue(stringIDToTypeID('textStyle')));
        }

        var theColors = [[222, 0, 52]];  // 設置新的顏色值
        var idPxl = charIDToTypeID("#Pxl");
        var idPnt = charIDToTypeID("#Pnt");
        var idTxtt = charIDToTypeID("Txtt");
        var idFrom = charIDToTypeID("From");
        var idT = charIDToTypeID("T   ");
        var idTxtS = charIDToTypeID("TxtS");
        var idTxLr = charIDToTypeID("TxLr");
        var idTxt = charIDToTypeID("Txt ");
        var idsetd = charIDToTypeID("setd");
        var desc6 = new ActionDescriptor();
        var idnull = charIDToTypeID("null");
        var ref1 = new ActionReference();
        ref1.putEnumerated(idTxLr, charIDToTypeID("Ordn"), charIDToTypeID("Trgt"));
        desc6.putReference(idnull, ref1);
        var desc7 = new ActionDescriptor();
        desc7.putString(idTxt, theText);
        var list2 = new ActionList();

        var indicesCount = 0;
        var targetStart = theIndices[indicesCount][0];
        var targetEnd = theIndices[indicesCount][1];
        for (var m = 0; m < theText.length; m++) {
            if (m == theFonts[indicesCount][3]) {
                indicesCount++;
                var targetStart = theIndices[indicesCount] ? theIndices[indicesCount][0] : -1;
                var targetEnd = theIndices[indicesCount] ? theIndices[indicesCount][1] : -1;
            }

            var desc14 = new ActionDescriptor();
            desc14.putInteger(idFrom, m);
            desc14.putInteger(idT, m + 1);
            var theStyle = theStyleRanges[indicesCount];

            if (m >= targetStart && m < targetEnd) {
                var desc21 = new ActionDescriptor();
                desc21.putDouble(charIDToTypeID("Rd  "), theColors[0][0]);
                desc21.putDouble(charIDToTypeID("Grn "), theColors[0][1]);
                desc21.putDouble(charIDToTypeID("Bl  "), theColors[0][2]);
                theStyle.putObject(charIDToTypeID("Clr "), charIDToTypeID("RGBC"), desc21);
                desc14.putObject(idTxtS, idTxtS, theStyle);
            } else {
                desc14.putObject(idTxtS, idTxtS, theStyleRanges2[indicesCount]);
                if (m == targetEnd && indicesCount < theIndices.length - 1) {
                    indicesCount++;
                    var targetStart = theIndices[indicesCount][0];
                    var targetEnd = theIndices[indicesCount][1];
                }
            }
            list2.putObject(charIDToTypeID("Txtt"), desc14);
        }

        var list3 = new ActionList();
        for (var n = 0; n < kernRange.count; n++) {
            var thisOne = kernRange.getObjectValue(n);
            var desc15 = new ActionDescriptor();
            desc15.putInteger(idFrom, thisOne.getInteger(stringIDToTypeID('From')));
            desc15.putInteger(idT, thisOne.getInteger(stringIDToTypeID('T')));
            desc15.putInteger(charIDToTypeID("Krng"), thisOne.getInteger(stringIDToTypeID("kerning")));
            list3.putObject(stringIDToTypeID("kerningRange"), desc15);
        }
        desc7.putList(idTxtt, list2);
        desc7.putList(stringIDToTypeID("kerningRange"), list3);
        if (originalAntiAlias !== null) {
            desc7.putEnumerated(antiAliasTypeID, antiAliasTypeID, originalAntiAlias);
        }
        desc6.putObject(idT, idTxLr, desc7);
        executeAction(idsetd, desc6, DialogModes.NO);
    } catch (e) {}
    app.preferences.rulerUnits = originalRulerUnits;
}

function selectLayerFromGroup(groupName, layerName) {
    try {
        var group = app.activeDocument.layerSets.getByName(groupName);
        var layer = group.artLayers.getByName(layerName);
        app.activeDocument.activeLayer = layer;
    } catch (e) {
        alert("Layer not found: " + layerName);
    }
}

function resizeTextLayerToWidth(layer, fixedWidth) {
    var bounds = layer.bounds;
    var textWidth = bounds[2] - bounds[0];
    var scaleFactor = (fixedWidth / textWidth) * 100;
    layer.resize(scaleFactor, 100); // 只調整寬度
}

function moveLayerToXPosition(layer, xPosition) {
    var bounds = layer.bounds;
    var currentX = bounds[0].value;
    var deltaX = xPosition - currentX;
    layer.translate(deltaX, 0);
}

function saveLayerAsPNG(doc, filePath) {
    var pngOptions = new PNGSaveOptions();
    var file = new File(filePath);
    doc.saveAs(file, pngOptions, true, Extension.LOWERCASE);
}

function saveAsTGAWithAlpha(filePath) {
    cTID = function(s) { return app.charIDToTypeID(s); };
    sTID = function(s) { return app.stringIDToTypeID(s); };

    var doc = app.activeDocument;
    var duppedDocument = doc.duplicate();
    app.activeDocument = duppedDocument;

    if (duppedDocument.layers.length > 1) {
        for (var j = 0; j < duppedDocument.layers.length; j++) {
            if (duppedDocument.layers[j].visible) {
                duppedDocument.activeLayer = duppedDocument.layers[j];
                break;
            }
        }
        duppedDocument.mergeVisibleLayers();
    }

    function makeAlpha_from_Transparency() {
        var idSetd = charIDToTypeID("setd");
        var descSetd = new ActionDescriptor();
        var idNull = charIDToTypeID("null");
        var refFsel = new ActionReference();
        var idChnl = charIDToTypeID("Chnl");
        var idFsel = charIDToTypeID("fsel");
        refFsel.putProperty(idChnl, idFsel);
        descSetd.putReference(idNull, refFsel);
        var idTo = charIDToTypeID("T   ");
        var refChnl = new ActionReference();
        var idChnlEnum = charIDToTypeID("Chnl");
        var idTrsp = charIDToTypeID("Trsp");
        refChnl.putEnumerated(idChnlEnum, idChnlEnum, idTrsp);
        descSetd.putReference(idTo, refChnl);
        executeAction(idSetd, descSetd, DialogModes.NO);

        var idMk = charIDToTypeID("Mk  ");
        var descMk = new ActionDescriptor();
        var idNw = charIDToTypeID("Nw  ");
        var idChnlClass = charIDToTypeID("Chnl");
        descMk.putClass(idNw, idChnlClass);
        var idAt = charIDToTypeID("At  ");
        var refNewChnl = new ActionReference();
        var idChnlRef = charIDToTypeID("Chnl");
        var idNew = charIDToTypeID("New ");
        refNewChnl.putEnumerated(idChnlRef, idChnlRef, idNew);
        descMk.putReference(idAt, refNewChnl);
        var idUsng = charIDToTypeID("Usng");
        var idUsrM = charIDToTypeID("UsrM");
        var idRvlS = charIDToTypeID("RvlS");
        descMk.putEnumerated(idUsng, idUsrM, idRvlS);
        executeAction(idMk, descMk, DialogModes.NO);

        var alphaChannel = duppedDocument.channels[3];
        duppedDocument.selection.store(alphaChannel, SelectionType.REPLACE);
    }

    makeAlpha_from_Transparency();

    function Save_as_TGA() {
        function step1(enabled, withDialog) {
            if (enabled != undefined && !enabled) return;
            var dialogMode = (withDialog ? DialogModes.ALL : DialogModes.NO);
            var desc1 = new ActionDescriptor();
            desc1.putInteger(cTID('Dpth'), 8);
            var desc2 = new ActionDescriptor();
            desc2.putInteger(cTID('Vrsn'), 6);
            desc2.putEnumerated(cTID('Mthd'), sTID("hdrToningMethodType"), sTID("hdrtype2"));
            desc2.putDouble(cTID('Exps'), 0);
            desc2.putDouble(cTID('Gmm '), 1);
            desc2.putBoolean(sTID("deghosting"), false);
            desc1.putObject(cTID('With'), sTID("hdrOptions"), desc2);
            executeAction(sTID('convertMode'), desc1, dialogMode);
        }

        function step4(enabled, withDialog) {
            if (enabled != undefined && !enabled) return;
            var dialogMode = (withDialog ? DialogModes.ALL : DialogModes.NO);
            var desc1 = new ActionDescriptor();
            var desc2 = new ActionDescriptor();
            desc2.putInteger(cTID('BtDp'), 32);
            desc2.putInteger(cTID('Cmpr'), 1); // RLE Compression
            desc1.putObject(cTID('As  '), cTID('TrgF'), desc2);
            desc1.putPath(cTID('In  '), new File(filePath));
            desc1.putInteger(cTID('DocI'), 223);
            executeAction(sTID('save'), desc1, dialogMode);
        }

        step1(true, 0);
        step4();
    }

    Save_as_TGA();
    duppedDocument.close(SaveOptions.DONOTSAVECHANGES);
    app.activeDocument = doc;
}

function hideAllLayersExceptGroup(group) {
    var doc = app.activeDocument;
    for (var i = 0; i < doc.layerSets.length; i++) {
        var layerSet = doc.layerSets[i];
        if (layerSet !== group) {
            layerSet.visible = false;
        } else {
            layerSet.visible = true;
        }
    }
}

function replaceTextInLayer(layer, text) {
    if (layer.kind == LayerKind.TEXT) {
        layer.textItem.contents = text;
    }
}

function cleanCopySuffix(layer) {
    // 處理中文版的 "拷貝" 後綴
    layer.name = layer.name.replace(/ 拷貝(?: \d+)?$/, "");
    // 處理英文版的 "copy" 後綴
    layer.name = layer.name.replace(/ copy(?: \d+)?$/i, "");
    // 可以根據需要添加更多語言版本的後綴處理
}

function renameLayersRecursively(group) {
    for (var i = 0; i < group.artLayers.length; i++) {
        cleanCopySuffix(group.artLayers[i]);
    }
    for (var j = 0; j < group.layerSets.length; j++) {
        cleanCopySuffix(group.layerSets[j]);
        renameLayersRecursively(group.layerSets[j]);
    }
}

function duplicateAndRenameGroup(originalGroupName, newGroupName) {
    var originalGroup = app.activeDocument.layerSets.getByName(originalGroupName);
    var newGroup = originalGroup.duplicate();
    var uniqueNewGroupName = newGroupName;
    var counter = 1;
    while (layerExists(uniqueNewGroupName)) {
        uniqueNewGroupName = newGroupName + "_" + counter;
        counter++;
    }
    newGroup.name = uniqueNewGroupName;
    renameLayersRecursively(newGroup);
    return newGroup;
}

function layerExists(layerName) {
    try {
        app.activeDocument.layers.getByName(layerName);
        return true;
    } catch (e) {
        return false;
    }
}

function processSUP(groupName, layersInfo, newGroupName) {
    var newGroup = duplicateAndRenameGroup(groupName, newGroupName);
    for (var i = 0; i < layersInfo.length; i++) {
        var layerInfo = layersInfo[i];
        var layer = newGroup.artLayers.getByName(layerInfo.layerName);
        replaceTextInLayer(layer, layerInfo.text);
    }
    newGroup.visible = true;
    collapseGroup(newGroupName);
    moveGroupToTop(newGroupName); // 確保排序
}

function processSUPVS(groupName, vsInfo, newGroupName) {
    var newGroup = duplicateAndRenameGroup(groupName, newGroupName);
    var groupL = newGroup.layerSets.getByName("SUP L");
    var groupR = newGroup.layerSets.getByName("SUP R");

    var leftInfo = vsInfo.left;
    var rightInfo = vsInfo.right;

    for (var i = 0; i < leftInfo.length; i++) {
        var layerInfo = leftInfo[i];
        var layer = groupL.artLayers.getByName(layerInfo.layerName);
        replaceTextInLayer(layer, layerInfo.text);
    }

    for (var j = 0; j < rightInfo.length; j++) {
        var layerInfo = rightInfo[j];
        var layer = groupR.artLayers.getByName(layerInfo.layerName);
        replaceTextInLayer(layer, layerInfo.text);
    }

    newGroup.visible = true;
    collapseGroup(newGroupName);
    moveGroupToTop(newGroupName); // 確保排序
}

function collapseGroup(groupName) {
    var group = app.activeDocument.layerSets.getByName(groupName);
    app.activeDocument.activeLayer = group;
    var idungroupLayersEvent = stringIDToTypeID("ungroupLayersEvent");
    var desc14 = new ActionDescriptor();
    var idnull = charIDToTypeID("null");
    var ref13 = new ActionReference();
    var idLyr = charIDToTypeID("Lyr ");
    var idOrdn = charIDToTypeID("Ordn");
    var idTrgt = charIDToTypeID("Trgt");
    ref13.putEnumerated(idLyr, idOrdn, idTrgt);
    desc14.putReference(idnull, ref13);
    executeAction(idungroupLayersEvent, desc14, DialogModes.NO);

    var idMk = charIDToTypeID("Mk  ");
    var desc15 = new ActionDescriptor();
    var idnull = charIDToTypeID("null");
    var ref14 = new ActionReference();
    var idlayerSection = stringIDToTypeID("layerSection");
    ref14.putClass(idlayerSection);
    desc15.putReference(idnull, ref14);
    var idFrom = charIDToTypeID("From");
    var ref15 = new ActionReference();
    var idLyr = charIDToTypeID("Lyr ");
    var idOrdn = charIDToTypeID("Ordn");
    var idTrgt = charIDToTypeID("Trgt");
    ref15.putEnumerated(idLyr, idOrdn, idTrgt);
    desc15.putReference(idFrom, ref15);
    executeAction(idMk, desc15, DialogModes.NO);
    app.activeDocument.activeLayer.name = groupName;
}

function moveGroupToTop(groupName) {
    var group = app.activeDocument.layerSets.getByName(groupName);
    group.move(app.activeDocument, ElementPlacement.PLACEATBEGINNING);
}

function deleteOriginalGroups() {
    var groupsToDelete = ["SUP 一行", "SUP 二行", "SUP VS"];
    for (var i = 0; i < groupsToDelete.length; i++) {
        try {
            var group = app.activeDocument.layerSets.getByName(groupsToDelete[i]);
            group.remove();
        } catch (e) {
            // 找不到群組，繼續執行
        }
    }
}

function parseTextFile(filePath) {
    var file = new File(filePath);
    if (file.open("r")) {
        var contents = file.read();
        file.close();
        return contents;
    } else {
        $.writeln("Error: Unable to open file.");
        return null;
    }
}

function processTextContents(contents) {
    var lines = contents.split(/\r?\n/);
    var supData = [];
    var processingSup = false;
    var skipNextLine = false;

    for (var i = 0; i < lines.length; i++) {
        var line = trim(lines[i]);

        if (skipNextLine) {
            skipNextLine = false;
            continue;
        }

        if (line.toLowerCase() === "sup" || line.toLowerCase() === "大bar") {
            processingSup = line.toLowerCase() === "sup";
            if (i + 1 < lines.length && trim(lines[i + 1]) === "") {
                skipNextLine = true;
            }
            continue;
        }

        if (processingSup && line) {
            if (line.indexOf("vs.") !== -1) {
                var parts = line.split("vs.");
                var left = trim(parts[0]).split(" ");
                var right = trim(parts[1]).split(" ");
                
                // 修改這裡來處理只有頭銜沒有名字的情況
                supData.push({
                    type: "SUP VS",
                    left: [
                        { layerName: "頭銜", text: left.length > 1 ? left.slice(0, -1).join(" ") : "" },
                        { layerName: "名字", text: left.length > 1 ? left[left.length - 1] : left[0] }
                    ],
                    right: [
                        { layerName: "頭銜", text: right.length > 1 ? right.slice(0, -1).join(" ") : "" },
                        { layerName: "名字", text: right.length > 1 ? right[right.length - 1] : right[0] }
                    ]
                });
            } else if (line.split(" ").length > 1) {
                var parts = line.split(" ");
                supData.push({
                    type: "SUP 二行",
                    head: "頭銜",
                    name: "名字",
                    text: [parts.slice(0, -1).join(" "), parts[parts.length - 1]]
                });
            } else {
                supData.push({
                    type: "SUP 一行",
                    name: "名字",
                    text: [line]
                });
            }
        } else if (!processingSup && line) {
            // 處理大BAR內容
            // 這裡可以添加處理大BAR的邏輯
        }

        if (trim(line) === "" && processingSup) {
            processingSup = false;
        }
    }
    return supData;
}

function trim(str) {
    return str.replace(/^\s+|\s+$/g, '');
}

function isArray(value) {
    return Object.prototype.toString.call(value) === '[object Array]';
}

function objectToString(obj) {
    if (isArray(obj)) {
        var arrStr = "";
        for (var i = 0; i < obj.length; i++) {
            arrStr += objectToString(obj[i]) + ", ";
        }
        return arrStr.slice(0, -2); // 去掉最後的逗號和空格
    }
    var str = "";
    for (var key in obj) {
        if (obj.hasOwnProperty(key)) {
            str += key + ": " + obj[key] + ", ";
        }
    }
    return str.slice(0, -2); // 去掉最後的逗號和空格
}

function showAllLayersInGroup(group) {
    for (var i = 0; i < group.artLayers.length; i++) {
        group.artLayers[i].visible = true;
    }
    for (var j = 0; j < group.layerSets.length; j++) {
        showAllLayersInGroup(group.layerSets[j]);
        group.layerSets[j].visible = true;
    }
}

function duplicateAndCloseOriginal() {
    if (app.documents.length > 0) {
        var originalDoc = app.activeDocument;
        var docName = originalDoc.name;
        app.activeDocument.duplicate(docName + " copy");
        originalDoc.close(SaveOptions.DONOTSAVECHANGES);
    } else {
        alert("沒有打開的文檔！");
    }
}

function main() {
    // 在腳本開始時複製當前文檔並關閉原文檔
    duplicateAndCloseOriginal();

    alert("請先選擇txt檔，將執行自動化工作");

    var currentDate = new Date();
    var month = ("0" + (currentDate.getMonth() + 1)).slice(-2);
    var day = ("0" + currentDate.getDate()).slice(-2);
    var defaultPath = "\\\\10.227.58.117\\新聞txt\\" + month + day + "\\民間特偵組";


    var defaultFolder = new Folder(defaultPath);
    var txtFile;

    if (defaultFolder.exists) {
        txtFile = defaultFolder.openDlg("Select the TXT file", "*.txt");
    } else {
        txtFile = File.openDialog("Select the TXT file", "*.txt");
    }

    if (txtFile === null) return;

    var content = readTxtFile(txtFile);
    var extractedData = extractBarText(content);
    var bars = extractedData.bars;
    var highlights = extractedData.highlights;
    var unclosedQuotesWarnings = extractedData.warnings;
    var saveFormat = extractedData.format;
    var firstLine = extractedData.firstLine;

    if (bars.length == 0 && saveFormat === "") {
        alert("No valid 'Bar' content or save format found in the TXT file.");
        return;
    }

    var desktopPath = getDesktopPath();
    var folderName = month + day + "_" + firstLine;
    var saveFolder = new Folder(desktopPath + "/" + folderName);

    if (!saveFolder.exists) {
        saveFolder.create();
    }

    var doc = app.activeDocument;
    var baseLayer = null;

    if (bars.length > 0) {
        baseLayer = doc.layerSets.getByName("大標").artLayers.getByName("大標_01");

        // 處理大標部分
        for (var i = 0; i < bars.length; i++) {
            var currentLayerName = "大標_" + ("0" + (i + 1)).slice(-2);

            // 選擇當前圖層
            var currentLayer;
            if (i == 0) {
                currentLayer = baseLayer;
            } else {
                currentLayer = doc.layerSets.getByName("大標").artLayers.getByName(currentLayerName);
            }

            // 如果不是最後一個大標，則創建新圖層
            if (i < bars.length - 1) {
                var newLayerName = "大標_" + ("0" + (i + 2)).slice(-2);
                var newLayer = currentLayer.duplicate();
                newLayer.name = newLayerName;
                newLayer.visible = false;  // Hide the new layer
            }

            // 替換和高亮文本
            selectLayerFromGroup("大標", currentLayerName);
            replaceTextLayerContent(app.activeDocument.activeLayer, bars[i]);

            if (i < highlights.length && highlights[i] !== "") {
                var highlightText = highlights[i];
                var theRegExp = new RegExp(highlightText, "gi");
                changeWordProperties(theRegExp);
            }

            // 調整文本圖層大小和位置
            resizeTextLayerToWidth(app.activeDocument.activeLayer, 1300);
            moveLayerToXPosition(app.activeDocument.activeLayer, 471);

            // 隱藏當前圖層
            app.activeDocument.activeLayer.visible = false;
        }

        // Show warnings for unclosed quotes
        if (unclosedQuotesWarnings.length > 0) {
            alert(unclosedQuotesWarnings.join("\n"));
        }
    }

    // 處理 SUP 部分
    var supContents = content;  // Use the content we already read
    var supData = processTextContents(supContents);

    for (var i = 0; i < supData.length; i++) {
        var data = supData[i];
        var newGroupName = "super_" + ("0" + (i + 1)).slice(-2);

        if (data.type === "SUP 二行") {
            processSUP(data.type, [
                { layerName: data.head, text: data.text[0] },
                { layerName: data.name, text: data.text[1] }
            ], newGroupName);
        } else if (data.type === "SUP 一行") {
            processSUP(data.type, [
                { layerName: data.name, text: data.text[0] }
            ], newGroupName);
        } else if (data.type === "SUP VS") {
            processSUPVS(data.type, {
                left: data.left,
                right: data.right
            }, newGroupName);
        }
    }

    // 刪除原始模板群組
    deleteOriginalGroups();

    // 確保所有大標圖層都被關閉
    if (bars.length > 0) {
        var bigTitleGroup = doc.layerSets.getByName("大標");
        for (var j = 0; j < bigTitleGroup.artLayers.length; j++) {
            bigTitleGroup.artLayers[j].visible = false;
        }
    }

    // 存檔大標部分
    if (bars.length > 0) {
        for (var i = 0; i < bars.length; i++) {
            var currentLayerName = "大標_" + ("0" + (i + 1)).slice(-2);
            selectLayerFromGroup("大標", currentLayerName);
            hideAllLayersExceptGroup(doc.layerSets.getByName("大標"));
            app.activeDocument.activeLayer.visible = true;  // 打開當前要存檔的圖層
            var fileName = saveFolder.fsName + "/" + currentLayerName + "." + saveFormat;
            if (saveFormat === "png") {
                saveLayerAsPNG(doc, fileName);
            } else if (saveFormat === "tga") {
                saveAsTGAWithAlpha(fileName);
            }
            app.activeDocument.activeLayer.visible = false;  // 關閉當前圖層
        }
    }

    // 存檔 SUP 部分
    for (var i = 0; i < supData.length; i++) {
        var newGroupName = "super_" + ("0" + (i + 1)).slice(-2);
        hideAllLayersExceptGroup(doc.layerSets.getByName(newGroupName));
        showAllLayersInGroup(doc.layerSets.getByName(newGroupName));
        var fileName = saveFolder.fsName + "/" + newGroupName + "." + saveFormat;
        if (saveFormat === "png") {
            saveLayerAsPNG(doc, fileName);
        } else if (saveFormat === "tga") {
            saveAsTGAWithAlpha(fileName);
        }
        doc.layerSets.getByName(newGroupName).visible = false;  // 關閉當前 SUP 群組
    }

    alert(folderName + "已自動完成並儲存於桌面，請檢查後再丟出去");
}

main();
