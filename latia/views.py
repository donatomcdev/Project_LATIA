from bisect import bisect_left
from datetime import UTC, date, datetime, time, timedelta
from statistics import mean
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import click
from flask import Blueprint, Response, abort, flash, g, redirect, render_template, request, send_file, session, url_for
from flask.cli import with_appcontext
from psycopg.errors import UniqueViolation
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from . import database
from .models import Account, Reading
from .profile_photo import normalize_photo
from .reports import readings_pdf

journal = Blueprint("journal", __name__)
METRICS = (("systolic", "Sistólica", "mmHg"), ("diastolic", "Diastólica", "mmHg"), ("pulse", "Pulso", "lpm"))
PERIODS = {"all": "Todo", "month": "Último mes", "week": "Última semana", "custom": "Rango personalizado"}
DEFAULT_RANGES = {"systolic": [90, 110, 135, 150], "diastolic": [40, 60, 85, 100]}
RANGE_LEVELS = ("Muy bajo", "Bajo", "Normal", "Alto", "Muy alto")
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 16
PASSWORD_LENGTH_ERROR = f"La contraseña debe tener entre {PASSWORD_MIN_LENGTH} y {PASSWORD_MAX_LENGTH} caracteres."
DUMMY_HASH = generate_password_hash("latia-login-placeholder")


def valid_zone(value):
    if len(value) > 64:
        raise ValueError("Introduce una zona horaria válida, como America/La_Paz.")
    try:
        return ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError("Introduce una zona horaria válida, como America/La_Paz.") from None


@click.command("crear-usuario")
@click.argument("username")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
@with_appcontext
def create_user(username, password):
    username = username.strip().lower()
    if not 1 <= len(username) <= 64 or "\x00" in username:
        raise click.ClickException("Indica un usuario válido de hasta 64 caracteres.")
    if not PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH:
        raise click.ClickException(PASSWORD_LENGTH_ERROR)
    db = database()
    db.add(Account(username=username, password_hash=generate_password_hash(password), timezone="America/La_Paz"))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise click.ClickException("El usuario ya existe.") from None
    click.echo("Usuario creado.")


@journal.before_request
def load_account():
    g.account = None
    if "account_id" in session:
        account = database().get(Account, session["account_id"])
        if account is not None and account.session_version == session.get("session_version", 0):
            g.account = account
        else:
            session.clear()
    if request.endpoint != "journal.login" and g.account is None:
        return redirect(url_for("journal.login"))


@journal.route("/acceso", methods=["GET", "POST"])
def login():
    if g.account is not None:
        return redirect(url_for("journal.records"))
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        if not 1 <= len(username) <= 64 or "\x00" in username:
            return render_template("login.html", error="Usuario o contraseña incorrectos."), 401
        account = database().scalar(select(Account).where(Account.username == username))
        if check_password_hash(account.password_hash if account else DUMMY_HASH, password) and account:
            session.clear()
            session["account_id"] = account.id
            session["session_version"] = account.session_version
            session.permanent = True
            return redirect(url_for("journal.records"), code=303)
        return render_template("login.html", error="Usuario o contraseña incorrectos."), 401
    return render_template("login.html")


@journal.post("/salir")
def logout():
    session.clear()
    return redirect(url_for("journal.login"), code=303)


def owned_readings():
    return select(Reading).where(Reading.account_id == g.account.id)


def filtered_readings(zone):
    period = request.args.get("period", "all")
    start = request.args.get("start", "")
    end = request.args.get("end", "")
    error = None
    query = owned_readings()
    today = datetime.now(zone).date()
    try:
        if period in ("week", "month"):
            days = 7 if period == "week" else 30
            first, last = today - timedelta(days=days - 1), today
        elif period == "custom":
            first, last = date.fromisoformat(start), date.fromisoformat(end)
        elif period == "all":
            first = last = None
        else:
            raise ValueError
        if first is not None:
            if first > last:
                raise ValueError
            query = query.where(
                Reading.measured_at >= datetime.combine(first, time.min, zone),
                Reading.measured_at < datetime.combine(last + timedelta(days=1), time.min, zone),
            )
    except (ValueError, OverflowError):
        return [], period, start, end, "Selecciona un rango válido. La fecha inicial debe ser anterior o igual a la final."
    rows = database().scalars(query.order_by(Reading.measured_at.desc(), Reading.id.desc())).all()
    return rows, period, start, end, error


def reading_level(row, ranges):
    systolic = bisect_left(ranges["systolic"], row.systolic)
    diastolic = bisect_left(ranges["diastolic"], row.diastolic)
    highest = max(systolic, diastolic)
    return highest if highest > 2 else min(systolic, diastolic)


@journal.get("/")
@journal.get("/tendencias", endpoint="trends")
@journal.get("/estadisticas", endpoint="stats")
def records():
    view = request.endpoint.rsplit(".", 1)[-1]
    zone = valid_zone(g.account.timezone)
    rows, period, start, end, error = filtered_readings(zone)
    groups = {}
    if view == "records":
        ranges = g.account.pressure_ranges or DEFAULT_RANGES
        for row in rows:
            local = row.measured_at.astimezone(zone)
            groups.setdefault(local.date(), []).append((row, local, reading_level(row, ranges)))
    chart = []
    stats = []
    if rows and view == "trends":
        chart = [
            {"label": row.measured_at.astimezone(zone).strftime("%d/%m/%Y %H:%M %Z"),
             "timestamp": row.measured_at.timestamp() * 1000,
             **{key: getattr(row, key) for key, _, _ in METRICS}}
            for row in reversed(rows)
        ]
    if rows and view == "stats":
        for key, label, unit in METRICS:
            values = [getattr(row, key) for row in rows]
            stats.append((label, unit, f"{mean(values):.1f}".replace(".", ","), min(values), max(values)))
    return render_template(
        "journal.html", view=view, rows=rows,
        groups=groups, levels=RANGE_LEVELS, periods=PERIODS, period=period, start=start, end=end,
        filter_error=error, chart=chart, stats=stats,
    ), 400 if error else 200


@journal.get("/registros/exportar.pdf")
def export_pdf():
    zone = valid_zone(g.account.timezone)
    rows, period, start, end, error = filtered_readings(zone)
    if error:
        return render_template("error.html", message=error), 400

    label = PERIODS[period]
    if period == "custom":
        first, last = (date.fromisoformat(value).strftime("%d/%m/%Y") for value in (start, end))
        label = f"{first} al {last}"
    report = readings_pdf(rows, zone, label)
    return send_file(report, mimetype="application/pdf", as_attachment=True, download_name="LATIA-lecturas.pdf")


def find_reading(reading_id):
    row = database().scalar(owned_readings().where(Reading.id == reading_id))
    if row is None:
        abort(404)
    return row


def measurement_time(value, zone, original):
    local = datetime.strptime(value, "%Y-%m-%dT%H:%M")
    if original and original.astimezone(zone).strftime("%Y-%m-%dT%H:%M") == value:
        return original
    candidate = local.replace(tzinfo=zone)
    if candidate.astimezone(UTC).astimezone(zone).replace(tzinfo=None) != local:
        raise ValueError("La hora indicada no existe en tu zona horaria.")
    if candidate.utcoffset() != local.replace(tzinfo=zone, fold=1).utcoffset():
        raise ValueError("La hora indicada se repite por el cambio horario. Elige una hora sin ambigüedad.")
    return candidate


def reading_values(form, zone, original):
    try:
        measured_at = measurement_time(form.get("measured_at", ""), zone, original)
    except (ValueError, OverflowError) as error:
        message = str(error) if str(error).startswith("La hora") else "Indica una fecha y hora válidas."
        raise ValueError(message) from None
    try:
        systolic, diastolic, pulse = (int(form.get(key, "")) for key, _, _ in METRICS)
    except ValueError:
        raise ValueError("Introduce números enteros para la presión y el pulso.") from None
    if not all(1 <= value <= 999 for value in (systolic, diastolic, pulse)):
        raise ValueError("Cada valor debe estar entre 1 y 999.")
    if systolic <= diastolic:
        raise ValueError("La sistólica debe ser mayor que la diastólica.")
    note = form.get("note", "").strip()
    if len(note) > 500 or "\x00" in note:
        raise ValueError("Introduce un comentario válido de hasta 500 caracteres.")
    return dict(measured_at=measured_at, systolic=systolic, diastolic=diastolic, pulse=pulse, note=note)


@journal.route("/registros/nuevo", methods=["GET", "POST"])
@journal.route("/registros/<int:reading_id>/editar", methods=["GET", "POST"])
def editor(reading_id=None):
    row = find_reading(reading_id) if reading_id is not None else None
    zone = valid_zone(g.account.timezone)
    error = None
    if request.method == "POST":
        values = request.form
        try:
            fields = reading_values(values, zone, row.measured_at if row else None)
        except ValueError as invalid:
            error = str(invalid)
        else:
            db = database()
            if row is None:
                db.add(Reading(account_id=g.account.id, **fields))
            else:
                for key, value in fields.items():
                    setattr(row, key, value)
            db.commit()
            flash("Lectura guardada.")
            return redirect(url_for("journal.records"), code=303)
    else:
        measured_at = row.measured_at.astimezone(zone) if row else datetime.now(zone)
        values = {key: getattr(row, key) if row else "" for key, _, _ in METRICS}
        values.update(measured_at=measured_at.strftime("%Y-%m-%dT%H:%M"), note=row.note if row else "")
    return render_template("editor.html", row=row, values=values, metrics=METRICS, error=error), 422 if error else 200


@journal.post("/registros/<int:reading_id>/eliminar")
def delete(reading_id):
    row = find_reading(reading_id)
    db = database()
    db.delete(row)
    db.commit()
    flash("Lectura eliminada.")
    return redirect(url_for("journal.records"), code=303)


@journal.route("/perfil", methods=["GET", "POST"])
def profile():
    error = None
    timezone = g.account.timezone
    if request.method == "POST":
        timezone = request.form.get("timezone", "").strip()
        try:
            zone = valid_zone(timezone)
        except ValueError as invalid:
            error = str(invalid)
        else:
            g.account.timezone = zone.key
            database().commit()
            flash("Preferencias guardadas.")
            return redirect(url_for("journal.profile"), code=303)
    return render_template("profile.html", timezone=timezone, error=error), 422 if error else 200


@journal.post("/perfil/usuario")
def change_username():
    account = g.account
    username = request.form.get("new_username", "").strip().lower()
    error = None
    status = 422
    if not 1 <= len(username) <= 64 or "\x00" in username:
        error = "Introduce un nombre de usuario válido de hasta 64 caracteres."
    elif username == account.username:
        error = "Elige un nombre de usuario diferente del actual."
    else:
        db = database()
        try:
            changed = db.scalar(
                update(Account)
                .where(
                    Account.id == account.id,
                    Account.username == account.username,
                    Account.session_version == account.session_version,
                )
                .values(username=username)
                .returning(Account.id)
            )
            if changed is not None:
                db.commit()
                flash("Nombre de usuario actualizado.", "username-updated")
                return redirect(url_for("journal.profile", _anchor="usuario"), code=303)
            db.rollback()
            error = "La cuenta se actualizó en otra sesión. Vuelve a abrir Perfil e inténtalo de nuevo."
            status = 409
        except IntegrityError as conflict:
            db.rollback()
            if not isinstance(conflict.orig, UniqueViolation):
                raise
            error = "Ese nombre de usuario ya está en uso."
            status = 409
    return render_template(
        "profile.html", timezone=account.timezone, username_error=error, new_username=username,
    ), status


@journal.route("/ajustes/rangos", methods=["GET", "POST"])
def edit_ranges():
    values = g.account.pressure_ranges or DEFAULT_RANGES
    error = None
    if request.method == "POST":
        values = {
            key: [request.form.get(f"{key}_{index}", "") for index in range(len(limits))]
            for key, limits in DEFAULT_RANGES.items()
        }
        try:
            ranges = {key: list(map(int, limits)) for key, limits in values.items()}
            for limits in ranges.values():
                if not 1 <= limits[0] < limits[1] < limits[2] < limits[3] <= 999:
                    raise ValueError
        except ValueError:
            error = "Introduce cuatro límites enteros del 1 al 999 en orden ascendente para cada medición."
        else:
            g.account.pressure_ranges = ranges
            database().commit()
            flash("Rangos guardados.")
            return redirect(url_for("journal.edit_ranges"), code=303)
    return render_template(
        "ranges.html", values=values, levels=RANGE_LEVELS[:-1], metrics=METRICS[:2], error=error,
    ), 422 if error else 200


@journal.post("/perfil/contrasena")
def change_password():
    current = request.form.get("current_password", "")
    new = request.form.get("new_password", "")
    confirmation = request.form.get("confirm_password", "")
    account = g.account
    error = None
    if not PASSWORD_MIN_LENGTH <= len(new) <= PASSWORD_MAX_LENGTH:
        error = PASSWORD_LENGTH_ERROR
    elif new != confirmation:
        error = "La nueva contraseña y su confirmación deben coincidir."
    elif new == current:
        error = "Elige una contraseña diferente de la actual."
    elif not check_password_hash(account.password_hash, current):
        error = "La contraseña actual es incorrecta."
    if error:
        return render_template("profile.html", timezone=account.timezone, password_error=error), 422

    db = database()
    next_version = account.session_version + 1
    changed = db.scalar(
        update(Account)
        .where(Account.id == account.id, Account.session_version == account.session_version)
        .values(password_hash=generate_password_hash(new), session_version=next_version)
        .returning(Account.id)
    )
    if changed is None:
        db.rollback()
        session.clear()
        flash("La contraseña ya cambió. Inicia sesión de nuevo.")
        return redirect(url_for("journal.login"), code=303)
    db.commit()
    session["session_version"] = next_version
    flash("Contraseña actualizada. Las demás sesiones se cerraron.", "password-updated")
    return redirect(url_for("journal.profile", _anchor="contrasena"), code=303)


@journal.get("/perfil/foto")
def profile_photo():
    photo = g.account.profile_photo
    if photo is None:
        abort(404)
    return Response(photo, mimetype="image/jpeg")


@journal.post("/perfil/foto")
def upload_photo():
    upload = request.files.get("photo")
    try:
        if not upload:
            raise ValueError("Selecciona una foto para guardar.")
        photo = normalize_photo(upload)
    except ValueError as error:
        return render_template("profile.html", timezone=g.account.timezone, photo_error=str(error)), 422
    g.account.profile_photo = photo
    database().commit()
    flash("Foto de perfil guardada.")
    return redirect(url_for("journal.profile", _anchor="foto"), code=303)
