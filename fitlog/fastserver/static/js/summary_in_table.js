

// 这个文件主要是summary功能在table.html的相关函数

// 需要显示modal提示可以选择，或者新增一个summary
// 选择新增之后就在后台计算，如果成功了就会显示在下次打开的页面。如果失败了，下次打开就弹出失败的说明？或者还是等待结果

// 需要一个modal用于选择新增的summary规则

// 需要对应的table来显示最终的结果。


// 1.解决启动的问题，即生成modal的问题。从window.



$(function () {
    //

});

function getVerticalHorizontalSelections(column_dict) {
    // 从window.column_dict, 与window.unchanged_columns获取对应的可选值
    // column_dict: 二级json，key为header的名称，value是这个header的相关设置
    var field_headers = [];
    for(var key in window.column_dict){
        if(key in window.hidden_columns){
            continue
        }
        if(key.startsWith('metric-') || key.startsWith('other-')){
            var value = column_dict[key];
            if('field' in value){
                field_headers.push(value['field']);
            }
        }
    }

    return field_headers;
}

// 生成summary modal的html
function summaryModal(){
    // 只用生成内部的即可。
    // 1. 生成vertical, horizontal的selections. 只选择hyper与other中可以选择的. 允许只选择其中一个。
    var field_headers = [];
    

    // 2. 生成criterion的section

    // 3. 生成result的section

}
