"""End-to-end API test. Builds a model from model/config.json with RANDOM weights (so it runs without your
real model.weights.h5) and exercises login, sessions, PDF upload, Mistral (mocked), reports, PDF export and QR verify.
Run:  cd backend && pip install pytest && pytest -q
Predictions are meaningless here; this checks the plumbing, not model accuracy."""
import io, os, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp(prefix="leuknet_test_"))
os.environ.update(
    MODEL_CONFIG_PATH=str(ROOT / "model/config.json"), MODEL_WEIGHTS_PATH=str(TMP / "model.weights.h5"),
    MODEL_METADATA_PATH=str(ROOT / "model/metadata.json"), DATABASE_URL=f"sqlite:///{TMP}/test.db",
    FRONTEND_URL="https://leuknet.example.vercel.app", KERAS_BACKEND="tensorflow", TF_CPP_MIN_LOG_LEVEL="3",
    SECRET_KEY="test-secret-test-secret-test-secret", ADMIN_EMAIL="Doc@Hospital.org", ADMIN_PASSWORD="supersecret1",
    MISTRAL_API_KEY="fake", ACUTE_BLAST_THRESHOLD="3", BLAST_PROB_THRESHOLD="0.0",  # 0.0 => every tile flagged
)
sys.path.insert(0, str(ROOT))

import json
import keras
cfg = json.loads((ROOT / "model/config.json").read_text())
keras.saving.deserialize_keras_object(cfg).save_weights(str(TMP / "model.weights.h5"))

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from fastapi.testclient import TestClient
from main import app
import app.analysis as analysis

rng = np.random.default_rng(0)
def png(img, fmt="PNG"):
    b = io.BytesIO(); img.save(b, fmt); b.seek(0); return b

def smear(w, h, foreign=False):
    im = Image.new("RGB", (w, h), (238, 214, 226)); d = ImageDraw.Draw(im)
    for _ in range(40):
        x, y = rng.integers(10, w - 10), rng.integers(10, h - 10); r = int(rng.integers(8, 16))
        d.ellipse([x-r, y-r, x+r, y+r], fill=(90 + int(rng.integers(0, 20)), 40, 140), outline=(60, 20, 100))
    if foreign:  # grey/green fibre-like debris with texture in bottom-right
        patch = rng.integers(70, 110, (140, 140, 3), dtype=np.uint8); patch[..., 1] += 25
        im.paste(Image.fromarray(patch), (w - 150, h - 150))
    return im.filter(ImageFilter.GaussianBlur(0.6))

small = smear(128, 128)
big = smear(700, 500, foreign=True)
blurry = smear(400, 400).filter(ImageFilter.GaussianBlur(25))
photo = Image.fromarray(rng.integers(0, 255, (300, 300), dtype=np.uint8)).convert("RGB").convert("L").convert("RGB")  # gray noise
pdfimg = smear(500, 400)

def test_full_flow():
    with TestClient(app) as c:

        # ---- auth ----
        assert c.get("/api/patients").status_code == 401
        assert c.post("/api/auth/login", json={"email": "doc@hospital.org", "password": "wrong"}).status_code == 401
        t = c.post("/api/auth/login", json={"email": "DOC@hospital.org", "password": "supersecret1"}); assert t.status_code == 200, t.text
        H = {"Authorization": "Bearer " + t.json()["access_token"]}
        assert c.get("/api/auth/me", headers=H).json()["email"] == "doc@hospital.org"
        assert c.get("/api/health").status_code == 200 and c.get("/api/verify/x").status_code == 200   # public
        assert c.get("/api/patients", headers={"Authorization": "Bearer junk"}).status_code == 401

        pid = c.post("/api/patients", headers=H, json={"name": "Matsiko James", "gender": "Male", "age": 12, "contact": "077", "address": "Kampala"}).json()["id"]

        # ---- predict: per-sample calls into one session ----
        r1 = c.post("/api/predict", headers=H, files=[("files", ("big.png", png(big), "image/png"))]); assert r1.status_code == 200, r1.text
        j1 = r1.json(); sid = j1["session_id"]; f = j1["findings"][0]
        print("big:", f["status"], "tiles", f["tiles_analyzed"], "blasts", f["blast_count"], "foreign", f["foreign_objects"], "| original preview:", bool(f["original_image"]))
        assert f["foreign_objects"] >= 1 and f["original_image"]
        r2 = c.post("/api/predict", headers=H, data={"session_id": sid}, files=[("files", ("small.png", png(small), "image/png"))]); assert r2.status_code == 200
        r3 = c.post("/api/predict", headers=H, data={"session_id": sid}, files=[("files", ("blur.png", png(blurry), "image/png")), ("files", ("gray.png", png(photo), "image/png"))])
        fs = {x["filename"]: x for x in r3.json()["findings"]}; print("blur:", fs["blur.png"]["status"], "|", fs["blur.png"]["note"]); print("gray:", fs["gray.png"]["status"], "|", fs["gray.png"]["note"])
        assert fs["blur.png"]["status"] == "unknown" and fs["gray.png"]["status"] == "unknown"
        r4 = c.post("/api/predict", headers=H, data={"session_id": sid}, files=[("files", ("scan.pdf", png(pdfimg, "PDF"), "application/pdf"))]); assert r4.status_code == 200, r4.text
        print("pdf sample:", [(x["filename"], x["status"]) for x in r4.json()["findings"]])
        agg = r4.json()["aggregate"]; print("running aggregate:", {k: agg[k] for k in ("result", "indication", "sample_size", "images_analyzed", "total_blasts", "foreign_objects")})
        assert agg["sample_size"] == 5
        # other user cannot touch the session / unknown session
        assert c.post("/api/predict", headers=H, data={"session_id": "nope"}, files=[("files", ("s.png", png(small), "image/png"))]).status_code == 404
        assert c.post("/api/predict", headers=H, files=[("files", ("x.txt", io.BytesIO(b"hi"), "text/plain"))]).status_code == 415

        # ---- summary with mocked Mistral ----
        calls = []
        def fake_ok(payload, key, timeout):
            calls.append(payload); n = agg["total_blasts"]
            return {"choices": [{"message": {"content": f"The screening flagged {n} suspected blast regions. Please have a pathologist review the result."}}]}
        analysis._mistral_call = fake_ok
        s = c.post(f"/api/sessions/{sid}/summarize", headers=H).json(); print("summary:", s["summary_source"], "|", s["summary"][:90])
        assert s["summary_source"] == "mistral" and "Matsiko" not in str(calls[0]) and "James" not in str(calls[0])
        def fake_bad(payload, key, timeout):  # hallucinated number must be rejected
            return {"choices": [{"message": {"content": "Found 9999 blasts."}}]}
        analysis._mistral_call = fake_bad
        s2 = c.post(f"/api/sessions/{sid}/summarize", headers=H).json(); assert s2["summary_source"] == "template", s2
        def fake_err(payload, key, timeout): raise RuntimeError("boom")
        analysis._mistral_call = fake_err
        s3 = c.post(f"/api/sessions/{sid}/summarize", headers=H).json(); assert s3["summary_source"] == "template"
        print("template summary:", s3["summary"][:140])

        # ---- Save Results -> report ----
        assert c.post("/api/reports", headers=H, json={"patient_id": "nope", "session_id": sid}).status_code == 404
        rep = c.post("/api/reports", headers=H, json={"patient_id": pid, "session_id": sid}); assert rep.status_code == 201, rep.text
        R = rep.json(); print("report:", R["result"], R["indication"], R["total_blasts"], "foreign", R["foreign_objects"], "sample", R["sample_size"], R["images_analyzed"])
        assert all(not x["original_image"] for x in R["findings"])
        assert c.post("/api/reports", headers=H, json={"patient_id": pid, "session_id": sid}).status_code == 404  # session consumed
        assert R["indication"] == "acute" and R["qr_code"].startswith("data:image/png") and R["verify_url"].endswith("/verify/" + R["token"])
        L = c.get("/api/reports", headers=H).json(); assert L[0]["patient_name"] == "Matsiko James"

        # ---- PDF ----
        c.put("/api/settings", headers=H, json={"facility_name": "Mbarara Regional Referral Hospital", "address": "Mbarara", "contact": "0700 000 000", "email": "lab@mrrh.ug", "report_footer": "AI-assisted; review required."})
        p = c.get(f"/api/reports/{R['id']}/pdf", headers=H); assert p.status_code == 200 and p.content[:5] == b"%PDF-", p.status_code
        print("pdf bytes:", len(p.content), p.headers["content-disposition"])

        # ---- verify ----
        v = c.get(f"/api/verify/{R['token']}").json(); print("verify:", v["valid"], v["patient_name"], v["indication"], v["facility_name"])
        assert v["valid"] and v["patient_name"] == "Matsiko James"
        # discard flow
        j = c.post("/api/predict", headers=H, files=[("files", ("small.png", png(small), "image/png"))]).json()
        assert c.delete(f"/api/sessions/{j['session_id']}", headers=H).status_code == 204
        assert c.post(f"/api/sessions/{j['session_id']}/summarize", headers=H).status_code == 404
        assert c.delete(f"/api/patients/{pid}", headers=H).status_code == 204
        assert c.get(f"/api/reports/{R['id']}", headers=H).status_code == 404   # cascade
