from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
import os, json, io, fitz, requests
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

FRONTEND_DIR   = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
app = Flask(__name__, static_folder=FRONTEND_DIR)
CORS(app)

GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_URL       = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL     = "llama-3.3-70b-versatile"
GEMINI_URL     = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=" + (GEMINI_API_KEY or "")

@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/chat.html")
def chat_page():
    return send_from_directory(FRONTEND_DIR, "chat.html")

@app.route("/jobs.html")
def jobs_page():
    return send_from_directory(FRONTEND_DIR, "jobs.html")

@app.route("/auth-guard.js")
def auth_guard():
    return send_from_directory(FRONTEND_DIR, "auth-guard.js")

@app.route("/profile.html")
def profile_page():
    return send_from_directory(FRONTEND_DIR, "profile.html")

@app.route("/login.html")
def login_page():
    return send_from_directory(FRONTEND_DIR, "login.html")

@app.route("/resume.html")
def resume_page():
    return send_from_directory(FRONTEND_DIR, "resume.html")

@app.route("/roadmap.html")
def roadmap_page():
    return send_from_directory(FRONTEND_DIR, "roadmap.html")

@app.route("/interview.html")
def interview_page():
    return send_from_directory(FRONTEND_DIR, "interview.html")

@app.route("/courses.html")
def courses_page():
    return send_from_directory(FRONTEND_DIR, "courses.html")

def ask_ai(prompt, temperature=0.3):
    """Try Gemini first, fall back to Groq."""
    try:
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        res = requests.post(GEMINI_URL, json=payload, timeout=30)
        res.raise_for_status()
        return res.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        headers = {"Authorization": "Bearer " + (GROQ_API_KEY or ""), "Content-Type": "application/json"}
        payload = {"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}], "temperature": temperature}
        res = requests.post(GROQ_URL, json=payload, headers=headers, timeout=30)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]

def clean_json(raw):
    """Extract and parse JSON from AI response robustly."""
    import re
    raw = raw.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    # Extract content between first { and last }
    start = raw.find("{")
    end   = raw.rfind("}")
    if start != -1 and end != -1:
        raw = raw[start:end+1]
    # Try direct parse first
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fix common AI JSON issues: trailing commas, unescaped chars
        raw = re.sub(r',\s*}', '}', raw)
        raw = re.sub(r',\s*]', ']', raw)
        # Remove control characters
        raw = re.sub(r'[\x00-\x1f\x7f]', ' ', raw)
        return json.loads(raw)

def extract_text(file):
    """Extract text from uploaded PDF, JSON, or image file."""
    name = file.filename.lower()
    if name.endswith(".pdf"):
        doc = fitz.open(stream=file.read(), filetype="pdf")
        return "".join(p.get_text() for p in doc).strip()
    elif name.endswith(".json"):
        raw = file.read().decode("utf-8")
        try: return json.dumps(json.loads(raw), indent=2)
        except: return raw
    elif name.endswith((".png", ".jpg", ".jpeg")):
        img = Image.open(io.BytesIO(file.read()))
        return "[Image resume: {}, size={}]".format(file.filename, img.size)
    return ""
    name = file.filename.lower()
    if name.endswith(".pdf"):
        doc = fitz.open(stream=file.read(), filetype="pdf")
        return "".join(p.get_text() for p in doc).strip()
    elif name.endswith(".json"):
        raw = file.read().decode("utf-8")
        try: return json.dumps(json.loads(raw), indent=2)
        except: return raw
    elif name.endswith((".png", ".jpg", ".jpeg")):
        img = Image.open(io.BytesIO(file.read()))
        return "[Image resume: {}, size={}]".format(file.filename, img.size)
    return ""

def groq_stream(messages):
    headers = {"Authorization": "Bearer " + (GROQ_API_KEY or ""), "Content-Type": "application/json"}
    payload = {"model": GROQ_MODEL, "messages": messages, "temperature": 0.7, "stream": True}
    return requests.post(GROQ_URL, json=payload, headers=headers, stream=True, timeout=60)

# ── /api/chat — Groq streaming ──
@app.route("/api/chat", methods=["POST"])
def api_chat():
    try:
        data = request.json
        messages = data.get("messages", [])
        if not messages:
            return jsonify({"error": "No messages provided"}), 400
        system = {"role": "system", "content": (
            "You are CareerPilot AI, a helpful expert career advisor. "
            "Help with resume tips, interview prep, career roadmaps, job search, salary negotiation. "
            "Be concise unless asked for detail. Use bullet points when helpful."
        )}
        def generate():
            resp = groq_stream([system] + messages)
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        chunk = line[6:]
                        if chunk == "[DONE]":
                            yield "data: [DONE]\n\n"
                            break
                        try:
                            delta = json.loads(chunk)["choices"][0]["delta"].get("content", "")
                            if delta:
                                yield "data: " + json.dumps({"content": delta}) + "\n\n"
                        except: pass
        return Response(stream_with_context(generate()), mimetype="text/event-stream",
                        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── /score ──
@app.route("/score", methods=["POST"])
def score():
    try:
        resume = request.form.get("resume", "")
        target_role = request.form.get("target_role", "Software Developer")
        if "file" in request.files:
            f = request.files["file"]
            if f.filename:
                resume = extract_text(f)
        if not resume:
            return jsonify({"error": "No resume content provided"}), 400

        prompt = """Analyze the resume below for the role of "{role}".
Respond with ONLY a valid JSON object. No explanation, no markdown, no extra text.
Use this exact structure (replace angle bracket values with actual data):

{{
  "total_score": 72,
  "breakdown": {{
    "keywords":     {{"score": 14, "max": 20, "feedback": "your feedback here"}},
    "experience":   {{"score": 16, "max": 20, "feedback": "your feedback here"}},
    "education":    {{"score": 12, "max": 15, "feedback": "your feedback here"}},
    "skills":       {{"score": 15, "max": 20, "feedback": "your feedback here"}},
    "formatting":   {{"score": 10, "max": 15, "feedback": "your feedback here"}},
    "achievements": {{"score": 5,  "max": 10, "feedback": "your feedback here"}}
  }},
  "summary": "2-3 sentence overall summary here.",
  "top_strengths": ["strength 1", "strength 2", "strength 3"],
  "critical_gaps": ["gap 1", "gap 2", "gap 3"]
}}

Resume:
{resume}""".format(role=target_role, resume=resume[:3000])

        raw = ask_ai(prompt)
        return jsonify(clean_json(raw))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── /generate-questions ──
@app.route("/generate-questions", methods=["POST"])
def generate_questions():
    try:
        data   = request.json
        role   = data.get("role", "Software Developer")
        level  = data.get("level", "Mid-level")
        skills = data.get("skills", "")
        prompt = (
            "You are an expert technical interviewer.\n"
            "Role: " + role + "\nExperience: " + level + "\nSkills: " + skills + "\n\n"
            "Generate exactly 5 technical, 3 behavioral, 2 scenario questions.\n"
            "Adjust difficulty for " + level + ". Make questions specific to the role and skills.\n\n"
            'Return ONLY valid JSON, no markdown:\n'
            '{"technical":[{"question":"<q>","difficulty":"Easy|Medium|Hard","hint":"<hint>"}],'
            '"behavioral":[{"question":"<q>","framework":"STAR|CAR","hint":"<hint>"}],'
            '"scenario":[{"question":"<q>","context":"<context>","hint":"<hint>"}]}'
        )
        raw = ask_ai(prompt)
        return jsonify(clean_json(raw))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── /interview-questions ──
@app.route("/interview-questions", methods=["POST"])
def interview_questions():
    try:
        data  = request.json
        role  = data.get("target_role", "Software Developer")
        level = data.get("level", "Mid-level")
        prompt = (
            "Generate 15 interview questions for a " + level + " " + role + ".\n"
            'Return JSON ONLY: {"questions":[{"id":1,"type":"Technical|Behavioral|Situational",'
            '"question":"<q>","framework":"<framework>","sample_answer":"<answer>"}]}\n'
            "Mix: 6 technical, 5 behavioral, 4 situational."
        )
        raw = ask_ai(prompt)
        return jsonify(clean_json(raw))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── /roadmap ──
@app.route("/roadmap", methods=["POST"])
def roadmap():
    try:
        data    = request.json
        current = data.get("current_role", "")
        target  = data.get("target_role", "")
        prompt = (
            "Career roadmap. Current: " + (current or "Not specified") + ". Target: " + target + ".\n"
            'Return JSON ONLY: {"skill_gaps":["g1","g2","g3","g4","g5"],'
            '"milestones":[{"month":"Month 1-2","title":"<t>","tasks":["t1","t2"],"outcome":"<o>"}],'
            '"total_timeline":"<X months>","immediate_actions":["a1","a2","a3"]}\n'
            "Include 5 milestones covering 12 months."
        )
        raw = ask_ai(prompt)
        return jsonify(clean_json(raw))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── /courses ──
@app.route("/courses", methods=["POST"])
def courses():
    try:
        data = request.json
        role = data.get("target_role", "")
        gaps = data.get("skill_gaps", [])
        prompt = (
            "Recommend 8 courses for " + role + ". Gaps: " + (", ".join(gaps) if gaps else "general") + ".\n"
            'Return JSON ONLY: {"courses":[{"title":"<t>","platform":"<p>","skill":"<s>",'
            '"level":"Beginner|Intermediate|Advanced","duration":"<d>","priority":"High|Medium|Low","url_hint":"<search>"}]}'
        )
        raw = ask_ai(prompt)
        return jsonify(clean_json(raw))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── /upload-chat ──
@app.route("/upload-chat", methods=["POST"])
def upload_chat():
    try:
        target_role  = request.form.get("target_role", "Software Developer")
        messages_raw = request.form.get("messages", "[]")
        messages     = json.loads(messages_raw)
        file_context = ""
        if "file" in request.files:
            f = request.files["file"]
            if f.filename:
                file_context = extract_text(f)
        system = (
            "You are a professional technical interviewer for " + target_role + ".\n" +
            ("Candidate resume: " + file_context[:1000] + "\n" if file_context else "") +
            "Ask one tailored question at a time. Give brief feedback then ask the next question."
        )
        if not messages:
            result = ask_ai(system + "\n\nIntroduce yourself briefly and ask the first interview question.")
        else:
            history = "\n".join([("User: " if m["role"] == "user" else "AI: ") + m["content"] for m in messages[:-1]])
            last    = messages[-1]["content"]
            result  = ask_ai(system + "\n\nConversation:\n" + history + "\n\nUser: " + last + "\n\nAI:")
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── /chat ──
@app.route("/chat", methods=["POST"])
def chat():
    try:
        data           = request.json
        messages       = data.get("messages", [])
        resume_context = data.get("resume_context", "")
        role           = data.get("target_role", "")
        history        = "\n".join([("User: " if m["role"] == "user" else "AI: ") + m["content"] for m in messages[:-1]])
        last           = messages[-1]["content"] if messages else "Hello"
        prompt = (
            "You are CareerPilot AI, an expert career advisor.\n" +
            ("Target role: " + role + "\n" if role else "") +
            ("Resume: " + resume_context[:600] + "\n" if resume_context else "") +
            "\nConversation:\n" + history +
            "\nUser: " + last + "\nAI:"
        )
        return jsonify({"result": ask_ai(prompt)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/.well-known/appspecific/com.chrome.devtools.json")
def devtools():
    return "", 204

if __name__ == "__main__":
    app.run(debug=True, port=5000)
