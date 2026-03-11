from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

@app.route('/test', methods=['GET'])
def test():
    return jsonify({"status": "OK", "message": "API STPA fonctionne"})

@app.route('/analyse', methods=['POST'])
def analyse():
    data = request.get_json()
    valeurs = data.get('valeurs', [])
    if not valeurs:
        return jsonify({"erreur": "Aucune donnee"}), 400
    return jsonify({
        "total": round(sum(valeurs), 2),
        "moyenne": round(sum(valeurs)/len(valeurs), 2),
        "maximum": max(valeurs),
        "minimum": min(valeurs),
        "count": len(valeurs)
    })

@app.route('/recommandations', methods=['POST'])
def recommandations():
    data = request.get_json()
    conformite = data.get('conformite', 0)
    alertes = data.get('alertes', 0)
    liste = []
    if conformite < 90:
        liste.append("Conformite CQ en dessous de 90%")
    if alertes > 5:
        liste.append("Nombre d alertes eleve")
    if conformite >= 95:
        liste.append("Excellente conformite")
    if not liste:
        liste.append("Tous les indicateurs sont dans les normes")
    return jsonify({
        "recommandations": liste,
        "priorite": "haute" if alertes > 5 else "normale"
    })

