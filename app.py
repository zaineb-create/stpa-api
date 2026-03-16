from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# ══════════════════════════════════════════
# Mémoire interne de l'agent
# ══════════════════════════════════════════
agent_etat = {
    "derniere_analyse": None,
    "nb_analyses": 0,
    "alertes_envoyees": [],
    "statut": "en attente",
    "taux_conformite": 0,
    "nb_non_conformes": 0
}

# ══════════════════════════════════════════
# /test
# ══════════════════════════════════════════
@app.route('/test', methods=['GET'])
def test():
    return jsonify({"status": "OK", "message": "API STPA — analyse_kpi active"})

# ══════════════════════════════════════════
# /analyse_kpi — Analyse complète SSSE
# ══════════════════════════════════════════
@app.route('/analyse_kpi', methods=['POST'])
def analyse_kpi():

    data   = request.get_json() or {}
    lignes = data.get('lignes', [])
    source = data.get('source', 'SSSE')

    if not lignes:
        return jsonify({"erreur": "Aucune donnee recue"}), 400

    def to_float(val):
        try:
            return float(str(val).replace(',', '.').replace(' ', '').strip())
        except:
            return None

    NORMES = {
        "Humidite":      {"min": 13.5, "max": 14.5, "label": "Humidite",       "unite": "%"},
        "AW":            {"max": 0.7,               "label": "AW",             "unite": ""},
        "Proteine_Brut": {"min": 10,                "label": "Proteine Brut",  "unite": "%"},
        "Proteine_MS":   {"min": 12,                "label": "Proteine/MS",    "unite": "%"},
        "G_400":         {"max": 10,                "label": "Somme >400µ",    "unite": "%"},
        "G_355_250":     {"min": 40,                "label": "Somme 355-250",  "unite": "%"},
        "G_200":         {"max": 50,                "label": "Somme <200µ",    "unite": "%"},
        "G_125":         {"max": 10,                "label": "G <125µ",        "unite": "%"},
        "Gluten_Humide": {"min": 28,                "label": "Gluten Humide",  "unite": "%"},
        "Gluten_Index":  {"min": 65, "max": 90,     "label": "Gluten Index",   "unite": "%"},
        "Gluten_Sec":    {"min": 10,                "label": "Gluten Sec",     "unite": "%"},
        "Col_b":         {"min": 18,                "label": "Couleur b",      "unite": ""},
        "Piqure_Noir":   {"max": 10,                "label": "Piqure Noir",    "unite": ""},
        "Piqure_Brun":   {"max": 100,               "label": "Piqure Brun",    "unite": ""},
        "Cendres":       {"max": 1,                 "label": "Cendres",        "unite": "%"},
        "T_Chute":       {"min": 250,               "label": "T Chute",        "unite": ""},
        "Emballage":     {"valeur_ok": "C",         "label": "Emballage",      "unite": ""},
        "C_Poids":       {"valeur_ok": "C",         "label": "Poids",          "unite": ""},
        "C_Date":        {"valeur_ok": "C",         "label": "Etiquetage",     "unite": ""},
    }

    COL_MAP = {
        "Humidite":                           "Humidite",
        "Humidite (%)":                       "Humidite",
        "Humidité (%)":                       "Humidite",
        "AW":                                 "AW",
        "Proteine_Brut":                      "Proteine_Brut",
        "Protéine Brut (%) (+/-0,7)":         "Proteine_Brut",
        "Protéine Brut (%) (+/-0.7)":         "Proteine_Brut",
        "Proteine_MS":                        "Proteine_MS",
        "Protéine (%)/MS":                    "Proteine_MS",
        "G_400":                              "G_400",
        "∑ >400µ":                            "G_400",
        "G_355_250":                          "G_355_250",
        "∑ 355;250":                          "G_355_250",
        "G_200":                              "G_200",
        "∑ < 200µ":                           "G_200",
        "G_125":                              "G_125",
        "G < 125µ":                           "G_125",
        "Gluten_Humide":                      "Gluten_Humide",
        "Gluten Humide":                      "Gluten_Humide",
        "Gluten_Index":                       "Gluten_Index",
        "Gluten Index":                       "Gluten_Index",
        "Gluten_Sec":                         "Gluten_Sec",
        "Gluten Sec":                         "Gluten_Sec",
        "Col_b":                              "Col_b",
        "Col. b":                             "Col_b",
        "Piqure_Noir":                        "Piqure_Noir",
        "Piqûre Noir":                        "Piqure_Noir",
        "Piqure_Brun":                        "Piqure_Brun",
        "Piqûre Brun":                        "Piqure_Brun",
        "Cendres":                            "Cendres",
        "Cendres (%) (+/- 0,02)":             "Cendres",
        "T_Chute":                            "T_Chute",
        "T Chute":                            "T_Chute",
        "Emballage":                          "Emballage",
        "Embalage (Etanchite,visuel...)":     "Emballage",
        "Embalage (Etanchité,visuel...)":     "Emballage",
        "C_Poids":                            "C_Poids",
        "C.Poids ":                           "C_Poids",
        "C_Date":                             "C_Date",
        "C .Date ":                           "C_Date",
        "Date":                               "Date",
        "N_lot":                              "N_lot",
        "N°lot":                              "N_lot",
        "Heure":                              "Heure",
        "N_echantillon":                      "N_echantillon",
        "N° de l'échantillon":                "N_echantillon",
        "Etape":                              "Etape",
        "Flux_Statut":                        "Flux_Statut",
        "Decision":                           "Decision",
        "Décision":                           "Decision",
        "Probleme":                           "Probleme",
        "Problème":                           "Probleme",
        "Notif":                              "Notif",
    }

    rapports = []
    for ligne in lignes:
        r_norm = {}
        if isinstance(ligne, dict):
            for col_excel, col_interne in COL_MAP.items():
                val = ligne.get(col_excel)
                if val is not None and str(val).strip():
                    r_norm[col_interne] = val
        rapports.append(r_norm)

    nb_total = len(rapports)

    def verifier_conformite(valeur_raw, norme):
        if "valeur_ok" in norme:
            val = str(valeur_raw).strip()
            return None if not val else val == norme["valeur_ok"]
        val = to_float(valeur_raw)
        if val is None:
            return None
        if "min" in norme and val < norme["min"]:
            return False
        if "max" in norme and val > norme["max"]:
            return False
        return True

    stats_params = {
        k: {"valeurs": [], "hors_norme": 0, "total": 0}
        for k in NORMES
    }

    anomalies_par_ligne = []

    for r in rapports:
        anomalies_ligne = []
        for cle, norme in NORMES.items():
            val_raw = r.get(cle, '')
            if not str(val_raw).strip():
                continue
            stats_params[cle]["total"] += 1
            conforme = verifier_conformite(val_raw, norme)
            if conforme is False:
                stats_params[cle]["hors_norme"] += 1
                if "valeur_ok" in norme:
                    msg = "- " + norme['label'] + " : " + str(val_raw) + " (cible " + norme['valeur_ok'] + ")"
                elif "min" in norme and "max" in norme:
                    msg = ("- " + norme['label'] + " : " + str(val_raw) + " " +
                           norme['unite'] + " (cible " + str(norme['min']) +
                           " < x < " + str(norme['max']) + ")")
                elif "min" in norme:
                    msg = ("- " + norme['label'] + " : " + str(val_raw) + " " +
                           norme['unite'] + " (cible > " + str(norme['min']) + ")")
                else:
                    msg = ("- " + norme['label'] + " : " + str(val_raw) + " " +
                           norme['unite'] + " (cible < " + str(norme['max']) + ")")
                anomalies_ligne.append(msg)
            if conforme is not None and "valeur_ok" not in norme:
                v = to_float(val_raw)
                if v is not None:
                    stats_params[cle]["valeurs"].append(v)

        if anomalies_ligne:
            anomalies_par_ligne.append({
                "lot":          str(r.get('N_lot', 'N/A')),
                "date":         str(r.get('Date', 'N/A')),
                "heure":        str(r.get('Heure', 'N/A')),
                "echantillon":  str(r.get('N_echantillon', 'N/A')),
                "etape":        str(r.get('Etape', 'N/A')),
                "nb_anomalies": len(anomalies_ligne),
                "anomalies":    anomalies_ligne,
                "niveau":       "critique" if len(anomalies_ligne) >= 3 else "avertissement"
            })

    kpi_params = []
    for cle, norme in NORMES.items():
        stats   = stats_params[cle]
        valeurs = stats["valeurs"]
        total   = stats["total"]
        hors    = stats["hors_norme"]
        kpi = {
            "parametre":  norme["label"],
            "unite":      norme.get("unite", ""),
            "nb_mesures": total,
            "hors_norme": hors,
            "taux_ok":    round((total - hors) / total * 100, 1) if total > 0 else 100,
            "statut":     "critique" if hors >= 3 else "avertissement" if hors >= 1 else "normal"
        }
        if valeurs:
            kpi["moyenne"] = round(sum(valeurs) / len(valeurs), 3)
            kpi["minimum"] = round(min(valeurs), 3)
            kpi["maximum"] = round(max(valeurs), 3)
        if "min" in norme:
            kpi["norme_min"] = norme["min"]
        if "max" in norme:
            kpi["norme_max"] = norme["max"]
        kpi_params.append(kpi)

    kpi_params.sort(key=lambda x: x["taux_ok"])

    nb_anomalies      = len(anomalies_par_ligne)
    nb_critiques      = len([a for a in anomalies_par_ligne if a["niveau"] == "critique"])
    nb_avertissements = len([a for a in anomalies_par_ligne if a["niveau"] == "avertissement"])
    taux_conformite   = round((nb_total - nb_anomalies) / nb_total * 100, 1) if nb_total > 0 else 100

    params_problematiques = [p for p in kpi_params if p["hors_norme"] > 0]

    if nb_critiques > 0 or taux_conformite < 85:
        statut = "critique"
    elif nb_avertissements > 0 or taux_conformite < 90:
        statut = "avertissement"
    else:
        statut = "normal"

    # ── Mise à jour mémoire complète
    agent_etat['derniere_analyse']  = datetime.now().strftime('%d/%m/%Y %H:%M')
    agent_etat['nb_analyses']      += 1
    agent_etat['statut']            = statut
    agent_etat['taux_conformite']   = taux_conformite
    agent_etat['nb_non_conformes']  = nb_anomalies
    agent_etat['alertes_envoyees'].extend(anomalies_par_ligne)

    return jsonify({
        "source":     source,
        "horodatage": datetime.now().strftime('%d/%m/%Y %H:%M'),
        "statut":     statut,
        "kpi_globaux": {
            "nb_total":          nb_total,
            "nb_conformes":      nb_total - nb_anomalies,
            "nb_non_conformes":  nb_anomalies,
            "nb_critiques":      nb_critiques,
            "nb_avertissements": nb_avertissements,
            "taux_conformite":   taux_conformite
        },
        "kpi_parametres":        kpi_params,
        "anomalies":             anomalies_par_ligne[:20],
        "params_problematiques": params_problematiques[:5],
        "analyse_numero":        agent_etat['nb_analyses']
    })

# ══════════════════════════════════════════
# /agent/statut
# ══════════════════════════════════════════
@app.route('/agent/statut', methods=['GET'])
def agent_statut():
    return jsonify({
        "statut":            agent_etat['statut'],
        "derniere_analyse":  agent_etat['derniere_analyse'],
        "nb_analyses_total": agent_etat['nb_analyses'],
        "nb_alertes_total":  len(agent_etat['alertes_envoyees']),
        "en_ligne":          True
    })

# ══════════════════════════════════════════
# /kpi/statut — pour Power Apps dashboard
# Retourne exactement les 4 champs attendus
# ══════════════════════════════════════════
@app.route('/kpi/statut', methods=['GET'])
def kpi_statut():
    return jsonify({
        "statut":           agent_etat['statut'],
        "derniere_analyse": agent_etat['derniere_analyse'],
        "taux_conformite":  agent_etat['taux_conformite'],
        "nb_non_conformes": agent_etat['nb_non_conformes']
    })
