# 这个文件主要是用于响应summary以及计算summary等


from flask import render_template

from flask import request, jsonify
from flask import Blueprint


summary_page = Blueprint('summary_page', __name__, template_folder='templates')

@summary_page.route('/summary')
def demo():
    return render_template('summary.html')