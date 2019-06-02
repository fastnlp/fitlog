

// 负责summary的table的各种功能


function initTable() {
    // 重新生成Table
    var columns = convert_to_columns(window.column_order, window.column_dict,
                        window.hidden_columns);
    add_checkbox(columns);

    var data = [];
    for(var key in window.table_data){
        data.push(window.table_data[key]);
    }

    formTable(columns, data, true);

    // 在toggle新增加一个add row的操作
    // var new_button;
    // new_button = generate_a_button("btn btn-default", 'add', 'Add row', AddRowModal,
    //    '<i class="glyphicon glyphicon-plus"></i>');
    // new_button.setAttribute('data-toggle', 'modal');
    // new_button.setAttribute('data-target', '#row_box');
}

function processSummaryData(column_dict)
{
    // 将数据设置为居中，将一些内容设置为json类型
    for (var key1 in column_dict)
    {
        var v1 = column_dict[key1];
        v1['valign'] = 'middle';
        v1['align'] = 'center';
        if ('field' in v1){
            v1['class'] = 'word-wrap';
        }
        for(var key in v1)
        {
            if(v1[key] === 'true')
                v1[key] = true;
            if(v1[key] === 'false')
                v1[key] = false;
        }
        v1['escape'] = true;

    }
    return column_dict;
}

function formTable(columns, table_data, reorderable){
    $('#tb_summary').bootstrapTable('destroy').bootstrapTable({
        // url: '/table/data',         //请求后台的URL（*）
        // method: 'get',                      //请求方式（*）
        data: table_data,
        toolbar: '#toolbar',                //工具按钮用哪个容器
        striped: false,                      //是否显示行间隔色
        cache: true,                       //是否使用缓存，默认为true，所以一般情况下需要设置一下这个属性（*）
        pagination: false,                   //是否显示分页（*）
        maintainSelected:true,              // 当操作时，保持selected的对象不改变
        sortable: true,                     //是否启用排序
        sortOrder: "desc",                   //排序方式
        sortName: 'id',                     //依照哪个标准排序
        sidePagination: "client",           //分页方式：client客户端分页，server服务端分页（*）
        pageNumber: 1,                       //初始化加载第一页，默认第一页
        search: false,                       //是否显示表格搜索，此搜索是客户端搜索，不会进服务端，所以，个人感觉意义不大
        strictSearch: false,
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
        reorderableRows:reorderable,              //使用的话会导致无法选中copy
        undefinedText: '-',
        columns: columns,
        paginationVAlign: 'both',
});
}


function add_checkbox(columns) {
    //将columns增加一个operate栏与checkbox栏
    var max_depth = columns.length;

    //checkbox栏
    columns[0].splice(0, 0, {'checkbox':true, 'rowspan':max_depth, 'title':'checkbox', 'field': 'checkbox','valign':'middle',
                        'align':'center'});
    return columns;
}

