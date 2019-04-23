


function generate_range_modal(current_step, charts, ele, range_checked, ranges) {
    // 根据charts中的内容生成几个range
    var sliders = {};

    if(!jQuery.isEmptyObject(charts)){
        for(var key in charts){
            if(!(key in range_checked)){
                range_checked[key] = '';
            }
            var checked = range_checked[key];
            var _range = [];
            if(!(key in ranges)){
                _range = [0, current_step];
            }else{
                _range = ranges[key];
            }
            var name = key;
            var id = key + '_range_bar';
            var html = '<div style="margin: 5px 0px 5px 0;">';
            html += " <div class=\"page__toggle\" style=\"padding: 0 0;margin: 0px 20px 0px 0;float:left\">\n" +
            "                      <label class=\"toggle\" style=\"margin-bottom: 0\">\n" +
            "                        <input class=\"toggle__input\" type=\"checkbox\" id='choose_range_checkbox' " +
            " name='" + name + "' " + checked + " style='position:static;margin:0;display:none'>\n" +
            "                        <span class=\"toggle__label\" style='padding: 0 0 0 24px'>\n" +
            "                          <span class=\"toggle__text\">"+ key +"</span>" +
            "                        </span>\n" +
            "                      </label>\n" +
            "                    </div>";
            html += '<input id="' + id + '" type="text" class="span2" style="float:left;margin-left:10px;width:75%"/>';
            html += '<div class="clear"></div></div>';
            ele.append(html);
            var enabled = checked !== '';
            sliders[key] = new Slider('#' + id, {max:current_step,
                                                 value:_range,
                                                 enabled:enabled,
                                                 step:50});
      }
    }
    return sliders;
}