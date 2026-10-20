# GestMoto — agent IA Flask, Web et WhatsApp

## Installation

```powershell
& "C:/Users/fofan/AppData/Local/Programs/Python/Python313/python.exe" -m pip install -r requirements.txt
Copy-Item .env.example .env
& "C:/Users/fofan/AppData/Local/Programs/Python/Python313/python.exe" app.py
```

Puis ouvrir `http://localhost:5000`.

Pour activer l’IA, renseigner `OPENAI_API_KEY` dans `.env`. Un mode local est fourni automatiquement si aucune clé n’est disponible.

Pour WhatsApp Cloud API, exposer `/webhook` en HTTPS, utiliser la même valeur que `WHATSAPP_VERIFY_TOKEN` dans Meta Developers, puis renseigner `WHATSAPP_ACCESS_TOKEN` et `WHATSAPP_PHONE_NUMBER_ID`.
