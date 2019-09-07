
function rgbToHex(r, g, b) {
    return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
}


function get_bg_color(depth, max_depth) {
    // 自动为没一层生成背景颜色。depth从0开始
    var start = 240;
    var color;
    if(max_depth>4) // 如果小于这个值，则每次减30
    {
        var end = 120;
        color = Math.ceil(start - (start - end)/max_depth*depth);
    }
    else
    {
        color = start - 30*depth;
    }

    return rgbToHex(color, color, color)
}

function generate_sortable_columns(column_order, column_dict, hidden_columns, ele) {
    /*
    column_order: json对象，是每一级的顺序，可以通过OrderKeys元素保证顺序
    column_dict: json对象，2级json，key是path，value是column的item
    hidden_columns: json对象, 如果某个path在里面，则该内容是隐藏的
    ele: 将内容append到哪里, 一般是某个modal的内部元素。
     */

    var max_depth = get_max_col_ord_depth(column_order);
    var html = "<div id=\"choose_column_nested\" class=\"list-group col nested-sortable\">";
    html += generate_sortable_column_group(column_order, column_dict, hidden_columns, '', 0, max_depth,
        false);
    html += '</div>';
    ele.append(html);

}

function generate_sortable_column_group(column_order, column_dict, hidden_columns, prefix, depth, max_depth, hide) {
    // 给定column_order的内容，创建元素
    var html = "";
    var keys = get_order_keys(column_order);
    var ignore = true;
    keys.forEach(function (key) {
        var field,group;
        var _hide = false;
        if(prefix==='')
        {
            field = key;
            group = '#';
        } else{
            field = prefix + '-' + key;
            group = prefix;
        }

        var item = column_dict[field];

        if(!hide && (field in hidden_columns))
            _hide = true;

        if(!(_hide && window.settings['Hide hidden columns when reorder'])){
            var new_add_html = '';
            if(column_order[key]==='EndOfOrder'){ //说明这是最后一层了
                new_add_html += generate_for_end_item(item, depth, max_depth, field, !_hide, true);
            }else{
                new_add_html += generate_for_end_item(item, depth, max_depth, field, !_hide, false);
                new_add_html += "<div class=\"list-group nested-sortable\" id='" + group + "'>";
                var child_html = generate_sortable_column_group(column_order[key], column_dict, hidden_columns, field,
                    depth+1, max_depth, hide);
                if(child_html==='') // 如果子节点为空，则没有必要创建了
                    new_add_html = '';
                else
                    new_add_html += child_html + "</div></div>";
            }
            html += new_add_html;
        }
    });
    return html;
}


function generate_for_end_item(item, depth, max_depth, path, hide, include_last_div) {
    // 为终点结构生成一个div block
    var color = get_bg_color(depth, max_depth);
    var title = item['title'];
    var html;
    if(include_last_div)
        html = "<div class=\"list-group-item\" title='" + title + "' style='background-color: "+ color +"'>" +
            generate_checkbox(title, path, hide) + "</div>";
    else
        html = "<div class=\"list-group-item\" title='" + title + "' style='background-color: "+ color +"'>" +
            generate_checkbox(title, path, hide);
    return html
}

function generate_checkbox(title, path, checked) {
    // 给定title, path, 和checked(bool)状态生成一段checkbox的html
    if(checked)
        checked = 'checked';
    else
        checked = '';

    var html = "              <div class=\"page__toggle\" style=\"padding: 0 0;margin: 0 0\">\n" +
        "                      <label class=\"toggle\" style=\"margin-bottom: 0\">\n" +
        "                        <input class=\"toggle__input\" type=\"checkbox\" id='choose_column_checkbox' " +
        " name='" + path + "' " + checked + " style='position:static;margin:0;display:none'>\n" +
        "                        <span class=\"toggle__label\" style='padding: 0 0 0 24px'>\n" +
        "                          <span class=\"toggle__text\">" + title + "</span>\n" +
        "                        </span>\n" +
        "                      </label>\n" +
        "                    </div>";
    return html
}

/*
层级checkbox https://codepen.io/seemikehack/pen/bpdrGB
 */


function change_children_state($group_item, state) {
    // 将后代的check状态与自己的设置为一致
    var $group_list = $group_item.children('.list-group');
    if(!($group_list.length>0)){ //说明有子类
        var $group_items = $group_list.children('.list-group-item');
        for(var i=0;i<$group_items.length;i++)
        {
            change_children_state($group_items[i], state);
        }
    }else{
        $group_item.find('input').prop('checked', state); // 如果这个没有下一级了，就设置属性
    }
}

function change_parent_state($group_item, state){
    // 根据情况设置parent的状态

    $group_item.find('input').first().prop('checked', state);

    $siblings = $group_item.siblings();
    for(var i=0;i<$siblings.length;i++) // 统计状态，向上汇报
    {
        state = $($siblings[i]).find('input').prop('checked') || state;
    }

    var $parents = $group_item.closest('.list-group');
    if(!($parents[0].getAttribute('id') === 'choose_column_nested')) //还没有到头的时候往上继续传递
    {
        var $parent_item = $parents.closest('.list-group-item');
        change_parent_state($parent_item, state);
    }
}

function check_checkbox_valid($group_item){
    // 给定最顶层的group_item从最底层向上check
    var $item_list = $group_item.children('.list-group-item');
    for(var i=0;i<$item_list.length;i++)
    {
        var $item = $($item_list[i]); // 获取item
        var $group_list = $item.children('.list-group');
        if($group_list.length>0){ // 如果还有下面的
            check_checkbox_valid($($group_list[0]));
        }else{
            change_parent_state($item, $item.find('input').prop('checked'));
        }
    }
}


// 确认顺序之后调用
function get_new_column_order(sortable_item, column_order) {
    // 给定以上的对象，生成新的column_order，返回一个新的order_dict顺序
    var new_column_order = {};
    var items = sortable_item.children('.list-group-item');  // 得到所有的list-group-item, 有可能为空
    var new_key_order = [];
    var old_key_order = get_order_keys(column_order);
    for(var i=0;i<items.length;i++)
    {
        var item = items[i];
        var new_column_value;
        var key = item.getAttribute('title');
        var child_group = $(item).children('.list-group');
        if(child_group.length>0){ //有可能有下有的节点
           new_column_value = get_new_column_order($(child_group), column_order[key])
        }else{ // 没有更下面的节点了
           new_column_value = 'EndOfOrder';
        }
        new_key_order.push(key);
        new_column_order[key] = new_column_value;
        old_key_order[old_key_order.indexOf(key)] = "AlreadyInReorder"
    }
    // 把没有显示的value加进去
    old_key_order.forEach(function (key) {
        // new_key_order.push(key);
        if(!(key in new_column_order))
            new_column_order[key] = column_order[key];
    });

    // 重新组织一下key的顺序，保证new_key_order在old_key_order是一致
    var new_order_index = 0;
    for(var index=0;index<old_key_order.length;index++){
        if(old_key_order[index]==='AlreadyInReorder'){
            if(old_key_order[index] !== new_key_order[new_order_index]){ // 需要更新column
                old_key_order[index] = new_key_order[new_order_index];
                window.column_order_updated = true
            }
            new_order_index += 1;
        }
    }

    console.assert(new_order_index===new_key_order.length, "Bug");
    new_column_order['OrderKeys'] = old_key_order;

    return new_column_order
}

// 更新hidden_columns
function get_new_hidden_columns(sortable_item, new_hidden_columns, prefix) {
    var items = sortable_item.children('.list-group-item');  // 得到所有的list-group-item, 有可能为空
    for(var i=0;i<items.length;i++)
    {
        var item = items[i];
        var key = item.getAttribute('title');
        var field;
        if(prefix===''){
            field = key;
        } else{
            field = prefix + '-' + key;
        }
        var child_group = $(item).children('.list-group');
        if(child_group.length>0){ //有可能有下有的节点
           get_new_hidden_columns($(child_group), new_hidden_columns, field)
        }else{ // 没有更下面的节点了
           var checkbox = $(item).find('input');
           var checked = checkbox.prop('checked');
           if(!checked){ // 如果没有选中
               if(!(field in new_hidden_columns)) //不在之前的内容里面, 需要更新
                  window.hidden_columns_updated = true;
               new_hidden_columns[field] = 1;
           } else if(checked && field in new_hidden_columns){ //需要更新hidden
               delete new_hidden_columns[field];
               window.hidden_columns_updated = true;
           }
        }
    }
}




// 以下的几个函数用于生成增加row的modal
function add_a_row(row, update_to_server){
    //row: {'id':, 'key1': value}
    // 增加到table中
    $table.bootstrapTable('prepend', row);
    // 保存到服务器
    if(update_to_server || update_to_server===undefined)
        update_new_row(row);
    window.table_data[row['id']] = row;
}

function generate_add_row_columns(column_order, column_dict, hidden_columns, ele) {
    /*
    column_order: json对象，是每一级的顺序，可以通过OrderKeys元素保证顺序
    column_dict: json对象，key是path，value是column的item
    hidden_columns: json对象, 如果某个path在里面，则直接该内容是隐藏的
    ele: 将内容append到哪里
     */

    var max_depth = get_max_col_ord_depth(column_order);
    var html = "<div id=\"add_row_nested\" class=\"list-group col nested-sortable\">";
    html += generate_hierachy_column_when_add_row(column_order, column_dict, hidden_columns, '', 0, max_depth,
        false);
    html += '</div>';
    ele.append(html);

}

function generate_hierachy_column_when_add_row(column_order, column_dict, hidden_columns, prefix, depth, max_depth, hide) {
    // 给定column_order的内容，创建层级元素，用于新增一个rows
    var html = "";
    var keys = get_order_keys(column_order);
    var ignore = true;
    keys.forEach(function (key) {
        var field,group;
        var _hide = false;
        if(prefix==='')
        {
            field = key;
            group = '#';
        } else{
            field = prefix + '-' + key;
            group = prefix;
        }

        var item = column_dict[field]; // 一个json对象，包含field, title, editable等

        if(!hide && (field in hidden_columns))
            _hide = true;

        if(!(_hide && window.settings['Hide hidden columns when reorder'])){
            var new_add_html = '';
            if(column_order[key]==='EndOfOrder'){ //说明这是最后一层了
                new_add_html += generate_add_row_for_end_item(item, depth, max_depth, field, true);
            }else{
                new_add_html += generate_add_row_for_end_item(item, depth, max_depth, field, false);
                new_add_html += "<div class=\"list-group nested-sortable\" id='" + group + "'>";
                var child_html = generate_hierachy_column_when_add_row(column_order[key], column_dict, hidden_columns, field,
                    depth+1, max_depth, hide);
                if(child_html==='') // 如果子节点为空，则没有必要创建了
                    new_add_html = '';
                else
                    new_add_html += child_html + "</div></div>";
            }
            html += new_add_html;
        }
    });
    return html;
}


function generate_add_row_for_end_item(item, depth, max_depth, path, include_last_div) {
    // 为终点结构生成一个div block
    // include_last_div是否需要补齐一个</div>
    var color = get_bg_color(depth, max_depth);
    var title = item['title'];
    var html;
    if(include_last_div)
        html = "<div class=\"list-group-item\" title='" + title + "' style='background-color: "+ color +"'>" +
            generate_add_input(title, path, item['field']) + "</div>";
    else
        html = "<div class=\"list-group-item\" title='" + title + "' style='background-color: "+ color +"'>" +
            generate_add_input(title, path, item['field']);
    return html
}

function generate_add_input(title, path, id) {
    // 给定title, path, id(相当与是field_name, 只有需要填写内容的field才有的)生成一段input的html

    if(id===undefined){
         var html = "              <div class=\"page__toggle\" style=\"padding: 0 0;margin: 0 0\">\n" +
            "                      <label class=\"toggle\" style=\"margin-bottom: 0\">\n" +
            "                          <span class=\"toggle__text\">" + title + "</span>\n" +
            "                      </label>\n" +
            "                    </div>";
    }else{
        var placeholder = '';
        if(id==='id'){
            placeholder += 'placeholder=required';
        }
        var html = '<div class="page__toggle" style="padding: 0 0;margin: 0 0">' +
                '<label class="toggle" style="margin-bottom: 0">' +
                    '<span class="toggle__text">' + title +': </span>' +
                    '<input type="text" name="input_row" ' + placeholder +' id='+id+'>' +
                '</label>' +
                '</div>';
    }
    return html
}

// 将当前设置保存到文件; 如果有filter条件，一并保存，如果有filter条件将触发刷新页面。
// TODO 修改为弹窗
function save_filter_conditions(){
    // 获取当前filter条件
    var filter_divs = document.getElementsByClassName('filter-control');

    var condition = {};
    for(var index=0;index<filter_divs.length;index++){
        var filter = filter_divs[index].children[0];
        var value='';
        var key = filter.className.split(' ')[1].substring(31);
        if(filter.tagName==='INPUT'){
            value = filter.value;
        }else if(filter.tagName==='SELECT'){
            var _index=filter.selectedIndex;
            if(filter.options[_index].value!=='' && filter.options[_index].value!==undefined)
                value  = '=' + filter.options[_index].value;
        }
        if(value!==undefined &&value!==''){
            condition[key] = value;
        }
    }
    if(Object.keys(condition).length!==0){
        if($table.bootstrapTable('getData', false).length===0){
            bootbox.alert("There is no data qualify your condition.")
        }else{
            bootbox.prompt({
                title:"Whether to save filter conditions.",
                inputType:'radio',
                inputOptions:[
                    {
                        text:'True',
                        value: 'true',
                    },{
                        text:'False',
                        value: 'false',
                    }
                ],
                callback:function (result) {
                    console.log(result);
                    if(result==='true'){
                        update_filter_condition(condition, false);
                    }else if(result==='false'){
                        update_filter_condition(condition, true);
                    }
                }
            });

        }
    }else{
         update_filter_condition(condition, true);
    }
}

//生成一个4位uuid
function generate_uuid() {
    return (((1+Math.random())*0x10000)|0).toString(16).substring(1);
}


/*
用于处理切换config

 */
//1. 生成对应的modal
function change_config(){
      $.ajax({
            url: '/table/configs',
            type: 'POST',
            dataType: 'json',
            contentType: 'application/json;charset=UTF-8',
            data: JSON.stringify({
                 uuid: window.server_uuid,
            }),
            success: function(value){
                var status = value['status'];
                if(status==='success'){
                    // 显示modal
                    var configs = value['configs']; // 一个一级json
                    if(window.save_config_name in configs){
                        if(!configs[window.save_config_name]){
                            bootbox.alert("This page is out-of-date, please refresh.")
                        }else{
                            var dialogue = $("#change_config_dialogue");
                            dialogue.empty();
                            $('#config_box').modal('show');
                            append_single_choices(configs, dialogue, 'config_name_checkbox', 'config')
                        }
                    }else{
                        bootbox.alert("The current config name:" + window.save_config_name  +" cannot be found in server," +
                            "you may need to save it first.")
                    }
                } else{
                    bootbox.alert(value['msg']);
                }
            },
            error: function(error){
                bootbox.alert("Some error happens. You may disconnect from the server.");
            }
    })
}

function append_single_choices(configs, ele, input_id, input_name){
    // 给定一个configs的json文件，被选中为1. 将生成的html append到ele. ele通过$('#id')获取
    var html = '';
    for(var config_name in configs){
        html += generate_radio_item(config_name, configs[config_name], input_id, input_name);
    }
    ele.append(html);
}

function generate_radio_item(config_name, checked, input_id, input_name) {
    // 给定config_name是否checked，返回对应的html
    if(checked)
        checked = 'checked';
    else
        checked = '';

    var html = "              <div class=\"page__toggle\" style=\"padding: 0 0;margin: 0 0\">\n" +
        "                      <label class=\"toggle\" style=\"margin-bottom: 0\">\n" +
        "                        <input class=\"toggle__input\" type=\"radio\" id='" + input_id + "' " +
        " name='" + input_name +"' value='" + config_name + "'"  + checked + " style='position:static;margin:0;display:none'>\n" +
        "                        <span class=\"toggle__label\" style='padding: 0 0 0 24px'>\n" +
        "                          <span class=\"toggle__text\">" + config_name + "</span>\n" +
        "                        </span>\n" +
        "                      </label>\n" +
        "                    </div>";
    return html
}


/*
// 计算多个row的min, max, mean, std
* */


function getFirstJsonValue(obj) {
    for (var k in obj) return obj[k];
}

function getJsonKeys(obj){
    var keys = [];
    for(var key in obj) keys.push(key)
    return keys
}

function generate_metric_stats_table(formatted_metrics) {
    // {metric_name: {min:, max:, std:, }}
    // 返回table的str
    var html = '<table class="table table-striped">';
    var keys = getJsonKeys(getFirstJsonValue(formatted_metrics));
    // 第一行
    html += '<thead><tr>';
    html += '<th>Metric name</th>';
    for(var index=0;index<keys.length;index++){
        html += '<th>' + keys[index] + '</th>';
    }
    html += '</thead></tr><tbody>';
    // 后面的内容
    for(var key in formatted_metrics){
        var value = formatted_metrics[key];
        html += '<tr><td>' + key + '</td>';
        for(var index=0;index<keys.length;index++){
            html += '<td>' + value[keys[index]] + '</td>';
        }
        html += '</tr>';
    }
    html += '</tbody></table>';
    return html
}

var sum = function(x,y){ return x+y;};　　//求和函数
var square = function(x){ return x*x;};　　//数组中每个元素求它的平方

function getMaxMin(arr,maximin)
{
    if(maximin==="max")
    {
        return Math.max.apply(Math,arr);
    }
    else if(maximin==="min")
    {
        return Math.min.apply(Math, arr);
    }
}

function calculate_stats(metrics){
    // metrics: {key1:[v1, v2], key2:[v1, v2], key3:[v1, v2]}.
    // 计算这些值的max，min，std，avg。 返回是{key1: {max:v, min:v, avg:v}}
    // 如果返回为空， 说明没有合法的值
    var new_metrics = {};
    for(var key in metrics){
        var value = metrics[key];
        var f_value = [];
        for(var index=0;index<value.length;index++){
            var float_value = parseFloat(value[index]);
            if(!(float_value===float_value)){
                f_value = []; //说明有无法转为float的
                break;
            }else{
                f_value.push(float_value);
            }
        }
        if(f_value.length>0)
            new_metrics[key] = f_value;
    }
    var results = {};
    for(var key in new_metrics){
        var result = {};
        var data = new_metrics[key];
        result['max'] = getMaxMin(data, 'max').toFixed(6);
        result['min'] = getMaxMin(data, 'min').toFixed(6);
        var mean = data.reduce(sum)/data.length;
        result['avg'] = mean.toFixed(6);
        var deviations = data.map(function(x){return x-mean;});
        //需要考虑报道处以N还是除以N-1的版本 https://blog.csdn.net/xidiancoder/article/details/71341345
        result['std(/N-1)'] = Math.sqrt(deviations.map(square).reduce(sum)/(data.length-1)).toFixed(6);
        result['std(/N)'] = Math.sqrt(deviations.map(square).reduce(sum)/(data.length)).toFixed(6);
        results[key] = result;
    }
    return results
}
