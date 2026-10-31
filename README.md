# LeukNet - FastAPI + React

AI-assisted blood-smear screening: sign-in, patient register, LeukNet Assistant (drag-and-drop analysis with a
review-then-save step), Reports Manager with Quick View / print / PDF, QR verification and facility branding.

```
leuknet/
├── backend/                       <- FastAPI (deploys to Hugging Face Spaces)
│   ├── main.py                    <- app entry point, CORS, auth-protected routers
│   ├── requirements.txt  Dockerfile  README.md(HF header)  .env.example  .gitattributes
│   ├── app/
│   │   ├── config.py database.py models.py schemas.py auth.py qr.py pdf.py
│   │   ├── ml.py                  <- model from config.json, preprocessing, tiling, blast counting, checks
│   │   ├── analysis.py            <- totals, acute/chronic rule, summaries (Mistral or template)
│   │   └── routers/ auth predict sessions patients reports verify settings
│   ├── model/
│   │   ├── config.json  metadata.json        (included)
│   │   └── model.weights.h5                  <- !!! YOU copy your 204 MB file here !!!
│   ├── scripts/ calibrate.py create_user.py
│   └── tests/test_e2e.py          <- runs without your weights (random weights)
└── frontend/                      <- React + Vite (deploys to Vercel)
    └── src/ services/api.js (Axios) · context/ · components/ · pages/
            Welcome About Login Dashboard PatientRegister Assistant ReportsManager ReportPage Settings Verify
```

## 1. Run locally (Debian 13, VS Code)

```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip git git-lfs curl nodejs npm
code leuknet
```

**Place the weights:** copy `model.weights.h5` into `backend/model/` (next to `config.json` and `metadata.json`).

```bash
cp ~/Downloads/model.weights.h5 backend/model/ && ls -lh backend/model   # ~204M
```

**Backend**
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip && pip install -r requirements.txt
cp .env.example .env        # then edit: ADMIN_EMAIL, ADMIN_PASSWORD, SECRET_KEY
uvicorn main:app --reload --port 8000
```
Check http://localhost:8000/api/health -> `"model_loaded": true`. API docs: http://localhost:8000/docs.
The account in `ADMIN_EMAIL` / `ADMIN_PASSWORD` is created on startup. More accounts:
`python scripts/create_user.py nurse@clinic.org 'a-strong-password'`.

**Frontend**
```bash
cd frontend && cp .env.example .env && npm install && npm run dev      # http://localhost:5173
```

**Tests (no weights needed):** `cd backend && pip install pytest && pytest -q`

## 2. Calibrate two things config.json cannot tell us

`config.json` has no rescaling layer and no class names, so (a) the pixel scaling used in training and (b) which
output neuron means "blast" must be set by you. Put ~20+ images you are sure about in `calib/blast/` and
`calib/non_blast/`, then:

```bash
cd backend && source .venv/bin/activate
python scripts/calibrate.py ../calib --blast-folder blast
```
It prints the best `PREPROCESS_MODE` and `BLAST_CLASS_INDEX`; copy both lines into `backend/.env` and restart.
Wrong values give confident but wrong results, so do not skip this.

## 3. How the Chapter 4.3 workflow is implemented

1. **Welcome page** (Get Started / About) -> **sign in** with email + password.
2. **Dashboard** with four module cards.
3. **Patient Register**: Add Patient form (Save Details), table with entries-per-page, search, sort, Edit/Delete.
4. **LeukNet Assistant**: tab *File uploader* (choose patient, drag & drop up to 8 JPEG/PNG/PDF files, previews,
   Process) -> tab *LeukNet Tools* (`Processed k / N samples...`, one card per sample with Original vs Analysed
   image and a "n Blast Cells" badge) -> **Results** table (Uploaded Sample Size, Total Blast Cells, Foreign
   Objects) + **Results Report** text -> **New Session** / **Save Results**.
5. **Save Results** creates the report (UUID + QR token). Nothing is saved before the pathologist reviews it,
   and the report is built from server-held results, so a client cannot forge findings.
6. **Reports Manager**: table, **Quick View**, **PDF** (server-generated), **Print / Preview**, Delete, CSV export.
7. **QR verification** `/verify/<token>`: public "Report is Valid" page with the report's details.
8. **Settings**: facility name, address, contacts, logo, report footer; applied to every report.

Details that need your attention:

- **Blast count = suspected blast regions.** The retrained model classifies whole images, so each smear is cut
  into model-sized tiles (read from config.json), empty background is skipped, and tiles with blast probability
  >= `BLAST_PROB_THRESHOLD` are counted and boxed in red. It is not an exact per-cell count (that needs a detector).
- **Foreign objects is a heuristic**, not a model output: tiles with texture but almost no Wright/Giemsa stain
  colours (dust, fibres, debris) are counted, boxed in amber and excluded from blast classification. Validate it on
  your images; turn it off with `FOREIGN_OBJECT_CHECK=false`.
- **Unknown** is returned for blurred images (`BLUR_THRESHOLD`) and images with almost no stained cells
  (`MIN_STAIN_FRACTION`) such as unrelated photos or greyscale images. Tune on your images.
- **Acute / chronic rule**: the report states that more than 15 blasts = acute lymphoblastic leukemia and fewer =
  chronic. It is implemented as `ACUTE_BLAST_THRESHOLD=15` (0 turns it off). It is applied to tile counts, not
  cell counts, and is not a validated clinical criterion - treat that wording with caution.
- **Mistral summaries** are used when `MISTRAL_API_KEY` is set (Mistral's free tier may be enough; check its
  current limits). Only counts are sent - never names, contacts or images. Output containing numbers that are not
  in the facts is rejected, and any failure falls back to a built-in template. Not tested against the live API.
- **PDF input**: each PDF page (up to `MAX_PDF_PAGES`) becomes one sample.
- **Verification page** shows patient name, age, gender and result (as in the report). Set
  `VERIFY_SHOW_FULL_DETAILS=false` to show initials only.

## 4. API summary

Public: `POST /api/auth/login`, `GET /api/verify/{token}`, `GET /api/health`. Everything else needs `Authorization: Bearer <token>`.

| Method | Path | Notes |
|---|---|---|
| POST | `/api/predict` | multipart `files` (+ optional `session_id` to add to a session); returns findings + running totals |
| POST | `/api/sessions/{id}/summarize` | final totals + Results Report text (Mistral or template) |
| DELETE | `/api/sessions/{id}` | New Session |
| GET/POST | `/api/patients` · GET/PUT/DELETE `/api/patients/{id}` | CRUD; delete cascades to reports |
| POST | `/api/reports` | Save Results: `{patient_id, session_id}` -> report with UUID + QR |
| GET | `/api/reports`, `/api/reports/{id}`, `/{id}/pdf`, `/{id}/qr.png` | |
| DELETE | `/api/reports/{id}` | |
| GET/PUT | `/api/settings` | facility branding |

## 5. Free deployment: Hugging Face Spaces (backend) + Vercel (frontend)

### Backend -> Hugging Face Space (Docker)
1. huggingface.co -> **New Space** -> SDK **Docker** -> blank -> CPU basic (free).
2. Push the contents of `backend/` as the Space root (Git LFS is needed for the 204 MB weights):
```bash
git lfs install
git clone https://huggingface.co/spaces/YOUR_HF_USERNAME/leuknet-api && cd leuknet-api
cp -r ../leuknet/backend/. .
git add -A && git commit -m "LeukNet API" && git push      # .gitattributes already tracks *.h5 with LFS
```
3. Space -> **Settings -> Variables and secrets**:

| Name | Type | Value |
|---|---|---|
| `SECRET_KEY` | Secret | long random string (`python -c "import secrets; print(secrets.token_urlsafe(48))"`) |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Secret | your first account |
| `DATABASE_URL` | Secret | Postgres URL (see below) |
| `MISTRAL_API_KEY` | Secret | optional |
| `CORS_ORIGINS`, `FRONTEND_URL` | Variable | `https://YOUR-APP.vercel.app` |
| `PREPROCESS_MODE`, `BLAST_CLASS_INDEX` | Variable | from calibration |

API URL: `https://YOUR_HF_USERNAME-leuknet-api.hf.space`.

**Persistence:** a free Space's disk is wiped on rebuild/restart, so SQLite data would be lost. Create a free hosted
Postgres (e.g. Neon or Supabase - check current free limits) and put its URL in `DATABASE_URL`
(`postgresql://user:pass@host/db?sslmode=require`). Tables are created on startup. Free Spaces sleep when idle, so
the first request after a pause is slow.

### Frontend -> Vercel
1. Push `frontend/` to GitHub, import it in Vercel (Vite is auto-detected).
2. Environment variable `VITE_API_URL` = your Space URL.
3. After deploying, put the Vercel URL into the Space's `CORS_ORIGINS` and `FRONTEND_URL` and restart the Space
   (QR codes embed `FRONTEND_URL`). `vercel.json` rewrites all routes so `/verify/<token>` works.

## 6. Before real patient data

Accounts and bearer-token auth are included, but this is still a student-built system: use a strong `SECRET_KEY`,
HTTPS only, a managed database with backups, and get a data-protection review (e.g. Uganda's Data Protection and
Privacy Act, 2019). There is no password-reset or user-management screen (use `scripts/create_user.py`). Model
output is a screening aid and must be reviewed by a qualified pathologist or hematologist.
