# app.py

from flask import Flask, render_template, request, make_response
from flask_migrate import Migrate
from models import db, Nomination, Candidate
from config import Config 
from nominations import nominations, translate_nomination
from sqlalchemy import func


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
    textarea_info = request.form.get("textarea_info")
    print(textarea_info)
    if not selected or selected == "disabled":
        return "<div style='color:red;'>Вы не выбрали работника</div>", 400
    
    cookie_key = f"voted_{category.lower()}"
    nomination = translate_nomination(category)

    voter_id = request.headers.get("HX-Voter-ID")
    if not voter_id:
        return "Ошибка: отсутствует идентификатор голосующего", 400

    # Ищем, голосовал ли пользователь за эту категорию
    existing_vote = Nomination.query.filter_by(category=nomination, cookie_id=voter_id).first()

    if existing_vote:
        existing_vote.employee = selected  # Обновляем выбор
        existing_vote.description = textarea_info
        db.session.commit()
        message = f"<div style='color:green;'>Ваш голос обновлён: <strong>{selected} в номинации {nomination}</strong></div>"
    else:
        new_vote = Nomination(category=nomination, employee=selected, description=textarea_info, cookie_id=voter_id)
        db.session.add(new_vote)
        db.session.commit()
        message = f"<div style='color:green;'>Спасибо! Вы выбрали: <strong>{selected}</strong> в номинации {nomination}</div>"
    
    # Устанавливаем cookie, если новой не было
    response = make_response(message)
    response.set_cookie(cookie_key, voter_id, max_age=60*60*24*30)  # 30 дней

    return response

@app.route("/report")
def report():
    results = (
        db.session.query(Nomination.category, Nomination.employee, func.count().label("votes"))
        .group_by(Nomination.category, Nomination.employee)
        .order_by(Nomination.category, func.count().desc())
        .all()
    )
    
    # Преобразуем в словарь: {категория: [(имя, кол-во голосов), ...]}
    report_data = {}
    for category, employee, votes in results:
        report_data.setdefault(category, []).append((employee, votes))

     # 📌 Добавляем счётчик уникальных голосов
    total_voters = db.session.query(func.count(func.distinct(Nomination.cookie_id))).scalar()

    return render_template("report.html", report=report_data, total_voters=total_voters)


@app.route("/report.csv")
def download_csv():
    import csv
    from io import StringIO
    from sqlalchemy import func

    # results = (
    #     db.session.query(Nomination.category, Nomination.employee, Nomination.description, func.count().label("votes"))
    #     .group_by(Nomination.category, Nomination.employee)
    #     .order_by(Nomination.category, func.count().desc())
    #     .all()
    # )

    results = (
        db.session.query(Nomination.category, Nomination.employee, Nomination.description).all()
    )

    # Используем StringIO и добавляем BOM для Excel
    si = StringIO()
    si.write('\ufeff')  # UTF-8 BOM

    # writer = csv.writer(si)
    # writer.writerow(["Номинация", "Сотрудник", "Голосов", "Описание"])
    # for category, employee, votes, description in results:
    #     writer.writerow([category, employee, votes, description])

    writer = csv.writer(si)
    writer.writerow(["Номинация", "Сотрудник", "Голосов", "Описание"])
    for category, employee, description in results:
        writer.writerow([category, employee, description])

    output = si.getvalue()
    response = make_response(output)
    response.headers["Content-Disposition"] = "attachment; filename=report.csv"
    response.headers["Content-type"] = "text/csv; charset=utf-8"
    return response

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
