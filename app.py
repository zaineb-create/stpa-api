from flask import Flask, request, jsonify, Response
import io
import base64

app = Flask(__name__)

# ── Mémoire interne de l'agent
agent_etat = {
    "derniere_analyse": None,
    "nb_analyses": 0,
    "alertes_envoyees": [],
    "statut": "en attente"
}

# ────────────────────────────────────────────
# Cerveau de l'agent — analyse un fichier Excel
# ────────────────────────────────────────────
def analyser_donnees(lignes, colonnes):
    import statistics
    resultats = []

    for ligne in lignes:
        rapport = dict(zip(colonnes, ligne))
        dept = rapport.get("Département", "N/A")
        titre = rapport.get("Titre", "N/A")

        # Récupère la valeur Conforme
        conforme_raw = str(rapport.get("Conforme", "100")).replace("%","").strip()
        try:
            conformite = float(conforme_raw)
        except:
            conformite = 100.0

        # Décision de l'agent
        if conformite < 85:
            niveau = "critique"
            message = f"Conformité critique {conformite}% — {dept} — {titre}"
        elif conformite < 90:
            niveau = "avertissement"
            message = f"Conformité faible {conformite}% — {dept} — {titre}"
        else:
            niveau = "normal"
            message = None

        if message:
            resultats.append({
                "departement": dept,
                "titre": titre,
                "conformite": conformite,
                "niveau": niveau,
                "message": message,
                "horodatage": datetime.now().strftime("%d/%m/%Y %H:%M")
            })

    return resultats

# ────────────────────────────────────────────
# Déclenche ton flux Power Automate existant
# ────────────────────────────────────────────
def declencher_flux_alertes(alertes, webhook_url):
    import urllib.request
    payload = json.dumps({
        "nb_alertes": len(alertes),
        "nb_critiques": len([a for a in alertes if a["niveau"] == "critique"]),
        "alertes": alertes,
        "statut": "critique" if any(a["niveau"] == "critique" for a in alertes) else "avertissement",
        "horodatage": datetime.now().strftime("%d/%m/%Y %H:%M")
    }).encode("utf-8")

    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200 or resp.status == 202
    except Exception as e:
        print(f"Erreur webhook : {e}")
        return False

# ────────────────────────────────────────────
# Route principale — Power Automate appelle ici
# ────────────────────────────────────────────
@app.route('/agent', methods=['POST'])
def agent():
    data = request.get_json() or {}

    colonnes = data.get("colonnes", [])
    lignes   = data.get("lignes", [])
    webhook  = data.get("webhook_url", "")
    utilisateur = data.get("utilisateur", "Système")

    if not colonnes or not lignes:
        return jsonify({"erreur": "Aucune donnée reçue"}), 400

    # Analyse des données
    alertes = analyser_donnees(lignes, colonnes)

    # Met à jour la mémoire de l'agent
    agent_etat["derniere_analyse"] = datetime.now().strftime("%d/%m/%Y %H:%M")
    agent_etat["nb_analyses"] += 1
    agent_etat["statut"] = "critique" if any(
        a["niveau"] == "critique" for a in alertes) else (
        "avertissement" if alertes else "normal")

    flux_declenche = False
    if alertes and webhook:
        flux_declenche = declencher_flux_alertes(alertes, webhook)
        agent_etat["alertes_envoyees"].extend(alertes)

    # Rapport résumé
    return jsonify({
        "statut": agent_etat["statut"],
        "nb_alertes": len(alertes),
        "nb_critiques": len([a for a in alertes if a["niveau"] == "critique"]),
        "nb_avertissements": len([a for a in alertes if a["niveau"] == "avertissement"]),
        "alertes": alertes,
        "flux_declenche": flux_declenche,
        "analyse_numero": agent_etat["nb_analyses"],
        "horodatage": agent_etat["derniere_analyse"],
        "analyse_par": utilisateur
    })

# ────────────────────────────────────────────
# Route statut — voir ce que fait l'agent
# ────────────────────────────────────────────
@app.route('/agent/statut', methods=['GET'])
def agent_statut():
    return jsonify({
        "statut": agent_etat["statut"],
        "derniere_analyse": agent_etat["derniere_analyse"],
        "nb_analyses_total": agent_etat["nb_analyses"],
        "nb_alertes_total": len(agent_etat["alertes_envoyees"]),
        "en_ligne": True
    })
