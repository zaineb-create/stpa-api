from flask import Flask, request, jsonify, Response
from datetime import datetime
import io
import base64

app = Flask(__name__)

# ══════════════════════════════════════════
# Mémoire interne de l'agent
# ══════════════════════════════════════════
agent_etat = {
    "derniere_analyse": None,
    "nb_analyses": 0,
    "alertes_envoyees": [],
    "statut": "en attente"
}

# ══════════════════════════════════════════
# /test
# ══════════════════════════════════════════
@app.route('/test', methods=['GET'])
def test():
    return jsonify({"status": "OK", "message": "API STPA fonctionne"})

# ══════════════════════════════════════════
# /analyse
# ══════════════════════════════════════════
@app.route('/analyse', methods=['POST'])
def analyse():
    data = request.get_json()
    valeurs = data.get('valeurs', [])
    if not valeurs:
        return jsonify({"erreur": "Aucune donnee"}), 400
    return jsonify({
        "total": round(sum(valeurs), 2),
        "moyenne": round(sum(valeurs) / len(valeurs), 2),
        "maximum": max(valeurs),
        "minimum": min(valeurs),
        "count": len(valeurs)
    })

# ══════════════════════════════════════════
# /recommandations
# ══════════════════════════════════════════
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

# ══════════════════════════════════════════
# /generer_pdf
# ══════════════════════════════════════════
@app.route('/generer_pdf', methods=['POST'])
def generer_pdf():
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.units import cm

    data = request.get_json()
    departement = data.get('departement', 'N/A')
    total_rapports = data.get('total_rapports', 0)
    favoris = data.get('favoris', 0)
    conformite = data.get('conformite', 0)
    utilisateur = data.get('utilisateur', 'N/A')
    rapports = data.get('rapports', [])

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    elements = []

    titre_style = ParagraphStyle('Titre', parent=styles['Title'],
        fontSize=22, textColor=colors.HexColor('#0b1d3a'), spaceAfter=10)
    elements.append(Paragraph("S.T.P.A - Rapport " + departement, titre_style))

    sous_style = ParagraphStyle('Sous', parent=styles['Normal'],
        fontSize=11, textColor=colors.HexColor('#64748b'), spaceAfter=20)
    elements.append(Paragraph(
        "Genere le " + datetime.now().strftime('%d/%m/%Y a %H:%M') + " par " + utilisateur,
        sous_style))
    elements.append(Spacer(1, 0.5*cm))

    kpi_style = ParagraphStyle('KPI', parent=styles['Normal'],
        fontSize=13, textColor=colors.HexColor('#0b1d3a'),
        fontName='Helvetica-Bold', spaceAfter=6)
    elements.append(Paragraph("Indicateurs cles", kpi_style))
    elements.append(Spacer(1, 0.3*cm))

    kpi_data = [
        ['Indicateur', 'Valeur'],
        ['Total Rapports', str(total_rapports)],
        ['Favoris', str(favoris)],
        ['Conformite CQ', str(conformite) + '%'],
        ['Departement', departement],
        ['Date rapport', datetime.now().strftime('%d/%m/%Y')]
    ]
    kpi_table = Table(kpi_data, colWidths=[8*cm, 8*cm])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0b1d3a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 12),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dde4f0')),
        ('ROWHEIGHT', (0,0), (-1,-1), 0.8*cm),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 0.8*cm))

    if rapports:
        elements.append(Paragraph("Liste des rapports", kpi_style))
        elements.append(Spacer(1, 0.3*cm))
        rapport_data = [['#', 'Titre', 'Type', 'Favori']]
        for i, r in enumerate(rapports, 1):
            rapport_data.append([
                str(i), r.get('titre', 'N/A'),
                r.get('type', 'N/A'),
                'Oui' if r.get('favori') else 'Non'
            ])
        rapport_table = Table(rapport_data, colWidths=[1*cm, 10*cm, 4*cm, 2*cm])
        rapport_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2563eb')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dde4f0')),
            ('ROWHEIGHT', (0,0), (-1,-1), 0.7*cm),
        ]))
        elements.append(rapport_table)

    footer_style = ParagraphStyle('Footer', parent=styles['Normal'],
        fontSize=9, textColor=colors.HexColor('#94a3b8'), alignment=1)
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph(
        "S.T.P.A - Societe Tunisienne de Production Alimentaire | STPA Connect",
        footer_style))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
    return jsonify({
        "pdf_base64": pdf_base64,
        "nom_fichier": "rapport_" + departement + "_" + datetime.now().strftime('%Y%m%d') + ".pdf",
        "taille": len(pdf_bytes),
        "date": datetime.now().strftime('%d/%m/%Y %H:%M')
    })

# ══════════════════════════════════════════
# /afficher_pdf
# ══════════════════════════════════════════
@app.route('/afficher_pdf', methods=['GET', 'POST'])
def afficher_pdf():
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.units import cm

    data = request.get_json() or {} if request.method == 'POST' else request.args

    departement    = data.get('departement', 'N/A')
    total_rapports = int(data.get('total_rapports', 0))
    favoris        = int(data.get('favoris', 0))
    conformite     = float(data.get('conformite', 0))
    utilisateur    = data.get('utilisateur', 'N/A')
    titre          = data.get('titre', 'Rapport')

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    elements = []

    titre_style = ParagraphStyle('Titre', parent=styles['Title'],
        fontSize=22, textColor=colors.HexColor('#0b1d3a'), spaceAfter=10)
    elements.append(Paragraph("S.T.P.A - " + titre, titre_style))

    sous_style = ParagraphStyle('Sous', parent=styles['Normal'],
        fontSize=11, textColor=colors.HexColor('#64748b'), spaceAfter=20)
    elements.append(Paragraph(
        "Genere le " + datetime.now().strftime('%d/%m/%Y a %H:%M') + " par " + utilisateur,
        sous_style))
    elements.append(Spacer(1, 0.5*cm))

    kpi_style = ParagraphStyle('KPI', parent=styles['Normal'],
        fontSize=13, textColor=colors.HexColor('#0b1d3a'),
        fontName='Helvetica-Bold', spaceAfter=6)
    elements.append(Paragraph("Indicateurs cles", kpi_style))
    elements.append(Spacer(1, 0.3*cm))

    kpi_data = [
        ['Indicateur', 'Valeur'],
        ['Titre', titre],
        ['Departement', departement],
        ['Total Rapports', str(total_rapports)],
        ['Favoris', str(favoris)],
        ['Conformite CQ', str(conformite) + '%'],
        ['Date rapport', datetime.now().strftime('%d/%m/%Y')]
    ]
    kpi_table = Table(kpi_data, colWidths=[8*cm, 8*cm])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0b1d3a')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 12),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dde4f0')),
        ('ROWHEIGHT', (0,0), (-1,-1), 0.8*cm),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 1*cm))

    footer_style = ParagraphStyle('Footer', parent=styles['Normal'],
        fontSize=9, textColor=colors.HexColor('#94a3b8'), alignment=1)
    elements.append(Paragraph(
        "S.T.P.A - Societe Tunisienne de Production Alimentaire | STPA Connect",
        footer_style))

    doc.build(elements)
    pdf_bytes   = buffer.getvalue()
    pdf_base64  = base64.b64encode(pdf_bytes).decode('utf-8')
    nom_fichier = "rapport_" + departement + "_" + datetime.now().strftime('%Y%m%d') + ".pdf"

    html = (
        "<!DOCTYPE html><html><head><meta charset='UTF-8'><title>" + titre + "</title>"
        "<style>*{margin:0;padding:0;box-sizing:border-box}"
        "body{background:#0f172a;font-family:Arial,sans-serif}"
        ".header{background:#0b1d3a;color:white;padding:12px 24px;display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #2563eb}"
        ".header h1{font-size:18px}.header span{font-size:13px;color:#94a3b8;margin-left:12px}"
        ".btn{background:#2563eb;color:white;padding:10px 20px;border-radius:8px;font-size:14px;text-decoration:none;display:inline-block}"
        "iframe{width:100%;height:calc(100vh - 56px);border:none;display:block}"
        "</style></head><body>"
        "<div class='header'><div><h1>Rapport " + titre + "</h1>"
        "<span>Departement : " + departement + " | " + datetime.now().strftime('%d/%m/%Y %H:%M') + "</span></div>"
        "<a class='btn' href='data:application/pdf;base64," + pdf_base64 +
        "' download='" + nom_fichier + "'>Telecharger PDF</a></div>"
        "<iframe src='data:application/pdf;base64," + pdf_base64 + "'></iframe>"
        "</body></html>"
    )
    return Response(html, mimetype='text/html')

# ══════════════════════════════════════════
# /excel_en_pdf
# ══════════════════════════════════════════
@app.route('/excel_en_pdf', methods=['GET', 'POST'])
def excel_en_pdf():
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.units import cm

    data = request.get_json() or {} if request.method == 'POST' else request.args

    titre       = data.get('titre', 'Rapport Excel')
    departement = data.get('departement', 'N/A')
    utilisateur = data.get('utilisateur', 'N/A')
    colonnes    = data.get('colonnes', [])
    lignes      = data.get('lignes', [])

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    elements = []

    titre_style = ParagraphStyle('Titre', parent=styles['Title'],
        fontSize=20, textColor=colors.HexColor('#0b1d3a'), spaceAfter=6)
    elements.append(Paragraph("S.T.P.A - " + titre, titre_style))

    sous_style = ParagraphStyle('Sous', parent=styles['Normal'],
        fontSize=10, textColor=colors.HexColor('#64748b'), spaceAfter=16)
    elements.append(Paragraph(
        "Departement : " + departement + " | Genere le " +
        datetime.now().strftime('%d/%m/%Y a %H:%M') + " par " + utilisateur,
        sous_style))
    elements.append(Spacer(1, 0.3*cm))

    if colonnes and lignes:
        kpi_style = ParagraphStyle('KPI', parent=styles['Normal'],
            fontSize=12, textColor=colors.HexColor('#0b1d3a'),
            fontName='Helvetica-Bold', spaceAfter=6)
        elements.append(Paragraph("Donnees du fichier Excel", kpi_style))
        elements.append(Spacer(1, 0.3*cm))

        nb_col    = len(colonnes)
        col_width = (25*cm) / nb_col
        table_data = [colonnes]
        for ligne in lignes:
            table_data.append([str(v) for v in ligne])

        table = Table(table_data, colWidths=[col_width] * nb_col)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0b1d3a')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('FONTSIZE', (0,1), (-1,-1), 9),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dde4f0')),
            ('ROWHEIGHT', (0,0), (-1,-1), 0.7*cm),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('ROWBACKGROUNDS', (0,1), (-1,-1),
             [colors.HexColor('#f8fafc'), colors.white]),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.5*cm))

        stats_data = [
            ['Total lignes', str(len(lignes))],
            ['Total colonnes', str(len(colonnes))],
            ['Date export', datetime.now().strftime('%d/%m/%Y %H:%M')]
        ]
        stats_table = Table(stats_data, colWidths=[8*cm, 8*cm])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0f9ff')),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dde4f0')),
            ('ROWHEIGHT', (0,0), (-1,-1), 0.7*cm),
        ]))
        elements.append(stats_table)
    else:
        elements.append(Paragraph("Aucune donnee disponible", styles['Normal']))

    footer_style = ParagraphStyle('Footer', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#94a3b8'), alignment=1)
    elements.append(Spacer(1, 0.8*cm))
    elements.append(Paragraph(
        "S.T.P.A - Societe Tunisienne de Production Alimentaire | STPA Connect",
        footer_style))

    doc.build(elements)
    pdf_bytes   = buffer.getvalue()
    pdf_base64  = base64.b64encode(pdf_bytes).decode('utf-8')
    nom_fichier = "excel_" + departement + "_" + datetime.now().strftime('%Y%m%d') + ".pdf"

    html = (
        "<!DOCTYPE html><html><head><meta charset='UTF-8'><title>" + titre + "</title>"
        "<style>*{margin:0;padding:0;box-sizing:border-box}"
        "body{background:#0f172a;font-family:Arial,sans-serif}"
        ".header{background:#0b1d3a;color:white;padding:12px 24px;display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #2563eb}"
        ".header h1{font-size:18px}.header span{font-size:12px;color:#94a3b8}"
        ".btn{background:#2563eb;color:white;padding:10px 20px;border-radius:8px;font-size:14px;text-decoration:none}"
        "iframe{width:100%;height:calc(100vh - 56px);border:none;display:block}"
        "</style></head><body>"
        "<div class='header'><div><h1>" + titre + "</h1>"
        "<span>" + departement + " | " + datetime.now().strftime('%d/%m/%Y %H:%M') + "</span></div>"
        "<a class='btn' href='data:application/pdf;base64," + pdf_base64 +
        "' download='" + nom_fichier + "'>Telecharger PDF</a></div>"
        "<iframe src='data:application/pdf;base64," + pdf_base64 + "'></iframe>"
        "</body></html>"
    )
    return Response(html, mimetype='text/html')

# ══════════════════════════════════════════
# /alertes — analyse seuils conformité
# ══════════════════════════════════════════
@app.route('/alertes', methods=['POST'])
def alertes():
    data                = request.get_json()
    rapports            = data.get('rapports', [])
    seuil_critique      = float(data.get('seuil_critique', 85))
    seuil_avertissement = float(data.get('seuil_avertissement', 90))

    alertes_list = []
    for r in rapports:
        dept       = r.get('departement', 'N/A')
        conformite = float(r.get('conformite', 100))
        nb_alertes = int(r.get('alertes', 0))

        if conformite < seuil_critique or nb_alertes >= 5:
            alertes_list.append({
                "type": "critique",
                "departement": dept,
                "message": "Conformite critique : " + str(conformite) + "% pour " + dept,
                "conformite": conformite,
                "couleur": "#E24B4A",
                "priorite": 1
            })
        elif conformite < seuil_avertissement or nb_alertes >= 3:
            alertes_list.append({
                "type": "avertissement",
                "departement": dept,
                "message": "Conformite faible : " + str(conformite) + "% pour " + dept,
                "conformite": conformite,
                "couleur": "#BA7517",
                "priorite": 2
            })

    alertes_list.sort(key=lambda x: x['priorite'])
    return jsonify({
        "nb_alertes": len(alertes_list),
        "nb_critiques": len([a for a in alertes_list if a['type'] == 'critique']),
        "nb_avertissements": len([a for a in alertes_list if a['type'] == 'avertissement']),
        "alertes": alertes_list,
        "statut": "critique" if any(a['type'] == 'critique' for a in alertes_list) else
                  "avertissement" if alertes_list else "normal"
    })

# ══════════════════════════════════════════
# /agent — Agent IA autonome
# ══════════════════════════════════════════
@app.route('/agent', methods=['POST'])
def agent():
    import json
    import urllib.request as url_req

    data        = request.get_json() or {}
    colonnes    = data.get('colonnes', [])
    lignes      = data.get('lignes', [])
    webhook     = data.get('webhook_url', '')
    utilisateur = data.get('utilisateur', 'Agent STPA')

    if not colonnes or not lignes:
        return jsonify({"erreur": "colonnes et lignes sont obligatoires"}), 400

    # Analyse ligne par ligne
    alertes_detectees = []
    for ligne in lignes:
        rapport = {}
        for i, col in enumerate(colonnes):
            rapport[col] = ligne[i] if i < len(ligne) else ''

        dept  = str(rapport.get('Département', rapport.get('Departement', 'N/A')))
        titre = str(rapport.get('Titre', rapport.get('Title', 'N/A')))

        conf_raw = str(rapport.get('Conforme', rapport.get('Conformite', '100')))
        conf_raw = conf_raw.replace('%', '').replace(',', '.').strip()
        try:
            conformite = float(conf_raw)
        except ValueError:
            conformite = 100.0

        if conformite < 85:
            niveau  = "critique"
            message = "Conformite critique " + str(round(conformite, 1)) + "% — " + dept + " — " + titre
        elif conformite < 90:
            niveau  = "avertissement"
            message = "Conformite faible " + str(round(conformite, 1)) + "% — " + dept + " — " + titre
        else:
            niveau  = "normal"
            message = None

        if message:
            alertes_detectees.append({
                "departement": dept,
                "titre": titre,
                "conformite": round(conformite, 1),
                "niveau": niveau,
                "message": message,
                "horodatage": datetime.now().strftime('%d/%m/%Y %H:%M')
            })

    # Mise à jour mémoire
    agent_etat['derniere_analyse'] = datetime.now().strftime('%d/%m/%Y %H:%M')
    agent_etat['nb_analyses']     += 1
    agent_etat['alertes_envoyees'].extend(alertes_detectees)

    if any(a['niveau'] == 'critique' for a in alertes_detectees):
        agent_etat['statut'] = 'critique'
    elif alertes_detectees:
        agent_etat['statut'] = 'avertissement'
    else:
        agent_etat['statut'] = 'normal'

    # Déclenchement webhook Power Automate
    flux_declenche = False
    if alertes_detectees and webhook:
        payload = json.dumps({
            "nb_alertes": len(alertes_detectees),
            "nb_critiques": len([a for a in alertes_detectees if a['niveau'] == 'critique']),
            "nb_avertissements": len([a for a in alertes_detectees if a['niveau'] == 'avertissement']),
            "alertes": alertes_detectees,
            "statut": agent_etat['statut'],
            "horodatage": agent_etat['derniere_analyse'],
            "analyse_par": utilisateur
        }).encode('utf-8')
        req = url_req.Request(
            webhook,
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        try:
            with url_req.urlopen(req, timeout=15) as resp:
                flux_declenche = resp.status in (200, 202)
        except Exception:
            flux_declenche = False

    return jsonify({
        "statut": agent_etat['statut'],
        "nb_lignes_analysees": len(lignes),
        "nb_alertes": len(alertes_detectees),
        "nb_critiques": len([a for a in alertes_detectees if a['niveau'] == 'critique']),
        "nb_avertissements": len([a for a in alertes_detectees if a['niveau'] == 'avertissement']),
        "alertes": alertes_detectees,
        "flux_declenche": flux_declenche,
        "analyse_numero": agent_etat['nb_analyses'],
        "horodatage": agent_etat['derniere_analyse'],
        "analyse_par": utilisateur
    })

# ══════════════════════════════════════════
# /agent/statut — état de l'agent
# ══════════════════════════════════════════
@app.route('/agent/statut', methods=['GET'])
def agent_statut():
    return jsonify({
        "statut": agent_etat['statut'],
        "derniere_analyse": agent_etat['derniere_analyse'],
        "nb_analyses_total": agent_etat['nb_analyses'],
        "nb_alertes_total": len(agent_etat['alertes_envoyees']),
        "en_ligne": True
    })
