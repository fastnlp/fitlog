
r"""
主要用于显示log folder下的文件


"""
import os
import time
import base64
import struct
from flask import render_template, redirect, url_for

from flask import request, jsonify
from flask import Blueprint
from .server.data_container import all_data
from .server.table_utils import generate_columns
from .server.table_utils import expand_dict
from collections import defaultdict
from .server.utils import check_uuid
from flask import make_response, send_file
from .server.folder_utils import get_image_size



folder_page = Blueprint('folder_page', __name__, template_folder='templates')


@folder_page.route('/folder', methods=['POST', 'GET'])
def show_folder():
    if request.method == 'POST':
        uuid = request.values['uuid']
        id = request.values['id'] if 'id' in request.values else ''
        subdir = request.values['subdir'] if 'subdir' in request.values else ''
    else:
        uuid = request.args.get('uuid')
        id = request.args.get('id')
        subdir = request.args.get('subdir')
    res = check_uuid(all_data['uuid'], uuid)
    if res is not None:
        return jsonify(res)
    if id:
        log_dir = all_data['root_log_dir']
        folder = os.path.join(log_dir, id)
        if os.path.relpath(folder, log_dir).startswith('.'):
            return jsonify(status='fail', msg='Permission denied.')

        if subdir == '':  # 如果为空，说明还是需要访问folder
            pass
        elif os.path.isfile(os.path.join(folder, subdir)):  # 文件直接发送
            if os.path.splitext(subdir)[1][1:] in ('jpg', 'png', 'jpeg', 'fig'):
                return redirect(url_for('folder_page.show_image', uuid=uuid, id=id, subdir=subdir), code=301)
            resp = make_response(send_file(os.path.join(folder, subdir)))
            resp.headers["Content-type"]="text/plan;charset=UTF-8"
            return resp
        elif os.path.isdir(os.path.join(folder, subdir)):  # 如果是directory
            folder = os.path.join(folder, subdir)
        else:
            return jsonify(status='fail', msg="Invalid file.")

        if os.path.relpath(folder, log_dir).startswith('.'):
            return jsonify(status='fail', msg='Permission denied.')
        
        current_list = os.listdir(folder)
        contents = []
        for i in sorted(current_list):
            fullpath = folder + os.sep + i
            # 如果是目录，在后面添加一个sep
            if os.path.isdir(fullpath):
                extra = os.sep
            else:
                extra = ''
            content = {}
            content['filename'] = i + extra
            content['mtime'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.stat(fullpath).st_mtime))
            content['size'] = str(round(os.path.getsize(fullpath) / 1024)) + 'k'
            content['isfile'] = os.path.isfile(fullpath)
            if extra:
                contents.insert(0, content)
            else:
                contents.append(content)
        subdir = os.path.relpath(os.path.abspath(folder), start=os.path.abspath(os.path.join(log_dir, id)))
        if subdir.startswith('.'):
            subdir = ''
        else:
            if not subdir.endswith(os.sep):
                subdir += os.sep
        return render_template('folder.html', contents=contents, subdir=subdir, ossep=os.sep,
                               uuid=all_data['uuid'], id=id)
    else:
        return jsonify(status='fail', msg="The request lacks id or filename.")


@folder_page.route('/folder/show_image', methods=['GET'])
def show_image():
    uuid = request.args.get('uuid')
    id = request.args.get('id')
    subdir = request.args.get('subdir')
    res = check_uuid(all_data['uuid'], uuid)
    if res is not None:
        return jsonify(res)
    if id:
        log_dir = all_data['root_log_dir']
        folder = os.path.join(log_dir, id)
        if os.path.splitext(subdir)[1][1:] in ('jpg', 'png', 'jpeg', 'fig'):
            img_stream = ''
            with open(os.path.join(folder, subdir), 'rb') as img_f:
                img_stream = img_f.read()
                img_stream = base64.b64encode(img_stream).decode('ascii')
            try:
                width = get_image_size(os.path.join(folder, subdir))[0]
            except:
                width = -1
            if width == -1:
                width = 1000
            return render_template('folder_img.html', img_stream=img_stream, img_path=subdir, width=width)
    return jsonify(status='fail', msg=f"Fail to show {os.path.relpath(os.path.join(folder, subdir)), log_dir}")
