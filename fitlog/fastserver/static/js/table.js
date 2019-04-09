
$(function () {
    //初始化setting选项
    var _settings = {};
    _settings['Ignore null value when filter'] = true;
    _settings['Wrap display'] = false;
    _settings['Pagination'] = true;
    _settings['Hide hidden columns when reorder'] = false;
    _settings['Offline'] = false;
    _settings['Save settings'] = true;
    _settings['Refresh from disk'] = false;
    _settings['Reorderable rows'] = false;
    window.settings = _settings;

    //0. 从后台获取必要的数据，然后用于创建Table
    $.ajax({
        url: '/table/table',
        type: 'GET',
        dataType: 'json',

        data: {

        },
        success: function(value){
            // 新加的column只能往后加，否则会出现hidden的时候顺序乱掉。
            var column_dict = value['column_dict'];
            var column_order = value['column_order'];
            var settings = value['settings'];
            var hidden_columns = value['hidden_columns'];
            column_dict = processData(column_dict);

            for(var setting in settings)
            {
                window.settings[setting] = settings[setting];
            }
            // refine columns
            window.column_order = column_order;
            window.column_dict = column_dict;
            window.hidden_columns = hidden_columns;
            window.table_data = value['data'];
            window.server_uuid = value['uuid'];
            window.hidden_rows = value['hidden_rows'];
            window.column_order_updated = false;
            window.hidden_columns_updated = false;
            window.unchanged_columns = value['unchanged_columns'];
            initalizeTable();
            // 如果unchanged_columns不为空，则使得button可见，否则不可见
           if($.isEmptyObject(window.unchanged_columns)){
               document.getElementById('consistent_cols').style.visibility = 'hidden';
           }else{
               document.getElementById('consistent_cols').style.visibility = 'visible';
           }

        },
        error: function(error){
            bootbox.alert("Some error happens when initialize table.");
        }
     });

});

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
        if(window.settings['Offline']){
            bootbox.alert("You are on offline mode, no action will send to the server.")
        }else{
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
                                bootbox.alert(error)
                            }
                    })
                  }
                })
            }
        }
    }
};

function operateFormatter(value, row, index) {
    return [
      '<a class="reset" href="javascript:void(0)" title="Reset">',
      '<i class="glyphicon glyphicon-backward"></i>',
      '</a>'
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

        //1.初始化Table
        TableInit().Init(columns, window.table_data, filterControl, window.settings['Pagination'],
                window.settings['Reorderable rows']);
        //2. 将不需要的row隐藏
        hide_row_by_ids(window.hidden_rows, $('#tb_departments'));
        // 如果存在hidden_rows，那么应该是需要显示的
       var hidden_rows = $table.bootstrapTable('getHiddenRows');
       if(hidden_rows.length>0){
           $display.prop('disabled', false);
       }
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
            sortOrder: "asc",                   //排序方式
            sortName: 'id',                     //依照哪个标准排序
            queryParams: oTableInit.queryParams,//传递参数（*）
            sidePagination: "client",           //分页方式：client客户端分页，server服务端分页（*）
            pageNumber: 1,                       //初始化加载第一页，默认第一页
            pageSize: 10,                       //每页的记录行数（*）
            pageList: [5, 10, 20, 30, 50, 'All'],        //可供选择的每页的行数（*）
            search: true,                       //是否显示表格搜索，此搜索是客户端搜索，不会进服务端，所以，个人感觉意义不大
            strictSearch: true,
            filterControl:filterControl,                 // 是否显示filter栏
            filterShowClear: true,              // 是否显示一键删除所有fitler条件的按钮
            hideUnusedSelectOptions: false,       //不要显示不存在的filter对象，如果为true再选择某个filter之后，这个filter其它选项都消失了
            showColumns: false,                  //是否显示所有的列
            stickyHeader: false,                 //是否固定header, 多级header时有bug，不能正常使用
            showRefresh: false,                  //是否显示刷新按钮
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
                        success: function (msg, status) {
                            if (status === "success") {
                                success_prompt(field + " update successfully.", 1500);
                            }
                            if (status === 'fail')
                            {
                                bootbox.alert("Fail to save your change. " + msg);
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
                success: function (msg, status) {
                    if (status === "success") {
                        // success_prompt( "Settings update successfully.", 1500);
                    }
                    if (status === 'fail'){
                        bootbox.alert("Fail to save your settings to server. " + msg);
                    }
                },
                error: function (msg, status) {
                    bootbox.alert("Error. " + msg);
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
            success: function (msg, status) {
                if (status === "success") {
                    // success_prompt( "Hidden rows update successfully.", 1500);
                }
                if (status === 'fail'){
                    bootbox.alert("Fail to save your hidden rows to server. " + msg);
                }
            },
            error: function (msg, status) {
                bootbox.alert("Error. "+msg);
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
            success: function (msg, status) {
                if (status === "success") {
                    // success_prompt( "Hidden columns update successfully.", 1500);
                }
                if (status === 'fail'){
                    bootbox.alert("Fail to save your hidden columns  to server." + msg);
                }
            },
            error: function (value) {
                bootbox.alert("Error. "+value);
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
            success: function (msg, status) {
                if (status === "success") {
                    // success_prompt( "Column order update successfully.", 1500);
                }
                if (status === 'fail'){
                    bootbox.alert("Fail to save your column order to server. " + msg);
                }
            },
            error: function (value) {
                bootbox.alert("Error. "+value);
            }
        })
    }
}

