from flask import Blueprint, render_template

auth_bp = Blueprint('auth_web', __name__)

@auth_bp.route('/login')
def login():
    """登录页面"""
    return render_template('login.html')

@auth_bp.route('/register')
def register():
    """注册页面"""
    return render_template('register.html')
