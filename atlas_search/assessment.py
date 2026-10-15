"""Original question bank and deterministic diagnostic feedback."""
import json
from pathlib import Path


def questions(level=None):
    bank = json.loads((Path(__file__).parent / "data" / "questions.json").read_text(encoding="utf-8"))
    return [q for q in bank if level is None or q["level"] == level]


def normalize(value):
    return str(value).strip().casefold().replace("，", ",").replace(" ", "")


def assess(answers, level=None):
    bank = questions(level)
    known = {q["id"] for q in questions()}
    unknown = sorted(set(answers) - known)
    if unknown:
        raise ValueError("unknown question ids: " + ", ".join(unknown))
    details, correct = [], 0
    for q in bank:
        supplied = answers.get(q["id"])
        ok = supplied is not None and normalize(supplied) in [normalize(a) for a in q["answers"]]
        correct += ok
        details.append({"id": q["id"], "correct": ok, "submitted": supplied, "answer": q["answers"][0],
                        "explanation": q["explanation"], "review": q["review"], "topic": q["topic"]})
    score = round(100 * correct / len(bank), 1) if bank else 0
    band = "基础重建" if score < 60 else "专项补弱" if score < 80 else "综合迁移" if score < 95 else "高分巩固"
    review = sorted({d["review"] for d in details if not d["correct"]})
    return {"score": score, "correct": correct, "total": len(bank), "band": band, "review": review, "details": details,
            "notice": "原创练习诊断，不是408正式成绩预测；满分目标仍需大纲核对、限时训练和人工审阅。"}
