from weasyprint import HTML

# Ajusta la ruta al HTML de tu Flask si hace falta
HTML('http://127.0.0.1:5002/informe').write_pdf('informe.pdf')
print("✅ PDF generado correctamente como 'informe.pdf'")