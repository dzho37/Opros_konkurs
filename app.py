# app.py

from flask import Flask, render_template, request, make_response
from flask_migrate import Migrate
from models import db, Nomination, Candidate
from config import Config 
import uuid
from nominations import nominations, translate_nomination


app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
migrate = Migrate(app, db)


@app.route("/")
def index():
    candidates = Candidate.query.all()
    return render_template("konkurs.html", candidates=candidates, nominations=nominations)


@app.route("/submit/<category>", methods=["POST"])
def submit_htmx(category):
    selected = request.form.get("personal")
    if not selected or selected == "disabled":
        return "<div style='color:red;'>Вы не выбрали работника</div>", 400
    
    cookie_key = f"voted_{category.lower()}"
    nomination = translate_nomination(category)

    # Получаем или создаём уникальный ID для пользователя
    voter_id = request.cookies.get(cookie_key)
    if not voter_id:
        voter_id = str(uuid.uuid4())

    # Ищем, голосовал ли пользователь за эту категорию
    existing_vote = Nomination.query.filter_by(category=nomination, cookie_id=voter_id).first()

    if existing_vote:
        existing_vote.employee = selected  # Обновляем выбор
        db.session.commit()
        message = f"<div style='color:green;'>Ваш голос обновлён: <strong>{selected} в номинации {nomination}</strong></div>"
    else:
        new_vote = Nomination(category=nomination, employee=selected, cookie_id=voter_id)
        db.session.add(new_vote)
        db.session.commit()
        message = f"<div style='color:green;'>Спасибо! Вы выбрали: <strong>{selected}</strong> в номинации {nomination}</div>"
    
    # Устанавливаем cookie, если новой не было
    response = make_response(message)
    response.set_cookie(cookie_key, voter_id, max_age=60*60*24*30)  # 30 дней

    return response


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)