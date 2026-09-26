#!/usr/bin/env python3
"""Fail fast on deployable graph/exercise contracts; report age-content risks."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
GRAPH_PATH = ROOT / "web" / "data" / "graph_lite.json"
EXERCISES_PATH = ROOT / "web" / "data" / "exercises.json"
QUALITY_FLAGS_PATH = ROOT / "web" / "data" / "quality_flags.json"
RELATION_REVIEWS_PATH = ROOT / "web" / "data" / "relation_reviews.json"
VALID_RELATIONS = {"prerequisite", "progresses_to", "relates_to"}
VALID_TYPES = {"multiple_choice", "fill_blank", "short_answer"}
JUNIOR_OR_HIGH_SCHOOL = re.compile(r"七年级|八年级|九年级|高中")


def load(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def prerequisite_cycles(edges: list[dict]) -> list[list[str]]:
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge.get("rel") == "prerequisite":
            adjacency[edge["from"]].append(edge["to"])

    completed: set[str] = set()
    active: set[str] = set()
    found: list[list[str]] = []

    def visit(node: str, trail: list[str]) -> None:
        if node in active:
            found.append(trail[trail.index(node) :])
            return
        if node in completed:
            return
        active.add(node)
        for child in adjacency[node]:
            visit(child, trail + [child])
        active.remove(node)
        completed.add(node)

    for node in list(adjacency):
        visit(node, [node])
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strict-grade", action="store_true", help="make age-content warnings fail the check"
    )
    args = parser.parse_args()

    graph = load(GRAPH_PATH)
    exercise_data = load(EXERCISES_PATH)
    quality_flags = load(QUALITY_FLAGS_PATH)
    relation_reviews = load(RELATION_REVIEWS_PATH)
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    exercises = exercise_data.get("exercises", [])
    node_ids = {node.get("id") for node in nodes}
    errors: list[str] = []
    warnings: list[str] = []

    for edge in edges:
        edge_id = edge.get("id", "<no id>")
        if edge.get("from") not in node_ids or edge.get("to") not in node_ids:
            errors.append(f"{edge_id}: endpoint does not exist")
        if edge.get("from") == edge.get("to"):
            errors.append(f"{edge_id}: self-loop")
        if edge.get("rel") not in VALID_RELATIONS:
            errors.append(f"{edge_id}: invalid relation {edge.get('rel')!r}")

    for cycle in prerequisite_cycles(edges):
        errors.append("prerequisite cycle: " + " -> ".join(cycle))

    edges_by_id = {edge.get("id"): edge for edge in edges}
    reviews = relation_reviews.get("reviews", [])
    if not isinstance(reviews, list):
        errors.append("relation_reviews: reviews must be a list")
    for review in reviews if isinstance(reviews, list) else []:
        edge_id = review.get("edge_id")
        edge = edges_by_id.get(edge_id)
        if not edge or edge.get("rel") != "prerequisite":
            errors.append(f"relation_reviews: {edge_id!r} is not a prerequisite edge")
        for field in (
            "evidence_source",
            "evidence_locator",
            "reviewer_role",
            "reviewed_at",
            "rationale",
        ):
            if not str(review.get(field, "")).strip():
                errors.append(f"relation_reviews: {edge_id!r} missing {field}")

    blocked_ids = quality_flags.get("blocked_concept_ids", [])
    if not isinstance(blocked_ids, list):
        errors.append("quality_flags: blocked_concept_ids must be a list")
    else:
        for concept_id in blocked_ids:
            if concept_id not in node_ids:
                errors.append(f"quality_flags: unknown concept_id {concept_id}")

    for exercise in exercises:
        exercise_id = exercise.get("id", "<no id>")
        exercise_type = exercise.get("type")
        if exercise.get("concept_id") not in node_ids:
            errors.append(f"{exercise_id}: unknown concept_id")
        if exercise_type not in VALID_TYPES:
            errors.append(f"{exercise_id}: invalid type {exercise_type!r}")
            continue
        if not str(exercise.get("question", "")).strip():
            errors.append(f"{exercise_id}: missing question")
        if exercise.get("answer") in (None, "", []):
            errors.append(f"{exercise_id}: missing answer")
        if exercise_type == "multiple_choice":
            options = exercise.get("options")
            answer = str(exercise.get("answer", "")).strip().upper()
            if not isinstance(options, list) or len(options) != 4:
                errors.append(f"{exercise_id}: single-choice needs exactly 4 options")
            if answer not in {"A", "B", "C", "D"}:
                errors.append(f"{exercise_id}: single-choice answer must be A-D")
            if "多选" in str(exercise.get("question", "")):
                errors.append(f"{exercise_id}: multi-select wording requires a separate UI/type")
        if exercise_type == "fill_blank" and exercise.get("options"):
            errors.append(f"{exercise_id}: fill_blank must not carry choice options")

    for node in nodes:
        grade_end = node.get("grade_end")
        text = " ".join(
            str(node.get(field, ""))
            for field in ("title", "description", "real_examples", "teaching_activity")
        )
        if isinstance(grade_end, int) and grade_end <= 6 and JUNIOR_OR_HIGH_SCHOOL.search(text):
            warnings.append(
                f"{node.get('id')}: grade_end={grade_end}, but content mentions junior/high school"
            )

    print(f"checked {len(nodes)} nodes, {len(edges)} edges, {len(exercises)} exercises")
    for message in errors:
        print(f"ERROR: {message}")
    for message in warnings:
        print(f"WARN: {message}")
    if warnings:
        print(f"age-content warnings: {len(warnings)}; review before student-facing recommendation")
    if errors or (args.strict_grade and warnings):
        return 1
    print("learning-quality contract check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
