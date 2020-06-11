class CharWrapper {

    constructor(name, type, data) {
        this.data = [];
        this.dataChanged = false;
        this.stepMax = 0;
        this.type = type;
        this.name = name;

        data.forEach(item => this.addLog(item));
        this.range = [0, this.stepMax];
        this.rangeEnable = false;

        this.chart = this.initChart();
        this.slider = null;
    }

    initChart() {
        const $box = $(`
            <div id="box_${this.name}" class="box_${this.type}">
                <h3 class="title" style="width: 100%; text-align: center">${this.name}</h3>
                <div class="chart"></div>
            </div>`);
        $("#charts").append($box);

        const chart = new G2.Chart({
            container: $box.find(".chart")[0],
            forceFit: true,
            height: document.body.clientHeight * 0.40,
            padding: [20, 210, 30, 50],
        });
        chart.source(this.data, {
            step: {
                range: [0, 1]
            }
        });
        chart.tooltip({
            useHtml:true,
            crosshairs: {
                type: 'line'
            },
            showTitle:false
        });
        // 使得两组颜色不一样
        if(this.type === 'metric'){
            chart.line().position('step*value').color('name');
            chart.point().position('step*value').color('name').size(5).shape('circle').style({
                stroke: '#fff',
                lineWidth: 1
            }).tooltip('name*epoch*step*value');
        }else{
            // todo
        }
        chart.axis('step', {});
        chart.legend({
            useHtml: true,
            position: 'right-center',
            reactive: true,
            legendStyle: {
                MARKER_CLASS: {
                    width: '20px',
                    height: '18px',
                    lineHeight: '18px',
                    borderRadius: '50px',
                    display: 'inline-block',
                    marginRight: '4px',
                    textAlign: 'center',
                    fontZize: '10px',
                    marginTop: '3px',
                    color: 'white',
                    float: 'left',
                    borderStyle: 'solid',
                    borderWidth: '1px',
                    borderColor: '#ccc'
                }
            },
            containerTpl: '<div class="g2-legend" style="font-weight: bold;font-size: 20px">Choose what to show' +
                '<div class="g2-legend-list"></div></div>',
        });
        chart.render();
        return chart;
    }

    addLog(log) {
        // console.log("add new log " + this.name,  log);
        this.dataChanged = true;
        this.stepMax = Math.max(this.stepMax, log.step);
        this.data.push(log);
    }

    refresh() {
        if (this.dataChanged) {
            this.dataChanged = false;
            this.chart.changeData(this.data);
        }
    }

    refreshRange() {
        let refreshRangeId = this.refreshRangeId = new Date().getTime();
        setTimeout(() => {
            if (refreshRangeId === this.refreshRangeId) {
                // console.log("refresh range");
                this.chart.filter('step', step => {
                    return !this.rangeEnable || (this.range[0] <= step && step <= this.range[1]);
                });
                // 调用 changeData 可以立即刷新，否则会有少许延迟
                this.chart.changeData(this.data);
            }
        }, 100);
    }

}

(async () => {
    const charts = [];

    // 第一次获取数据
    // function getFirstData() {
    //     // todo 下面的代码改为真实的请求数据的代码
    //     return new Promise((resolve, reject) => {
    //         jQuery.ajax({
    //             url: "/static/data_first.json",
    //             method: "GET",
    //             dataType: "json",
    //             data: {},
    //             success: res => {
    //                 if (res.status === 'fail') {
    //                     bootbox.alert(res.message);
    //                 }
    //                 else {
    //                     resolve(res);
    //                 }
    //             },
    //             error: e => {
    //                 reject(e);
    //                 bootbox.alert("Some error happens, stop updating data.");
    //             }
    //         })
    //     });
    // }

    // const firstData = await getFirstData();

    // 第一次绘制所有的 metric chart
    titles.forEach(title => {
        const data = [];
        const metricData = firstData[title];
        for (let logId of Object.keys(metricData)) {
            const logData = metricData[logId];
            logData.forEach(logItem => {
                data.push({
                    name: logId,
                    value: logItem[0],
                    step: logItem[1],
                    epoch: logItem[2]
                });
            });
        }
        charts.push(new CharWrapper(title, "metric", data));
    });

    const unchangedLogCounts = {};
    async function pullMoreData(unfinishedLogs) {
        const res = await new Promise((resolve, reject) => {
            jQuery.ajax({
                url: "/multi_chart/new_step",
                type: "POST",
                dataType: "json",
                contentType: 'application/json;charset=UTF-8',
                data: JSON.stringify({multi_chart_uuid: multi_chart_uuid}),
                success: res => {
                    if (res.status === 'fail') {
                        bootbox.alert(res.message);
                    }
                    else {
                        // console.log(res);
                        resolve(res['data']);
                    }
                },
                error: e => {
                    reject(e);
                    bootbox.alert("Some error happens, stop updating data.");
                }
            });
        });

        if (res.status === 'fail') {
            bootbox.alert(res.message);
            throw new Error(res.message);
        }

        const changedLogs = {};
        for (let title of titles) {
            // 将数据添加到已有的chart中，并记录有变化的logId
            const chartWrapper = charts.find(item => item.name === title);
            if(res.hasOwnProperty(title)){
                const metricData = res[title];
                for (let logId of Object.keys(metricData)) {
                    const logData = metricData[logId];
                    if (logData && logData.length) {
                        changedLogs[logId] = true;
                        logData.forEach(logItem => {
                            const newData = {
                                name: logId,
                                value: logItem[0],
                                step: logItem[1],
                                epoch: logItem[2]
                            };
                            chartWrapper.addLog(newData);
                        });
                    }
                }
                chartWrapper.refresh();
            }
        }
        // 更新 finish_status
        if(res.hasOwnProperty('finish_logs') && res['finish_logs'].length>0)
            res.finish_logs.forEach(log => finish_status[log] = true);
        for (let logId of Object.keys(finish_status)) {
            if (!finish_status[logId]) {
                if (changedLogs[logId]) {
                    unchangedLogCounts[logId] = 0;
                }
                else {
                    let count = unchangedLogCounts[logId] = (unchangedLogCounts[logId] || 0) + 1;
                    if (count >= firstData.max_no_updates) {
                        finish_status[logId] = true;
                    }
                }
            }
        }
        if(!finish_update_log){
            var flag = true;
            for(var key in finish_status){
                flag = finish_status[key] && flag;
            }
            if(flag){
                finish_update_log = true;
                bootbox.alert("Finish updating log.")
            }
        }
    }

    const intervalForDataPull = setInterval(async () => {
        try {
            const unfinishedLogs = logs.filter(log => !finish_status[log]);
            if (unfinishedLogs.length>0) {
                await pullMoreData(unfinishedLogs);
            }
            else {
                // 没有更多数据，停止加载
                clearInterval(intervalForDataPull);
            }
        }
        catch (e) {
            // 加载数据出现异常，停止加载
            console.error(e.stack);
            clearInterval(intervalForDataPull);
        }
    }, firstData.update_every * 1000);

    // range slider
    $("#range").on("click", () => {
        const $range_modal = $("#range_modal");
        // 为每一个 chart 绘制一个对应的 slider
        for (let chartWrapper of charts) {
            if (chartWrapper.slider === null) {
                const $sliderDiv = $(`
                    <div id="sliderDiv_${chartWrapper.name}" style="margin: 5px 0 5px 0;">
                        <div class="page__toggle" style="float:left; padding: 0 0; margin: 0 20px 0 0">
                            <label class="toggle" style="margin-bottom: 0">
                                <input class="toggle__input" type="checkbox"
                                    name = "${chartWrapper.name}" ${chartWrapper.rangeEnable ? "checked" : ""} 
                                    style="display: none; position: static; margin: 0">
                                <span class="toggle__label" style='padding: 0 0 0 24px'>
                                    <span class="toggle__text">${chartWrapper.name}</span>
                                </span>
                            </label>
                        </div>
                        <input id="${"range_bar_" + chartWrapper.name}" type="text" class="span2" style="width:75%"/>
                        <div class="clear"></div>
                    </div>
                `);
                $range_modal.append($sliderDiv);

                chartWrapper.slider = new Slider("#range_bar_" + chartWrapper.name, {
                    max: chartWrapper.stepMax,
                    value: chartWrapper.range,
                    enabled: chartWrapper.rangeEnable,
                    step: 50
                });
                chartWrapper.slider.on("change", event => {
                    chartWrapper.range = event.newValue;
                    chartWrapper.refreshRange();
                });

                $sliderDiv.find(".toggle__input").on("change", event => {
                    chartWrapper.rangeEnable = event.currentTarget.checked;
                    if (chartWrapper.rangeEnable) {
                        chartWrapper.slider.enable();
                    }
                    else {
                        chartWrapper.slider.disable();
                    }
                    chartWrapper.refreshRange();
                });
            }
        }
    });
})();
