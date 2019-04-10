from flask import Flask, render_template


from flask import request, jsonify, redirect, url_for
import uuid
import os
from flask import Blueprint

chart_page = Blueprint("chart_page", __name__, template_folder='templates')

@chart_page.route('/chart')
def chart():
    return render_template('chart.html')