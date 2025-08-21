from flask import Blueprint, request, jsonify, render_template, Response
import os
from .features import extract_metrics
from .scoring import load_rules, score_metrics

grafologia_bp = Blueprint("grafologia", __name__, template_folder="templates")

RULES_PATH = os.environ.get("GRAFO_RULES_PATH", os.path.join(os.path.dirname(__file__), "rules.yml"))

@grafologia_bp.route("/health", methods=["GET"], strict_slashes=False)
def health():
    return jsonify({"ok": True})

@grafologia_bp.route("/analizar", methods=["POST"], strict_slashes=False)
def analizar():
    if "file" not in request.files:
        return jsonify({"error": "Falta 'file'"}), 400
    b = request.files["file"].read()
    metrics, aux = extract_metrics(b)
    rules = load_rules(RULES_PATH)
    result = score_metrics(metrics, rules, aux)
    return jsonify(result)

@grafologia_bp.route("/informe", methods=["POST"], strict_slashes=False)
def informe():
    if "file" not in request.files:
        return jsonify({"error": "Falta 'file'"}), 400
    b = request.files["file"].read()
    metrics, aux = extract_metrics(b)
    rules = load_rules(RULES_PATH)
    result = score_metrics(metrics, rules, aux)
    html = render_template("informe.html.j2", result=result, metrics=metrics, aux=aux)
    return html