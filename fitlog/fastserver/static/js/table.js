

function add_operate_checkbox(columns)
{
    //将columns增加一个operate栏与checkbox栏
    var max_depth = columns.length;

    columns[0].push({field:'operate', title:'action',
                        events: window.operateEvents,
                        formatter: operateFormatter, rowspan: max_depth, valign: 'middle', align:'center',
                        clickToSelect: false});
    //checkbox栏
    columns[0].splice(0, 0, {'checkbox':true, 'rowspan':max_depth, 'title':'checkbox', 'field': 'checkbox','valign':'middle',
                        'align':'center'});
    return columns;
}

window.operateEvents = {
    'click .reset': function (e, value, row, index) {
        if(row['meta-fit_id']===undefined){
            bootbox.alert("This version of code is not managed by fitlog, cannot reset.")
        }else{
            var msg="Are you going to revert to this version of code.";
            bootbox.confirm(msg, function(result){
              if(result){
                  $.ajax({
                        url: '/table/reset',
                        type: 'POST',
                        dataType: 'json',
                        contentType: 'application/json;charset=UTF-8',
                        data: JSON.stringify({
                             id: row['id'],
                             suffix: !window.settings['No suffix when reset'],
                             fit_id: row['meta-fit_id'],
                             uuid: window.server_uuid
                        }),
                        success: function(value){
                            var status = value['status'];
                            var msg = value['msg'];
                            if(status==='success'){
                                bootbox.alert("Reset succeed! " + msg);
                            }
                            else{
                                bootbox.alert("Reset failed! " + msg);
                            }
                        },
                        error: function(error){
                            bootbox.alert('Error encountered. ');
                        }
                })
              }
            })
        }
    },
    'click .trend': function (e, value, row, index) {
          var finish = false;
          if(row['state']==='finish'){
              finish = true;
          }
          $.ajax({
                url: '/chart/have_trends',
                type: 'POST',
                dataType: 'json',
                contentType: 'application/json;charset=UTF-8',
                data: JSON.stringify({
                     uuid: window.server_uuid,
                     log_dir: row['id']
                }),
                success: function(value){
                    var status = value['status'];
                    if(status==='success' && value['have_trends']){
                        openPostWindow('/chart', {'log_dir': row['id'], 'finish': finish});
                    } else{
                        bootbox.alert(value['msg']);
                    }
                },
                error: function(error){
                    bootbox.alert("Some error happens. You may disconnect from the server.");
                }
        })
    },
    'click .file': function (e, value, row, index) {
          $.ajax({
                url: '/table/is_file_exist',
                type: 'POST',
                dataType: 'json',
                contentType: 'application/json;charset=UTF-8',
                data: JSON.stringify({
                     uuid: window.server_uuid,
                     id: row['id'],
                }),
                success: function(value){
                    var status = value['status'];
                    if(status==='success'){
                        openPostWindow('/table/get_file', {'id': row['id'], 'filename': value['filename'],
                            "uuid": window.server_uuid});
                    } else{
                        bootbox.alert(value['msg']);
                    }
                },
                error: function(error){
                    bootbox.alert("Some error happens. You may disconnect from the server.");
                }
        })
    },
};


function openPostWindow(url, params)
{
    // 打开新的页面
    var form = document.createElement("form");
    form.setAttribute("method", "post");
    form.setAttribute("action", url);
    form.setAttribute("target", '_blank');

    for (var i in params) {
        if (params.hasOwnProperty(i)) {
            var input = document.createElement('input');
            input.type = 'hidden';
            input.name = i;
            input.value = params[i];
            form.appendChild(input);
        }
    }
    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form);
}


function operateFormatter(value, row, index) {
    return [
       '<div style="display:inline-block; float: none; width: 70px">',
      '<a class="reset" href="javascript:void(0)" title="Reset">',
      '<i class="glyphicon glyphicon-share-alt" style="padding:0px 2px 0px 1px"></i>',
      '</a>',
      '<a class="trend" href="javascript:void(0)" title="Thread">',
      '<i class="glyphicon glyphicon-tasks" style="padding:0px 1px 0px 1px"></i>',
      '</a>',
      '<a class="file" href="javascript:void(0)" title="File">',
      '<i class="glyphicon glyphicon-list-alt" style="padding:0px 1px 0px 2px"></i>',
      '</a>',
       "</div>"
    ].join('')
}


function initalizeTable(){
        var columns = convert_to_columns(window.column_order, window.column_dict,
                            window.hidden_columns);

        if(window.settings['Wrap display']){
            columns = change_field_class(columns, 'word-wrap');
        }else{
            columns = change_field_class(columns, '');
        }

        //将operate和checkbox加入
        add_operate_checkbox(columns);
        var filterControl = false;
        columns.forEach(function (value, i) {
            value.forEach(function (v, i) {
                if("filterControl" in v)
                {
                    filterControl = true;
                }
            })
        });

        var data = [];
        for(var key in window.table_data){
            data.push(window.table_data[key]);
        }

        //1.初始化Table
        TableInit().Init(columns, data, filterControl, window.settings['Pagination'],
                window.settings['Reorderable rows']);
        //2. 将不需要的row隐藏
        hide_row_by_ids(window.hidden_rows, $('#tb_departments'));
        // 如果存在hidden_rows，那么应该是需要显示的
       var hidden_rows = $table.bootstrapTable('getHiddenRows');
       if(hidden_rows.length>0){
           $display.prop('disabled', false);
       }

       // 在toggle新增加一个add row的操作
       var new_button;
       new_button = generate_a_button("btn btn-default", 'add', 'Add row', AddRowModal,
           '<i class="glyphicon glyphicon-plus"></i>');
       new_button.setAttribute('data-toggle', 'modal');
       new_button.setAttribute('data-target', '#row_box');
       document.getElementsByClassName('columns').item(0).appendChild(new_button);
       // 保存配置
       new_button = generate_a_button("btn btn-default", 'save', 'Save', save_filter_conditions,
           '<i class="glyphicon glyphicon-floppy-save   "></i>');
       document.getElementsByClassName('columns').item(0).appendChild(new_button);
       // 显示所有的config_name
       new_button = generate_a_button("btn btn-default", 'config', 'Configs', change_config,
           '<i class="glyphicon glyphicon-file"></i>');
       document.getElementsByClassName('columns').item(0).appendChild(new_button);
       //显示选中的row的statics
        new_button = generate_a_button("btn btn-default", 'statistics', 'Stats', show_statistics,
            '<i class="glyphicon glyphicon-stats"></i>');
        document.getElementsByClassName('columns').item(0).appendChild(new_button);
       //显示summary
        new_button = generate_a_button('btn btn-default', 'summary', 'Summary', jump_to_summary,
            '<i class="glyphicon glyphicon-usd"></i>');
        document.getElementsByClassName('columns').item(0).appendChild(new_button);
       // 在toggle新增一个poweroff的按钮
       new_button = generate_a_button("btn btn-default", 'Poweroff', 'PoweOff', ShutDownServer,
           '<i class="glyphicon glyphicon-off"></i>');
       document.getElementsByClassName('columns').item(0).appendChild(new_button);
}

function generate_a_button(className, name, title, onclick, innerHTML){
    var new_button = document.createElement("button");
    new_button.className = className;
    new_button.type = 'button';
    new_button.name = name;
    new_button.title = title;
    new_button.onclick = onclick;
    new_button.innerHTML = innerHTML;
    return new_button
}

function show_statistics(){
    // 获取已经选中的ids
    var ids = getIdSelections();
    if(ids.length<2){
        bootbox.alert("You have not chosen enough logs(at least 2).")
    }else{
        // 计算它们的metric下面的值。目前仅支持完全都有的，不支持缺省的
        var logs = [];
        for(var index=0;index<ids.length;index++){
            logs.push(window.table_data[ids[index]]);
        }
        // 获取所有的值
        var metrics = {};
        var log;
        for(var index=0;index<logs.length;index++){
            log = logs[index];
            for(var key in log){
                if(key.startsWith('metric')){
                    if(key==='metric-epoch' || key==='metric-step'){
                        continue
                    }
                    if(!(key in metrics)){
                        metrics[key] = [log[key]];
                    }else{
                        metrics[key].push(log[key]);
                    }
                }
            }
        }
        // 判断是否都有相同的长度。
        for(var key in metrics){
            if(metrics[key].length!==ids.length){
                bootbox.alert(key + " has empty entries.");
                return;
            }
        }
        // 判断是否有哪一行是所有的都一样的
        var log_values = {};
        for(var index=0;index<logs.length;index++){
            log = logs[index];
            for(var key in log){
                if(!(key in log_values)){
                    log_values[key] = [log[key]];
                }else{
                    log_values[key].push(log[key]);
                }
            }
        }
        var values;
        var value_set;
        var invariant_values = {};
        for(var key in log_values){
            values = log_values[key];
            value_set = new Set(values);
            if(values.length===ids.length && value_set.size===1){
                invariant_values[key] = values[0];
            }
        }

        // 前端页面显示需要展示的值
        var formatted_metrics = calculate_stats(metrics);
        if(getJsonKeys(formatted_metrics).length>0){
            //
            window.row_stats = {'ids': ids, 'stats':formatted_metrics, 'invariant_values': invariant_values};
            var html = generate_metric_stats_table(formatted_metrics);
             $('#stats_dialogue').append(html).append('<p>Calculate from <span style="color: red;font-weight: bold;">' +
                 ids.length + '</span> logs(metric-wise max/min).</p>');
            $('#stats_box').modal('show');
        }else{
            bootbox.alert("No valid value found.")
        }
    }
}


function jump_to_summary() {
    // 决定需要跳转到line还是table
    bootbox.prompt({
        'title': "Which kind of summary?",
        "message": "<p>Please select an option below:</p>",
        "inputType":"radio",
        "inputOptions": [
            {
                'text': "line",
                "value": "1"
            },
            {
                "text": 'table',
                "value": "2"
            }
        ],
        callback:function (result) {
            if(result==='1'){
                jump_to_summary_line()
            }else if (result==='2'){
                jump_to_summary_table()
            }
        }
    })
}


function jump_to_summary_line() {
    var ids = getIdSelections();
    if(ids.length>1){
        openPostWindow('/line', {'ids': ids});
    }else{
        bootbox.alert("You have to choose at least two log.")
    }
}

function jump_to_summary_table() {
    // 点击之后弹框跳转
    var ids = getIdSelections();
    if(ids.length>0){
        var msg = "Generate summary on " + ids.length + " selected data?";
        bootbox.confirm(msg, function (result) {
            if(result){
                openPostWindow('/summary', {'ids': ids});
            }
        })
    }else{
        var msg = "This will open a new summary page, go on?";
        bootbox.confirm(msg, function (result) {
            if(result){
                window.open('/summary');
            }
        })
    }
}


function AddRowModal() {
    // 点击add row之后弹出一个modal. 对应的确认处理在table.html页面
   generate_add_row_columns(window.column_order, window.column_dict, window.hidden_columns,
       $("#add_row_dialogue"));
}

function ShutDownServer() {
    bootbox.confirm("This will shut down the server, are you sure to go on?", function(result){
        if(result){
          $.ajax({
                url: '/arange_kill',
                type: 'POST',
                dataType: 'json',
                contentType: 'application/json;charset=UTF-8',
                data: JSON.stringify({
                     uuid: window.server_uuid
                }),
                success: function(value){
                    var status = value['status'];
                    if(status==='success'){
                        success_prompt("Server is going to shut down in several seconds.")
                    } else{
                        bootbox.alert(value['msg']);
                    }
                },
                error: function(error){
                    bootbox.alert("Some error happens. Fail to shut server down, please shut down in the server.");
                }
            })
        }
    })

}


var TableInit = function () {
    var oTableInit = new Object();
    //初始化Table
    oTableInit.Init = function (use_columns, table_data, filterControl, pagination,
                                reorderable_row) {
        $('#tb_departments').bootstrapTable('destroy').bootstrapTable({
            // url: '/table/data',         //请求后台的URL（*）
            // method: 'get',                      //请求方式（*）
            data: table_data,
            toolbar: '#toolbar',                //工具按钮用哪个容器
            striped: false,                      //是否显示行间隔色
            cache: true,                       //是否使用缓存，默认为true，所以一般情况下需要设置一下这个属性（*）
            pagination: pagination,                   //是否显示分页（*）
            maintainSelected:true,              // 当操作时，保持selected的对象不改变
            sortable: true,                     //是否启用排序
            sortOrder: "desc",                   //排序方式
            sortName: 'id',                     //依照哪个标准排序
            queryParams: oTableInit.queryParams,//传递参数（*）
            sidePagination: "client",           //分页方式：client客户端分页，server服务端分页（*）
            pageNumber: 1,                       //初始化加载第一页，默认第一页
            pageSize: 10,                       //每页的记录行数（*）
            pageList: [5, 10, 20, 30, 50, 'All'],        //可供选择的每页的行数（*）
            search: true,                       //是否显示表格搜索，此搜索是客户端搜索，不会进服务端，所以，个人感觉意义不大
            strictSearch: false,
            filterControl:filterControl,         // 是否显示filter栏
            filterShowClear: true,              // 是否显示一键删除所有fitler条件的按钮
            hideUnusedSelectOptions: false,       //不要显示不存在的filter对象，如果为true再选择某个filter之后，这个filter其它选项都消失了
            searchOnEnterKey: false,              //输入enter才开始搜索, 不能用，否则select没响应
            showColumns: false,                  //是否显示所有的列
            stickyHeader: false,                 //是否固定header, 多级header时有bug，不能正常使用
            showRefresh: true,                  //是否显示刷新按钮
            minimumCountColumns: 2,             //最少允许的列数
            clickToSelect: true,                //是否启用点击选中行
            // height: 700,                        //行高，如果没有设置height属性，表格自动根据记录条数觉得表格高度.
            uniqueId: "id",                     //每一行的唯一标识，一般为主键列
            idField: "id",                      // id列
            showToggle: false,                    //是否显示详细视图和列表视图的切换按钮
            cardView: false,                    //是否显示详细视图
            detailView: false,                   //是否显示父子表
            showExport: true,                     //是否显示导出
            exportDataType: "basic",              //basic', 'all', 'selected'.
            exportTypes: ['json', 'csv', 'txt', 'excel'],
            reorderableRows:reorderable_row,              //使用的话会导致无法选中copy
            undefinedText: '-',
            columns: use_columns,
            paginationVAlign: 'both',
            onEditableSave: function (field, row, oldValue, $el) {
                $('#tb_departments').bootstrapTable('resetView');
                if(!window.settings['Offline']){
                    $.ajax({
                        type: "post",
                        url: "/table/edit",
                        contentType: 'application/json;charset=UTF-8',
                        data: JSON.stringify({
                            field: field,
                            id: row['id'],
                            new_field_value: row[field],
                            uuid: window.server_uuid}),
                        success: function (res, status) {
                            if (res['status'] === "success") {
                                success_prompt(field + " update successfully.", 1500);
                            }
                            if (res['status'] === 'fail')
                            {
                                bootbox.alert("Fail to save your change. " + res['msg']);
                            }
                        },
                        error: function (value) {
                            bootbox.alert("Error. "+value);
                        }
                    });
                }
            }
        });
    };

    //得到查询的参数
    oTableInit.queryParams = function (params) {
        var temp = {   //这里的键的名字和控制器的变量名必须一直，这边改动，控制器也需要改成一样的
            limit: params.limit,   //页面大小
            offset: params.offset,  //页码
            departmentname: $("#txt_search_departmentname").val(),
            statu: $("#txt_search_statu").val()
        };
        return temp;
    };
    return oTableInit;
};

function update_config_name(config_name){
    if(!window.settings['Offline']){
           $.ajax({
                type: "post",
                url: "/table/save_config_name",
                contentType: 'application/json;charset=UTF-8',
                data: JSON.stringify({
                    save_config_name: config_name,
                    uuid: window.server_uuid}),
                success: function (res, status) {
                    if (res['status'] === 'fail'){
                        bootbox.alert("Fail to set your config name. " + res['msg']);
                    }else{
                        window.save_config_name = res['msg'];
                        success_prompt("Successfully change the save name for current settings.", 3000)
                    }
                },
                error: function (value) {
                    bootbox.alert("Fail to synchronize your config name to the server.")
                }
            })
    }
}


function update_settings(settings){
    // 将新的settings更新到后端
    if(!window.settings['Offline']){
        $.ajax({
                type: "post",
                url: "/table/settings",
                contentType: 'application/json;charset=UTF-8',
                data: JSON.stringify({
                    settings: settings,
                    uuid: window.server_uuid}),
                success: function (res, status) {
                    if (res['status'] === "success") {
                        // success_prompt( "Settings update successfully.", 1500);
                    }
                    if (res['status'] === 'fail'){
                        bootbox.alert("Fail to save your settings to server. " + res['msg']);
                    }
                },
                error: function (msg, status) {
                    bootbox.alert("Error. If the server shuts down or you can not connect to the server, check Offline " +
                        "in settings")
                }
        })
    }
}


function update_hide_row_ids(ids){
    //将需要隐藏的row的id发送到后端
    if(!window.settings['Offline']){
        $.ajax({
            type: "post",
            url: "/table/hidden_rows",
            contentType: 'application/json;charset=UTF-8',
            data: JSON.stringify({
                ids: ids,
                uuid: window.server_uuid}),
            success: function (res, status) {
                if (res['status'] === "success") {
                    // success_prompt( "Hidden rows update successfully.", 1500);
                }
                if (res['status'] === 'fail'){
                    bootbox.alert("Fail to save your hidden rows to server. " + res['msg']);
                }
            },
            error: function (msg, status) {
                bootbox.alert("Error. If the server shuts down or you can not connect to the server, check Offline " +
                    "in settings")
            }
        })
    }

}


function update_hidden_columns(hidden_columns) {
    // 将隐藏的column发送到后端
    if(!window.settings['Offline']){
        $.ajax({
            type: "post",
            url: "/table/hidden_columns",
            contentType: 'application/json;charset=UTF-8',
            data: JSON.stringify({
                hidden_columns: hidden_columns,
                uuid: window.server_uuid}),
            success: function (res, status) {
                if (res['status'] === "success") {
                    // success_prompt( "Hidden columns update successfully.", 1500);
                }
                if (res['status'] === 'fail'){
                    bootbox.alert("Fail to save your hidden columns  to server." + res['msg']);
                }
            },
            error: function (value) {
                bootbox.alert("Error. If the server shuts down or you can not connect to the server, check Offline " +
                    "in settings")
            }
        })
    }

}


function update_column_order(column_order) {
    // 将生成的column顺序发送到前端
    if(!window.settings['Offline']){
        $.ajax({
            type: "post",
            url: "/table/column_order",
            contentType: 'application/json;charset=UTF-8',
            data: JSON.stringify({
                column_order: column_order,
                uuid: window.server_uuid}),
            success: function (res, status) {
                if (res['status'] === "success") {
                    // success_prompt( "Column order update successfully.", 1500);
                }
                if (res['status'] === 'fail'){
                    bootbox.alert("Fail to save your column order to server. " + res['msg']);
                }
            },
            error: function (value) {
                bootbox.alert("Error. If the server shut down or you can not connect to the server, check Offline " +
                    "in settings");
            }
        })
    }
}


function update_new_row(row){
    if(!window.settings['Offline']){
        $.ajax({
            type: "post",
            url: "/table/row",
            contentType: 'application/json;charset=UTF-8',
            data: JSON.stringify({
                row: row,
                uuid: window.server_uuid}),
            success: function (res, status) {
                if (res['status'] === "success") {
                    // success_prompt( "Column order update successfully.", 1500);
                }
                if (res['status'] === 'fail'){
                    bootbox.alert("Fail to save your new row to server. " + res['msg']);
                }
            },
            error: function (value) {
                bootbox.alert("Error. If the server shut down or you can not connect to the server, check Offline " +
                    "in settings");
            }
        })
    }
}


function update_filter_condition(condition, only_save) {
    // condition: 一级json; only_save: bool是否只保存没有condition
    if(!window.settings['Offline']){
        if(!only_save){
            var data = JSON.stringify({
                    condition: condition,
                    uuid: window.server_uuid});
        }else{
            var data = JSON.stringify({
                    uuid: window.server_uuid});
        }

        $.ajax({
            type: "post",
            url: "/table/save_settings",
            contentType: 'application/json;charset=UTF-8',
            data: data,
            success: function (res, status) {
                if (res['status'] === "success") {
                    success_prompt( "Setting are saved to " + window.save_config_name + " successfully.", 1500);
                    if(!only_save) // 如果不是只save，还需要刷新页面
                        window.location.reload();
                }
                if (res['status'] === 'fail'){
                    bootbox.alert("Fail to save your settings to server. " + res['msg']);
                }
            },
            error: function (value) {
                bootbox.alert("Error. If the server shut down or you can not connect to the server, check Offline " +
                    "in settings");
            }
        })
    }
}