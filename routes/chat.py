from flask import Flask,render_template,Blueprint


chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

@chat_bp.route('/',methods=['GET','POST'])
def chat():
    return render_template('chat.html')