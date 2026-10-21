import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

app = Flask(__name__)
CORS(app, origins=os.getenv("ALLOWED_ORIGIN", "*"))

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

LEVELS = {
    1: "Give only a tiny nudge: one gentle clue or one guiding question.",
    2: "Give a bigger hint: name the idea or formula needed and the first step.",
    3: "Give a step-by-step hint, but STOP before the final answer.",
}


def system_prompt(grade, subject, level):
    return (
        f"You are Hinty, a cheerful owl tutor for a student in class {grade} ({subject}). "
        "Use simple words, short sentences and a few emojis. "
        "NEVER give the final answer directly. Give HINTS that help the student think. "
        "End with a short encouraging line or a question. "
        f"{LEVELS.get(level, LEVELS[1])} Keep it under 90 words. "
        "If the message is unsafe or not about studies, kindly steer back to learning."
    )


CHOSEN = {}  # remembers the working model for each provider

GROQ_PREFER = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "openai/gpt-oss-20b",
               "openai/gpt-oss-120b", "qwen/qwen3-32b"]
GEMINI_PREFER = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash",
                 "gemini-2.5-flash-lite", "gemini-flash-lite-latest"]


def _raise(r):
    """Raise an error that includes the REAL message from the provider."""
    if r.status_code >= 400:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")


def discover_groq(key):
    r = requests.get("https://api.groq.com/openai/v1/models",
                     headers={"Authorization": f"Bearer {key}"}, timeout=20)
    _raise(r)
    ids = [m["id"] for m in r.json().get("data", [])]
    for p in GROQ_PREFER:
        if p in ids:
            return p
    bad = ("whisper", "orpheus", "guard", "tts", "playai", "distil")
    ok = [i for i in ids if not any(b in i.lower() for b in bad)]
    if ok:
        return ok[0]
    raise RuntimeError("This Groq key has no chat models: " + str(ids))


def discover_gemini(key):
    r = requests.get("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200",
                     headers={"x-goog-api-key": key}, timeout=20)
    _raise(r)
    names = [m["name"].split("/")[-1] for m in r.json().get("models", [])
             if "generateContent" in m.get("supportedGenerationMethods", [])]
    for p in GEMINI_PREFER:
        if p in names:
            return p
    skip = ("image", "tts", "live", "audio", "preview", "exp", "thinking")
    flash = [n for n in names if "flash" in n and not any(x in n for x in skip)]
    if flash:
        return flash[0]
    if names:
        return names[0]
    raise RuntimeError("This Gemini key has no usable models")


def with_model(name, key, default_model, discover, call):
    """Try the configured model; on 404 find a model this key can really use."""
    model = CHOSEN.get(name, default_model)
    r = call(key, model)
    if r.status_code == 404:
        model = discover(key)
        CHOSEN[name] = model
        print(f"[{name}] model not found, switched to: {model}")
        r = call(key, model)
    _raise(r)
    return r


def ask_gemini(key, system, messages):
    contents = [
        {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
        for m in messages
    ]

    def call(k, model):
        return requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": k, "Content-Type": "application/json"},
            json={"systemInstruction": {"parts": [{"text": system}]}, "contents": contents},
            timeout=40)

    r = with_model("gemini", key, GEMINI_MODEL, discover_gemini, call)
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def ask_groq(key, system, messages):
    def call(k, model):
        return requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"},
            json={"model": model, "max_tokens": 400,
                  "messages": [{"role": "system", "content": system}] + messages},
            timeout=40)

    r = with_model("groq", key, GROQ_MODEL, discover_groq, call)
    return r.json()["choices"][0]["message"]["content"]


@app.get("/api/diagnose")
def diagnose():
    """Open http://127.0.0.1:5000/api/diagnose to see what each key can use."""
    out = {}
    for name, env, fn in (("gemini", "GEMINI_API_KEY", discover_gemini),
                          ("groq", "GROQ_API_KEY", discover_groq)):
        key = os.getenv(env)
        if not key:
            out[name] = "no key set"
            continue
        try:
            out[name] = {"key_works": True, "model_to_use": fn(key)}
        except Exception as e:
            out[name] = {"key_works": False, "error": str(e)}
    return jsonify(out)


@app.get("/")
def home():
    return jsonify(
        status="Hinty backend is awake! 🦉",
        gemini_key_set=bool(os.getenv("GEMINI_API_KEY")),
        groq_key_set=bool(os.getenv("GROQ_API_KEY")),
    )


@app.post("/api/hint")
def hint():
    d = request.get_json(silent=True) or {}
    question = (d.get("question") or "").strip()[:800]
    if not question:
        return jsonify(error="Please type a question"), 400
    grade = d.get("grade", 6)
    subject = d.get("subject", "General")
    try:
        level = int(d.get("level", 1))
    except (TypeError, ValueError):
        level = 1
    history = [
        {"role": m["role"], "content": str(m.get("content", ""))[:1500]}
        for m in (d.get("history") or [])[-6:]
        if isinstance(m, dict) and m.get("role") in ("user", "assistant")
    ]
    messages = history + [{"role": "user", "content": question}]
    system = system_prompt(grade, subject, level)

    providers = [
        (os.getenv("GEMINI_API_KEY"), ask_gemini, "Gemini"),
        (os.getenv("GROQ_API_KEY"), ask_groq, "Groq"),
    ]
    errors = []
    for key, fn, name in providers:
        if not key:
            continue
        try:
            return jsonify(hint=fn(key, system, messages), provider=name)
        except Exception as e:
            print(f"[{name}] failed:", e)
            errors.append(f"{name}: {e}")
    if not any(k for k, _, _ in providers):
        return jsonify(error="No API key is set on the backend. Set GEMINI_API_KEY or GROQ_API_KEY."), 503
    return jsonify(error="Hinty is sleepy right now 😴 Try again!", details=errors), 503


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)