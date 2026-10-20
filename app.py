import os
import json
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from openai import OpenAI

load_dotenv()
app = Flask(__name__)

MOTOS = [
    {"id": "MOTO-001", "marque": "Yamaha", "modele": "MT-07", "immatriculation": "AB-1234", "statut": "Disponible"},
    {"id": "MOTO-002", "marque": "Honda", "modele": "CB 500", "immatriculation": "CD-5678", "statut": "En maintenance"},
]

SYSTEM_PROMPT = """Tu es GestMoto, un agent professionnel de gestion de motos.
Tu aides à consulter le parc, les disponibilités, les maintenances et à préparer des réservations.
Réponds en français, de façon courte et pratique. Ne prétends jamais avoir effectué une action si elle n'est pas confirmée.
Si la demande sort de la gestion de motos, explique poliment que tu es spécialisé dans ce domaine."""


def get_ai_client():
    api_key = os.getenv("NEON_AI_GATEWAY_TOKEN") or os.getenv("OPENAI_API_KEY")
    gateway_url = os.getenv("NEON_AI_GATEWAY_BASE_URL")
    if not api_key or api_key == "your_api_key_here":
        return None
    base_url = f"{gateway_url.rstrip('/')}/v1" if gateway_url else os.getenv("OPENAI_BASE_URL") or None
    return OpenAI(api_key=api_key, base_url=base_url)


def local_reply(message):
    text = message.lower()
    if "disponib" in text:
        available = [m for m in MOTOS if m["statut"] == "Disponible"]
        return "Motos disponibles : " + ", ".join(f'{m["marque"]} {m["modele"]} ({m["immatriculation"]})' for m in available) + "."
    if "parc" in text or "moto" in text:
        return f"Le parc contient {len(MOTOS)} motos : " + "; ".join(f'{m["marque"]} {m["modele"]} — {m["statut"]}' for m in MOTOS) + "."
    return "Je peux vous aider avec les motos disponibles, le parc et les maintenances. Quelle information souhaitez-vous ?"


def ask_agent(message, history=None):
    client = get_ai_client()
    if client is None:
        return local_reply(message)
    messages = [{"role": "system", "content": f"{SYSTEM_PROMPT}\nDonnées du parc : {MOTOS}"}]
    messages.extend((history or [])[-10:])
    messages.append({"role": "user", "content": message})
    try:
        result = client.chat.completions.create(
            model=os.getenv("AI_MODEL", "gpt-4o-mini"),
            temperature=0.2,
            messages=messages,
        )
        return result.choices[0].message.content or "Je n’ai pas pu formuler une réponse."
    except Exception:
        app.logger.exception("Appel du modèle impossible, utilisation du mode local")
        return local_reply(message)


@app.get("/")
def home():
    return render_template("index.html")


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    if not message:
        return jsonify(error="Le message est obligatoire."), 400
    try:
        return jsonify(reply=ask_agent(message, data.get("history", [])))
    except Exception:
        app.logger.exception("Erreur agent")
        return jsonify(error="Erreur pendant la réponse de l’agent."), 500


@app.get("/webhook")
def verify_whatsapp():
    if request.args.get("hub.verify_token") == os.getenv("WHATSAPP_VERIFY_TOKEN") and request.args.get("hub.mode") == "subscribe":
        return request.args.get("hub.challenge", ""), 200
    return "Forbidden", 403


@app.post("/webhook")
def whatsapp_webhook():
    payload = request.get_json(silent=True) or {}
    message = (((payload.get("entry") or [{}])[0].get("changes") or [{}])[0].get("value") or {}).get("messages", [{}])[0]
    if message.get("type") != "text" or not message.get("from"):
        return "EVENT_RECEIVED", 200
    try:
        reply = ask_agent(message["text"]["body"])
        send_whatsapp_message(message["from"], reply)
    except Exception:
        app.logger.exception("Erreur WhatsApp")
    return "EVENT_RECEIVED", 200


def send_whatsapp_message(to, body):
    token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    if not token or not phone_id:
        app.logger.warning("WhatsApp non configuré : réponse non envoyée")
        return
    version = os.getenv("META_GRAPH_VERSION", "v21.0")
    payload = json.dumps({"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": body}}).encode()
    req = Request(
        f"https://graph.facebook.com/{version}/{phone_id}/messages",
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=20) as response:
        if response.status >= 300:
            raise RuntimeError(f"Meta API returned HTTP {response.status}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG") == "1")
