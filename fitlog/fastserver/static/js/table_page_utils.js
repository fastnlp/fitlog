
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
    column_dict: json对象，key是path，value是column的item
    hidden_columns: json对象, 如果某个path在里面，则直接该内容是隐藏的
    ele: 将内容append到哪里
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
        " name='" + path + "' " + checked + " style='position: static;margin: 0; height: 0' >\n" +
        "                        <span class=\"toggle__label\" style='padding: 0 0 0 8px'>\n" +
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

