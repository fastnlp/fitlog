var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : new P(function (resolve) { resolve(result.value); }).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
class SuperParamVisual {
    constructor(container, config) {
        this.dataInfo = {
            columns: null,
            datas: null,
            posArrCache: null,
            sliders: [],
            selectedLines: null,
            redraws: []
        };
        this.ui = {
            columns: null,
            lines: null,
            sliders: null
        };
        this.mouseStatus = {
            isLeftDown: false,
            pos: [0, 0],
            selectedSlider: null
        };
        this.config = {
            containerHeight: 640,
            containerPadding: [64, 0, 64, 0],
            columnWidth: 180,
            columnNameFont: "18px Microsoft JhengHei",
            columnNameColor: "#353535",
            columnAxisLineWidth: 1,
            columnAxisLineColor: "#cccccc",
            columnAxisFont: "12px Microsoft JhengHei",
            columnAxisColor: "#353535",
            linesPerCanvas: 8,
            lineWidth: 1,
            lineColor: "rgba(180, 180, 180, 0.2)",
            lineHighlightColor: "rgba(255, 70, 0, 0.9)",
            lineSmooth: 0.2,
            sliderWidth: 16,
            sliderColor: "rgba(200, 200, 200, 0.3)",
            sliderHoverColor: "rgba(200, 200, 200, 0.7)"
        };
        if (config) {
            Object.assign(this.config, config);
        }
        this.container = typeof container == "string" ? document.querySelector(container) : container;
        if (this.container == null) {
            throw new Error("a container is needed");
        }
    }
    update(datasOrUrl) {
        return __awaiter(this, void 0, void 0, function* () {
            if (datasOrUrl == null) {
                return;
            }
            if (typeof datasOrUrl == "string") {
                const res = yield fetch(new Request(datasOrUrl, {
                    method: 'GET', cache: 'reload'
                }));
                this.datas = yield res.json();
            }
            else {
                this.datas = datasOrUrl;
            }
            this.refresh();
        });
    }
    getInfo() {
        let info = {
            range: [],
            datasInRange: [],
            rawDatas: this.datas
        };
        this.dataInfo.sliders.forEach((item, index) => {
            const slider = this.dataInfo.sliders[index];
            const column = this.dataInfo.columns[index];
            if (column.liner) {
                if (slider.enable) {
                    info.range.push({ name: column.name, min: slider.min, max: slider.max });
                }
                else {
                    info.range.push({ name: column.name, enable: false, min: column.liner.min, max: column.liner.max });
                }
            }
            else {
                const values = [];
                column.classified.forEach((value, key) => {
                    if (!slider.enable || (value >= slider.min && value <= slider.max)) {
                        values.push(key);
                    }
                });
                info.range.push({ name: column.name, enable: slider.enable, values: values });
            }
        });
        for (let dataI of Object.keys(this.dataInfo.selectedLines)) {
            info.datasInRange.push(this.datas.data[+dataI]);
        }
        return info;
    }
    setOnSliderChangeListener(listener) {
        this.onSliderChangeListener = listener;
    }
    static digitFix(num) {
        num = Math.abs(num);
        if (num == 0) {
            num = 1;
        }
        const log10 = Math.log10(num);
        if (log10 >= 2) {
            return 0;
        }
        else
            return Math.floor(-log10 + 2);
    }
    findSelectLines() {
        const newSelected = {};
        this.dataInfo.datas.forEach((value, index) => {
            let inRange = true;
            for (let i = 0; i < value.length; i++) {
                const slider = this.dataInfo.sliders[i];
                if (slider.enable && (value[i] < slider.min || value[i] > slider.max)) {
                    inRange = false;
                    break;
                }
            }
            if (inRange) {
                newSelected[index] = true;
            }
        });
        return newSelected;
    }
    prepareData() {
        this.dataInfo.columns = [];
        this.dataInfo.datas = [];
        this.dataInfo.posArrCache = [];
        this.dataInfo.sliders = [];
        this.dataInfo.selectedLines = {};
        this.dataInfo.redraws = [];
        this.datas.columns.forEach(column => this.dataInfo.columns.push({
            name: column
        }));
        this.datas.data.forEach(item => {
            item.forEach((value, index) => {
                const column = this.dataInfo.columns[index];
                if (typeof value == "number") {
                    if (column.liner == null) {
                        column.liner = {
                            min: value,
                            max: value
                        };
                    }
                    else {
                        column.liner.min = Math.min(column.liner.min, value);
                        column.liner.max = Math.max(column.liner.max, value);
                    }
                }
                else {
                    value = "" + value;
                    if (column.classified == null) {
                        column.classified = new Map();
                    }
                    column.classified.set(value, 0);
                }
            });
        });
        this.dataInfo.columns.forEach(column => {
            if (column.classified) {
                const classified = [];
                column.classified.forEach((value, key) => {
                    classified.push(key);
                });
                classified.sort((o1, o2) => o1.localeCompare(o2));
                column.classified = new Map();
                classified.forEach((value, index) => {
                    column.classified.set(value, index);
                });
            }
            else {
                let dur = column.liner.max - column.liner.min;
                if (dur == 0) {
                    dur = 2;
                }
                column.liner.min = column.liner.min - dur * 0.1;
                column.liner.max = column.liner.max + dur * 0.1;
                let fix = SuperParamVisual.digitFix(dur / 100);
                column.liner.min = +column.liner.min.toFixed(fix);
                column.liner.max = +column.liner.max.toFixed(fix);
                column.liner.fix = fix;
            }
        });
        const columnW = this.config.columnWidth;
        const paddingTop = this.config.containerPadding[0];
        const columnAxisHeight = this.config.containerHeight - this.config.containerPadding[0] - this.config.containerPadding[2];
        this.datas.data.forEach((data, index) => {
            const posArr = [];
            const transData = [];
            data.forEach((item, itemI) => {
                const midX = this.config.containerPadding[3] + columnW * (itemI + 0.5);
                const column = this.dataInfo.columns[itemI];
                if (column.liner) {
                    const y = paddingTop + columnAxisHeight * (column.liner.max - item) / (column.liner.max - column.liner.min);
                    posArr.push([midX, y]);
                    transData.push(item);
                }
                else {
                    const cIndex = column.classified.get("" + item);
                    const y = paddingTop + columnAxisHeight / (column.classified.size + 1) * (column.classified.size - cIndex);
                    posArr.push([midX, y]);
                    transData.push(cIndex);
                }
            });
            this.dataInfo.datas.push(transData);
            if (posArr.length == 2) {
                this.dataInfo.posArrCache[index] = {
                    type: "twoPoints",
                    points: posArr
                };
            }
            else if (posArr.length > 2) {
                const smoothPosArr = {
                    type: "smooth",
                    start: null,
                    ctlTos: []
                };
                let prePreviousPointX = NaN;
                let prePreviousPointY = NaN;
                let previousPointX = NaN;
                let previousPointY = NaN;
                let currentPointX = NaN;
                let currentPointY = NaN;
                let nextPointX;
                let nextPointY;
                const lineSize = posArr.length;
                for (let valueIndex = 0; valueIndex < lineSize; ++valueIndex) {
                    if (isNaN(currentPointX)) {
                        currentPointX = posArr[valueIndex][0];
                        currentPointY = posArr[valueIndex][1];
                    }
                    if (isNaN(previousPointX)) {
                        if (valueIndex > 0) {
                            previousPointX = posArr[valueIndex - 1][0];
                            previousPointY = posArr[valueIndex - 1][1];
                        }
                        else {
                            previousPointX = currentPointX;
                            previousPointY = currentPointY;
                        }
                    }
                    if (isNaN(prePreviousPointX)) {
                        if (valueIndex > 1) {
                            previousPointX = posArr[valueIndex - 2][0];
                            previousPointY = posArr[valueIndex - 2][1];
                        }
                        else {
                            prePreviousPointX = previousPointX;
                            prePreviousPointY = previousPointY;
                        }
                    }
                    if (valueIndex < lineSize - 1) {
                        nextPointX = posArr[valueIndex + 1][0];
                        nextPointY = posArr[valueIndex + 1][1];
                    }
                    else {
                        nextPointX = currentPointX;
                        nextPointY = currentPointY;
                    }
                    if (valueIndex == 0) {
                        smoothPosArr.start = [currentPointX, currentPointY];
                    }
                    else {
                        const firstDiffX = (currentPointX - prePreviousPointX);
                        const firstDiffY = (currentPointY - prePreviousPointY);
                        const secondDiffX = (nextPointX - previousPointX);
                        const secondDiffY = (nextPointY - previousPointY);
                        const firstControlPointX = previousPointX + (this.config.lineSmooth * firstDiffX);
                        const firstControlPointY = previousPointY + (this.config.lineSmooth * firstDiffY);
                        const secondControlPointX = currentPointX - (this.config.lineSmooth * secondDiffX);
                        const secondControlPointY = currentPointY - (this.config.lineSmooth * secondDiffY);
                        smoothPosArr.ctlTos.push({
                            ctl0X: firstControlPointX,
                            ctl0Y: firstControlPointY,
                            ctl1X: secondControlPointX,
                            ctl1Y: secondControlPointY,
                            toX: currentPointX,
                            toY: currentPointY,
                        });
                    }
                    prePreviousPointX = previousPointX;
                    prePreviousPointY = previousPointY;
                    previousPointX = currentPointX;
                    previousPointY = currentPointY;
                    currentPointX = nextPointX;
                    currentPointY = nextPointY;
                }
                this.dataInfo.posArrCache[index] = smoothPosArr;
            }
        });
        let firstColumnMaxV = null;
        this.dataInfo.datas.forEach((value, index) => {
            if (firstColumnMaxV == null || value[0] > firstColumnMaxV) {
                firstColumnMaxV = value[0];
            }
        });
        const firstColumn = this.dataInfo.columns[0];
        if (firstColumn.liner) {
            const dur = firstColumn.liner.max - firstColumn.liner.min;
            this.dataInfo.sliders.push({ enable: true, min: firstColumnMaxV - dur * 0.05, max: Math.min(firstColumnMaxV + dur * 0.05, firstColumn.liner.max), isHover: false });
        }
        else {
            this.dataInfo.sliders.push({ enable: true, min: -0.5, max: 0.5, isHover: false });
        }
        for (let i = 1; i < this.dataInfo.columns.length; i++) {
            const column = this.dataInfo.columns[i];
            if (column.liner) {
                this.dataInfo.sliders.push({ enable: false, min: column.liner.min, max: column.liner.max, isHover: false });
            }
            else {
                this.dataInfo.sliders.push({ enable: false, min: -0.5, max: 0.5, isHover: false });
            }
        }
        this.dataInfo.selectedLines = this.findSelectLines();
    }
    clearUi() {
        if (this.ui.lines) {
            while (this.ui.lines.length > 0) {
                this.ui.lines.pop().remove();
            }
        }
        this.ui.columns && this.ui.columns.remove() && (this.ui.columns = null);
        this.ui.sliders && this.ui.sliders.remove() && (this.ui.sliders = null);
    }
    static createCanvas(width, height, classStr) {
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        canvas.setAttribute("class", classStr);
        canvas.style.position = "absolute";
        canvas.style.left = "0";
        canvas.style.top = "0";
        return canvas;
    }
    static cutText(context, text, maxWdith) {
        const width = context.measureText(text).width;
        if (width <= maxWdith) {
            return [text, width];
        }
        else {
            return [text.substring(0, Math.floor(maxWdith / width * 0.9 * text.length)) + "...", maxWdith];
        }
    }
    drawColumns() {
        const context = this.ui.columns.getContext("2d");
        const columnW = this.config.columnWidth;
        const columnAxisLabelW = columnW * 0.6;
        const columnAxisHeight = this.config.containerHeight - this.config.containerPadding[0] - this.config.containerPadding[2];
        const columnNameLabelW = columnW * 0.8;
        const paddingTop = this.config.containerPadding[0];
        context.save();
        this.dataInfo.columns.forEach((column, index) => {
            const midX = this.config.containerPadding[3] + columnW * (index + 0.5);
            context.textBaseline = "bottom";
            context.font = this.config.columnNameFont;
            context.fillStyle = this.config.columnNameColor;
            const [columnName, nameWidth] = SuperParamVisual.cutText(context, column.name, columnNameLabelW);
            context.fillText(columnName, midX - nameWidth / 2, this.config.containerPadding[0] - 24);
            context.textBaseline = "middle";
            context.font = this.config.columnAxisFont;
            context.fillStyle = this.config.columnAxisColor;
            context.lineWidth = this.config.columnAxisLineWidth;
            context.strokeStyle = this.config.columnAxisLineColor;
            if (column.liner) {
                const max = column.liner.max;
                const per = (column.liner.max - column.liner.min) / 10;
                for (let i = 0; i <= 10; i++) {
                    const y = paddingTop + columnAxisHeight / 10 * i;
                    context.moveTo(midX, y);
                    context.lineTo(midX - 4, y);
                    if (i % 2 == 0) {
                        let axisLabel = "" + (max - per * i).toFixed(column.liner.fix);
                        const [text, width] = SuperParamVisual.cutText(context, axisLabel, columnAxisLabelW);
                        context.fillText(text, midX - 8 - width, y);
                    }
                }
            }
            else {
                const size = column.classified.size;
                const keys = Array.from(column.classified.keys());
                for (let i = -1; i <= size; i++) {
                    const y = paddingTop + columnAxisHeight / (size + 1) * (size - i);
                    context.moveTo(midX, y);
                    context.lineTo(midX - 4, y);
                    if (i > -1 && i < size) {
                        const [text, width] = SuperParamVisual.cutText(context, keys[i], columnAxisLabelW);
                        context.fillText(text, midX - 8 - width, y);
                    }
                }
            }
            context.moveTo(midX, paddingTop);
            context.lineTo(midX, paddingTop + columnAxisHeight);
            context.stroke();
        });
        context.restore();
    }
    drawLines(redrawLineIndexes = null) {
        let canvasRedrawIndexes = null;
        if (redrawLineIndexes != null) {
            canvasRedrawIndexes = {};
            for (let key of Object.keys(redrawLineIndexes)) {
                canvasRedrawIndexes[Math.floor(+key / this.config.linesPerCanvas)] = true;
            }
        }
        for (let i = 0; i < this.ui.lines.length; i++) {
            if (!canvasRedrawIndexes || canvasRedrawIndexes[i]) {
                const canvas = this.ui.lines[i];
                const context = canvas.getContext("2d");
                context.clearRect(0, 0, canvas.width, canvas.height);
                const startI = this.config.linesPerCanvas * i;
                const endI = Math.min(startI + this.config.linesPerCanvas, this.dataInfo.datas.length);
                for (let j = startI; j < endI; j++) {
                    this.drawLine(j);
                }
            }
        }
    }
    drawLine(index) {
        const posArr = this.dataInfo.posArrCache[index];
        const context = this.ui.lines[Math.floor(index / this.config.linesPerCanvas)].getContext("2d");
        context.save();
        context.lineWidth = this.config.lineWidth;
        context.strokeStyle = !this.dataInfo.selectedLines || !this.dataInfo.selectedLines[index] ? this.config.lineColor : this.config.lineHighlightColor;
        context.beginPath();
        if (posArr.type == "twoPoints") {
            context.moveTo(posArr.points[0][0], posArr.points[0][1]);
            context.lineTo(posArr.points[1][0], posArr.points[1][1]);
        }
        else {
            context.moveTo(posArr.start[0], posArr.start[1]);
            for (let i = 0, len = posArr.ctlTos.length; i < len; i++) {
                const item = posArr.ctlTos[i];
                context.bezierCurveTo(item.ctl0X, item.ctl0Y, item.ctl1X, item.ctl1Y, item.toX, item.toY);
            }
        }
        context.stroke();
        context.restore();
    }
    drawSlider(redrawIndexes = null) {
        const context = this.ui.sliders.getContext("2d");
        const columnW = this.config.columnWidth;
        const columnAxisHeight = this.config.containerHeight - this.config.containerPadding[0] - this.config.containerPadding[2];
        const paddingTop = this.config.containerPadding[0];
        const sliderWidth = this.config.sliderWidth;
        const sliderInfos = this.dataInfo.sliders;
        context.save();
        sliderInfos.forEach((value, index) => {
            if (redrawIndexes == null || redrawIndexes[index]) {
                const midX = this.config.containerPadding[3] + columnW * (index + 0.5);
                const sliderInfo = sliderInfos[index];
                const column = this.dataInfo.columns[index];
                context.clearRect(midX - sliderWidth / 2, 0, sliderWidth, this.config.containerHeight);
                if (sliderInfo.enable) {
                    context.fillStyle = sliderInfo.isHover ? this.config.sliderHoverColor : this.config.sliderColor;
                    let top;
                    let bottom;
                    if (column.liner) {
                        top = paddingTop + columnAxisHeight * (column.liner.max - sliderInfo.max) / (column.liner.max - column.liner.min);
                        bottom = paddingTop + columnAxisHeight * (column.liner.max - sliderInfo.min) / (column.liner.max - column.liner.min);
                        context.fillRect(midX - sliderWidth / 2, top, sliderWidth, bottom - top);
                    }
                    else {
                        top = paddingTop + columnAxisHeight * (column.classified.size - sliderInfo.max) / (column.classified.size + 1);
                        bottom = paddingTop + columnAxisHeight * (column.classified.size - sliderInfo.min) / (column.classified.size + 1);
                        context.fillRect(midX - sliderWidth / 2, top, sliderWidth, bottom - top);
                    }
                    const edgeH = 4;
                    sliderInfo.topDragRect = [midX - sliderWidth / 2, top - edgeH, sliderWidth, edgeH * 2 + 1];
                    sliderInfo.bottomDragRect = [midX - sliderWidth / 2, bottom - edgeH, sliderWidth, edgeH * 2 + 1];
                    sliderInfo.middleDragRect = [midX - sliderWidth / 2, top + edgeH, sliderWidth, bottom - top - edgeH * 2];
                }
                sliderInfo.enableBtnCircle = [midX, paddingTop + columnAxisHeight + 32, 5];
                context.beginPath();
                context.lineWidth = 2;
                context.strokeStyle = sliderInfo.enable ? this.config.lineHighlightColor : this.config.lineColor;
                context.arc(sliderInfo.enableBtnCircle[0], sliderInfo.enableBtnCircle[1], sliderInfo.enableBtnCircle[2], 0, 360);
                context.stroke();
            }
        });
        context.restore();
    }
    findMouseOverSlider(mousePos) {
        if (this.dataInfo.sliders) {
            for (let i = 0, len = this.dataInfo.sliders.length; i < len; i++) {
                const slider = this.dataInfo.sliders[i];
                if (slider.enable) {
                    if (SuperParamVisual.isPointInRect(slider.topDragRect, mousePos)) {
                        return {
                            index: i,
                            slider: slider,
                            pos: "top"
                        };
                    }
                    else if (SuperParamVisual.isPointInRect(slider.bottomDragRect, mousePos)) {
                        return {
                            index: i,
                            slider: slider,
                            pos: "bottom"
                        };
                    }
                    else if (SuperParamVisual.isPointInRect(slider.middleDragRect, mousePos)) {
                        return {
                            index: i,
                            slider: slider,
                            pos: "middle"
                        };
                    }
                }
                if (slider.enableBtnCircle) {
                    const dis = Math.sqrt(Math.pow(slider.enableBtnCircle[0] - mousePos[0], 2) + Math.pow(slider.enableBtnCircle[1] - mousePos[1], 2));
                    if (dis <= slider.enableBtnCircle[2] + 2) {
                        return {
                            index: i,
                            slider: slider,
                            pos: "enable"
                        };
                    }
                }
            }
        }
        return null;
    }
    refreshSelectedLine() {
        const newSelected = this.findSelectLines();
        for (let lineI of Object.keys(newSelected)) {
            if (this.dataInfo.selectedLines[lineI] != newSelected[lineI]) {
                this.dataInfo.redraws.push(["line", lineI]);
                delete this.dataInfo.selectedLines[lineI];
            }
        }
        for (let lineI of Object.keys(this.dataInfo.selectedLines)) {
            if (this.dataInfo.selectedLines[lineI] != newSelected[lineI]) {
                this.dataInfo.redraws.push(["line", lineI]);
            }
        }
        this.dataInfo.selectedLines = newSelected;
    }
    refresh() {
        this.prepareData();
        this.clearUi();
        let width = this.config.columnWidth * this.dataInfo.columns.length
            + this.config.containerPadding[1] + this.config.containerPadding[3];
        let height = this.config.containerHeight;
        this.container.style.width = width + "px";
        this.container.style.height = height + "px";
        this.ui.lines = [];
        for (let i = 0, max = Math.floor((this.dataInfo.datas.length - 1) / this.config.linesPerCanvas + 1); i < max; i++) {
            const lineCanvas = SuperParamVisual.createCanvas(width, height, "lines");
            this.container.appendChild(lineCanvas);
            this.ui.lines.push(lineCanvas);
        }
        this.ui.columns = SuperParamVisual.createCanvas(width, height, "columns");
        this.container.appendChild(this.ui.columns);
        this.ui.sliders = SuperParamVisual.createCanvas(width, height, "sliders");
        this.container.appendChild(this.ui.sliders);
        this.ui.sliders.onmousedown = ev => {
            if (ev.button == 0) {
                const curPos = [ev.offsetX, ev.offsetY];
                this.mouseStatus.isLeftDown = true;
                this.mouseStatus.pos = [ev.offsetX, ev.offsetY];
                const selectedSlider = this.findMouseOverSlider(curPos);
                if (selectedSlider) {
                    this.mouseStatus.selectedSlider = selectedSlider;
                    if (!selectedSlider.slider.isHover) {
                        selectedSlider.slider.isHover = true;
                        this.dataInfo.redraws.push(["slider", selectedSlider.index]);
                        this.redraw();
                    }
                }
            }
        };
        this.ui.sliders.onmouseup = ev => {
            if (ev.button == 0) {
                this.mouseStatus.isLeftDown = false;
                if (this.mouseStatus.selectedSlider) {
                    if (this.mouseStatus.selectedSlider.pos == "enable") {
                        this.mouseStatus.selectedSlider.slider.enable = !this.mouseStatus.selectedSlider.slider.enable;
                        this.dataInfo.redraws.push(["slider", this.mouseStatus.selectedSlider.index]);
                        this.refreshSelectedLine();
                        this.onSliderChangeListener && this.onSliderChangeListener(this.mouseStatus.selectedSlider.index, this.mouseStatus.selectedSlider.slider);
                        this.redraw();
                    }
                    this.mouseStatus.selectedSlider = null;
                }
            }
        };
        const columnAxisHeight = this.config.containerHeight - this.config.containerPadding[0] - this.config.containerPadding[2];
        this.ui.sliders.onmousemove = ev => {
            const curPos = [ev.offsetX, ev.offsetY];
            let selectedOrHoveredSliderInfo = this.mouseStatus.selectedSlider;
            if (!selectedOrHoveredSliderInfo) {
                selectedOrHoveredSliderInfo = this.findMouseOverSlider(curPos);
            }
            if (selectedOrHoveredSliderInfo) {
                if (selectedOrHoveredSliderInfo.pos == "middle") {
                    this.ui.sliders.style.cursor = this.mouseStatus.isLeftDown ? "grabbing" : "grab";
                }
                else if (selectedOrHoveredSliderInfo.pos == "top") {
                    this.ui.sliders.style.cursor = "n-resize";
                }
                else if (selectedOrHoveredSliderInfo.pos == "bottom") {
                    this.ui.sliders.style.cursor = "s-resize";
                }
                else if (selectedOrHoveredSliderInfo.pos == "enable") {
                    this.ui.sliders.style.cursor = "pointer";
                }
                if (!selectedOrHoveredSliderInfo.slider.isHover) {
                    selectedOrHoveredSliderInfo.slider.isHover = true;
                    this.dataInfo.redraws.push(["slider", selectedOrHoveredSliderInfo.index]);
                }
            }
            else {
                this.ui.sliders.style.cursor = "initial";
                for (let i = 0, len = this.dataInfo.sliders.length; i < len; i++) {
                    let item = this.dataInfo.sliders[i];
                    if (item.isHover) {
                        item.isHover = false;
                        this.dataInfo.redraws.push(["slider", i]);
                        break;
                    }
                }
            }
            if (this.mouseStatus.selectedSlider && this.mouseStatus.selectedSlider.pos.match("top|middle|bottom")) {
                let topDelta = 0;
                let bottomDelta = 0;
                if (this.mouseStatus.selectedSlider.pos == "top") {
                    topDelta = ev.offsetY - this.mouseStatus.pos[1];
                }
                else if (this.mouseStatus.selectedSlider.pos == "bottom") {
                    bottomDelta = ev.offsetY - this.mouseStatus.pos[1];
                }
                else {
                    bottomDelta = topDelta = ev.offsetY - this.mouseStatus.pos[1];
                }
                topDelta = -topDelta;
                bottomDelta = -bottomDelta;
                if (topDelta != 0 || bottomDelta != 0) {
                    const column = this.dataInfo.columns[this.mouseStatus.selectedSlider.index];
                    const sliderMax = column.liner ? column.liner.max : column.classified.size;
                    const sliderMin = column.liner ? column.liner.min : -1;
                    const dur = sliderMax - sliderMin;
                    const minDur = dur * 24 / columnAxisHeight;
                    let newMax = this.mouseStatus.selectedSlider.slider.max + dur * topDelta / columnAxisHeight;
                    let newMin = this.mouseStatus.selectedSlider.slider.min + dur * bottomDelta / columnAxisHeight;
                    if (newMax > sliderMax) {
                        newMax = sliderMax;
                    }
                    else if (newMin < sliderMin) {
                        newMin = sliderMin;
                    }
                    if (newMax - newMin < minDur) {
                        if (newMax == sliderMax) {
                            newMin = newMax - minDur;
                        }
                        else {
                            newMax = newMin + minDur;
                        }
                    }
                    if (this.mouseStatus.selectedSlider.slider.min != newMin
                        || this.mouseStatus.selectedSlider.slider.max != newMax) {
                        this.mouseStatus.selectedSlider.slider.min = newMin;
                        this.mouseStatus.selectedSlider.slider.max = newMax;
                        this.dataInfo.redraws.push(["slider", this.mouseStatus.selectedSlider.index]);
                        this.refreshSelectedLine();
                        this.onSliderChangeListener
                            && this.onSliderChangeListener(this.mouseStatus.selectedSlider.index, this.mouseStatus.selectedSlider.slider);
                    }
                }
            }
            this.redraw();
            this.mouseStatus.pos = curPos;
        };
        this.drawColumns();
        this.drawLines();
        this.drawSlider();
    }
    redraw(delay = 1000 / 60) {
        const innerRedraw = () => {
            const redrawSliderIndexes = {};
            const redrawLineIndexes = {};
            while (this.dataInfo.redraws.length > 0) {
                const item = this.dataInfo.redraws.pop();
                if (item[0] == "slider") {
                    redrawSliderIndexes[item[1]] = true;
                }
                else if (item[0] == "line") {
                    redrawLineIndexes[item[1]] = true;
                }
            }
            if (Object.keys(redrawSliderIndexes).length > 0) {
                this.drawSlider(redrawSliderIndexes);
            }
            if (Object.keys(redrawLineIndexes).length > 0) {
                this.drawLines(redrawLineIndexes);
            }
        };
        if (delay > 0) {
            setTimeout(() => {
                innerRedraw();
            }, delay);
        }
        else {
            innerRedraw();
        }
    }
    static isPointInRect(rect, point) {
        return rect && rect[0] < point[0] && rect[0] + rect[2] > point[0] && rect[1] < point[1] && rect[1] + rect[3] > point[1];
    }
    static clone(obj) {
        return JSON.parse(JSON.stringify(obj));
    }
}
//# sourceMappingURL=superParamVisual.js.map