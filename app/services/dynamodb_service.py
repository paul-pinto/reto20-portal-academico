from __future__ import annotations

from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from flask import current_app


def _table():
    dynamodb = boto3.resource(
        "dynamodb",
        region_name=current_app.config["AWS_REGION"],
    )
    return dynamodb.Table(current_app.config["DYNAMODB_TABLE"])


def get_user(user_id: str) -> dict[str, Any] | None:
    response = _table().get_item(
        Key={"PK": f"USER#{user_id}", "SK": "PROFILE"}
    )
    return response.get("Item")


def get_course(course_id: str) -> dict[str, Any] | None:
    response = _table().get_item(
        Key={"PK": f"COURSE#{course_id}", "SK": "META"}
    )
    return response.get("Item")


def get_activity(course_id: str, activity_id: str) -> dict[str, Any] | None:
    response = _table().get_item(
        Key={
            "PK": f"COURSE#{course_id}",
            "SK": f"ACTIVITY#{activity_id}",
        }
    )
    return response.get("Item")


def get_submission(activity_id: str, student_id: str) -> dict[str, Any] | None:
    response = _table().get_item(
        Key={
            "PK": f"ACTIVITY#{activity_id}",
            "SK": f"STUDENT#{student_id}",
        }
    )
    return response.get("Item")


def get_review(activity_id: str, student_id: str) -> dict[str, Any] | None:
    response = _table().get_item(
        Key={
            "PK": f"ACTIVITY#{activity_id}",
            "SK": f"REVIEW#{student_id}",
        }
    )
    return response.get("Item")


def list_student_courses(student_id: str) -> list[dict[str, Any]]:
    response = _table().query(
        IndexName="GSI1",
        KeyConditionExpression=(
            Key("GSI1PK").eq(f"STUDENT#{student_id}")
            & Key("GSI1SK").begins_with("COURSE#")
        ),
    )

    courses = []
    for enrollment in response.get("Items", []):
        course = get_course(enrollment["course_id"])
        if course:
            courses.append(course)
    return courses


def list_teacher_courses(teacher_id: str) -> list[dict[str, Any]]:
    response = _table().query(
        IndexName="GSI1",
        KeyConditionExpression=(
            Key("GSI1PK").eq(f"TEACHER#{teacher_id}")
            & Key("GSI1SK").begins_with("COURSE#")
        ),
    )
    return response.get("Items", [])


def list_course_activities(course_id: str) -> list[dict[str, Any]]:
    response = _table().query(
        KeyConditionExpression=(
            Key("PK").eq(f"COURSE#{course_id}")
            & Key("SK").begins_with("ACTIVITY#")
        )
    )
    return response.get("Items", [])


def list_activity_submissions(activity_id: str) -> list[dict[str, Any]]:
    response = _table().query(
        KeyConditionExpression=(
            Key("PK").eq(f"ACTIVITY#{activity_id}")
            & Key("SK").begins_with("STUDENT#")
        )
    )
    return response.get("Items", [])


def list_student_submissions(student_id: str) -> list[dict[str, Any]]:
    response = _table().query(
        IndexName="GSI1",
        KeyConditionExpression=(
            Key("GSI1PK").eq(f"STUDENT#{student_id}")
            & Key("GSI1SK").begins_with("SUBMISSION#")
        ),
    )
    return response.get("Items", [])
