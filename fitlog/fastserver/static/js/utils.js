

// 处理json数据.
/*
value是一个数组
[
    {}, //每一条是一次实验记录
    {},
    {}
]

 */
function processData(column_dict)
{
    // 将数据设置为居中，将一些内容设置为json类型
    for (var key1 in column_dict)
    {
        var v1 = column_dict[key1];
        v1['valign'] = 'middle';
        v1['align'] = 'center';
        if (('field' in v1) && window.settings['Wrap display']){
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

function change_field_class(columns, class_name) {
        columns.forEach(function (v1, i) {
            v1.forEach(function (v2, i) {
                if (('field' in v2)){
                    v2['class'] =class_name;
                }
                })
            });
    return columns;
}


function convert_to_columns(column_order, column_dict, hidden_columns) {
    // 根据column_order, column_dict, hidden_columns生成columns, columns可以用于生成table对象
    var max_depth = get_max_col_ord_depth(column_order);
    var columns = [];
    for(var i=0;i<max_depth;i++)
    {
        columns[i] = [];
    }

    generate_columns(column_order, column_dict, hidden_columns, '', columns, 0, max_depth);

    return columns;
}

function generate_columns(column_order, column_dict, hidden_columns, prefix, columns, depth, max_depth)
{
    var total_colspan = 0;

    var keys = get_order_keys(column_order);

    keys.forEach(function (key) {
        var field;
        if(prefix==='')
            field = key;
        else
            field = prefix + '-' + key;

        if(!(field in hidden_columns)) //没有隐藏
        {
            var item = column_dict[field];

            if(!(column_order[key]==='EndOfOrder')) // 说明还有下一层
            {
                var colspan = generate_columns(column_order[key], column_dict, hidden_columns, field, columns,
                    depth+1, max_depth);
                item['colspan'] = colspan;
                item['rowspan'] = 1;
                total_colspan += colspan;
            }else{
                item['rowspan'] = max_depth - depth;
                item['colspan'] = 1;
                total_colspan += 1;
            }
            if(item['colspan']!==0) //只有当下面的内容没有全被隐藏的时候才显示
                columns[depth].push(item);
        }
    });

    return total_colspan;
}

function get_order_keys(column_order) {
    // 给定order_columns返回他的key顺序. 按照这个顺序访问内容即可，已经删掉了OrderKeys关键字
    var keys = [];
    var key;
    if(column_order.hasOwnProperty('OrderKeys'))
    {
        column_order['OrderKeys'].forEach(function(key, i)
        {
            keys.push(key);
        });
    } else {
        for(key in column_order)
        {
            keys.push(key);
        }
    }
    return keys;
}

function get_max_col_ord_depth(value){
    // 根据column_order获取最大depth

    var depth = 0;
    var keys = get_order_keys(value);
    keys.forEach(function(key){
        if(value[key] === 'EndOfOrder')
            depth = Math.max(depth, 1);
        else
            depth = Math.max(depth, get_max_col_ord_depth(value[key])+1);
    });
    return depth;
}

var prompt = function (message, style, time)
{
    $('.alert').remove();
    style = (style === undefined) ? 'alert-success' : style;
    time = (time === undefined) ? 1200 : time;
    $('<div>')
        .appendTo('body')
        .addClass('alert ' + style)
        .html(message)
        .show()
        .delay(time)
        .fadeOut();
};

// 成功提示
var success_prompt = function(message, time)
{
    prompt(message, 'alert-success', time);
};

// 警告提示
var warning_prompt = function(message, time)
{
    prompt(message, 'alert-warning', time);
};





