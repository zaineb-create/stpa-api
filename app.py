@app.route('/afficher_pdf', methods=['POST'])
def afficher_pdf():
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

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
        rightMargin=2*cm, leftMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()
    elements = []

    titre_style = ParagraphStyle('Titre', parent=styles['Title'],
        fontSize=22, textColor=colors.HexColor('#0b1d3a'), spaceAfter=10)
    elements.append(Paragraph("S.T.P.A - Rapport " + departement, titre_style))

    sous_titre_style = ParagraphStyle('SousTitre', parent=styles['Normal'],
        fontSize=11, textColor=colors.HexColor('#64748b'), spaceAfter=20)
    elements.append(Paragraph(
        "Genere le " + datetime.now().strftime('%d/%m/%Y a %H:%M') + " par " + utilisateur,
        sous_titre_style))
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
    elements.append(Spacer(1, 1*cm))

    footer_style = ParagraphStyle('Footer', parent=styles['Normal'],
        fontSize=9, textColor=colors.HexColor('#94a3b8'), alignment=1)
    elements.append(Paragraph(
        "S.T.P.A - Societe Tunisienne de Production Alimentaire | STPA Connect",
        footer_style))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')

    # ── Retourne une page HTML avec le PDF intégré
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Rapport """ + departement + """</title>
    <style>
        body {{ margin: 0; padding: 0; background: #1e2035; }}
        .header {{
            background: #0b1d3a;
            color: white;
            padding: 15px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{ margin: 0; font-size: 20px; font-family: Arial; }}
        .btn {{
            background: #2563eb;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            text-decoration: none;
        }}
        iframe {{
            width: 100%;
            height: calc(100vh - 60px);
            border: none;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📄 Rapport """ + departement + """ — """ + datetime.now().strftime('%d/%m/%Y') + """</h1>
        <a class="btn" href="data:application/pdf;base64,""" + pdf_base64 + """" 
           download="rapport_""" + departement + """_""" + datetime.now().strftime('%Y%m%d') + """.pdf">
           ⬇️ Telecharger PDF
        </a>
    </div>
    <iframe src="data:application/pdf;base64,""" + pdf_base64 + """"></iframe>
</body>
</html>"""

    from flask import Response
    return Response(html, mimetype='text/html')
