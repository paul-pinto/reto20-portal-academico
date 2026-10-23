from __future__ import annotations

import logging

from flask import (
    Blueprint,
    abort,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .auth import login_required, role_required, verify_password
from .services import dynamodb_service as db
from .services.s3_service import generate_download_url

bp = Blueprint("portal", __name__)
logger = logging.getLogger("portal.audit")


def audit(action: str, **fields) -> None:
    payload = " ".join(f"{k}={v}" for k, v in sorted(fields.items()))
    logger.info("AUDIT action=%s %s", action, payload)


@bp.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("portal.login"))
    if session.get("role") == "estudiante":
        return redirect(url_for("portal.student_dashboard"))
    if session.get("role") == "docente":
        return redirect(url_for("portal.teacher_dashboard"))
    session.clear()
    return redirect(url_for("portal.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        user_id = request.form.get("user_id", "").strip()
        password = request.form.get("password", "")

        user = db.get_user(user_id)

        if not user or not verify_password(password, user.get("password_hash", "")):
            audit("login_failed", user_id=user_id, ip=request.remote_addr)
            error = "Usuario o contraseña incorrectos."
        else:
            session.clear()
            session["user_id"] = user["user_id"]
            session["nombre"] = user["nombre"]
            session["role"] = user["role"]
            audit(
                "login_success",
                user_id=user["user_id"],
                role=user["role"],
                ip=request.remote_addr,
            )
            return redirect(url_for("portal.index"))

    return render_template("login.html", error=error)


@bp.route("/logout")
@login_required
def logout():
    audit("logout", user_id=session.get("user_id"))
    session.clear()
    return redirect(url_for("portal.login"))


@bp.route("/estudiante")
@role_required("estudiante")
def student_dashboard():
    student_id = session["user_id"]
    courses = db.list_student_courses(student_id)
    submissions = db.list_student_submissions(student_id)
    return render_template(
        "estudiante.html",
        courses=courses,
        submissions=submissions,
    )


@bp.route("/docente")
@role_required("docente")
def teacher_dashboard():
    courses = db.list_teacher_courses(session["user_id"])
    return render_template("docente.html", courses=courses)


@bp.route("/curso/<course_id>")
@login_required
def course_detail(course_id: str):
    course = db.get_course(course_id)
    if not course:
        abort(404)

    user_id = session["user_id"]
    role = session["role"]

    if role == "docente":
        if course["teacher_id"] != user_id:
            audit(
                "forbidden_course",
                user_id=user_id,
                role=role,
                course_id=course_id,
            )
            abort(403)
    elif role == "estudiante":
        allowed_course_ids = {c["course_id"] for c in db.list_student_courses(user_id)}
        if course_id not in allowed_course_ids:
            audit(
                "forbidden_course",
                user_id=user_id,
                role=role,
                course_id=course_id,
            )
            abort(403)
    else:
        abort(403)

    activities = db.list_course_activities(course_id)
    submissions_by_activity = {}

    if role == "docente":
        for activity in activities:
            submissions_by_activity[activity["activity_id"]] = (
                db.list_activity_submissions(activity["activity_id"])
            )

    return render_template(
        "curso.html",
        course=course,
        activities=activities,
        submissions_by_activity=submissions_by_activity,
    )


@bp.route("/entrega/<activity_id>/<student_id>")
@login_required
def submission_detail(activity_id: str, student_id: str):
    submission = db.get_submission(activity_id, student_id)
    if not submission:
        abort(404)

    user_id = session["user_id"]
    role = session["role"]
    course = db.get_course(submission["course_id"])

    if not course:
        abort(404)

    allowed = False

    if role == "estudiante":
        allowed = submission["student_id"] == user_id

    elif role == "docente":
        allowed = course["teacher_id"] == user_id

    if not allowed:
        audit(
            "forbidden_submission",
            user_id=user_id,
            role=role,
            activity_id=activity_id,
            requested_student=student_id,
            course_id=submission["course_id"],
        )
        abort(403)

    review = db.get_review(activity_id, student_id)

    audit(
        "view_submission",
        user_id=user_id,
        role=role,
        activity_id=activity_id,
        student_id=student_id,
        course_id=submission["course_id"],
    )

    return render_template(
        "entrega.html",
        submission=submission,
        review=review,
    )


@bp.route("/entrega/<activity_id>/<student_id>/archivo")
@login_required
def download_submission(activity_id: str, student_id: str):
    submission = db.get_submission(activity_id, student_id)
    if not submission:
        abort(404)

    user_id = session["user_id"]
    role = session["role"]
    course = db.get_course(submission["course_id"])

    if not course:
        abort(404)

    allowed = (
        role == "estudiante"
        and submission["student_id"] == user_id
    ) or (
        role == "docente"
        and course["teacher_id"] == user_id
    )

    if not allowed:
        audit(
            "forbidden_download",
            user_id=user_id,
            role=role,
            activity_id=activity_id,
            requested_student=student_id,
            course_id=submission["course_id"],
        )
        abort(403)

    url = generate_download_url(submission["s3_key"])

    audit(
        "presigned_url_generated",
        user_id=user_id,
        role=role,
        activity_id=activity_id,
        student_id=student_id,
        course_id=submission["course_id"],
    )

    return redirect(url)


@bp.app_errorhandler(403)
def forbidden(_error):
    return render_template("error_403.html"), 403


@bp.app_errorhandler(404)
def not_found(_error):
    return render_template("error_404.html"), 404
