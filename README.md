
# 🩸 LeukNet – Blood Cell Classification System

**AI-powered blood cell image classification platform.**

LeukNet is a web-based application designed to support blood cell image analysis using deep learning. It combines a ResNet50-based classification model with a React frontend and FastAPI backend to provide an integrated image analysis platform.

---

## 🚀 Features

- **AI-powered classification:** Deep learning-based blood cell image classification.
- **Image analysis:** Upload microscopy images for automated analysis.
- **PDF processing:** Supports PDF documents containing images, where configured.
- **User authentication:** Secure registration and login.
- **Patient management:** Organize patient records.
- **Analysis history:** Access previous analysis sessions.
- **Reports:** Generate and manage analysis reports.
- **Administration:** Manage application settings and users.

---

## 🛠️ Technology Stack

| Component | Technology |
|---|---|
| Frontend | React, Vite |
| Backend | Python, FastAPI |
| Machine Learning | TensorFlow Lite |
| Model Architecture | ResNet50 |
| Database | PostgreSQL |
| Database Hosting | Supabase |
| Model Hosting | Hugging Face |
| Frontend Hosting | Cloudflare Pages |
| Backend Hosting | Render |
| Version Control | Git, GitHub |

---

## 🏗️ System Architecture

```text
                  USER
                   |
                   v
          React + Vite Frontend
             Cloudflare Pages
                   |
                   | REST API
                   v
             FastAPI Backend
                 Render
                   |
          +--------+--------+
          |                 |
          v                 v
    TensorFlow Lite     PostgreSQL
     ResNet50 Model      Supabase
          |
          v
    Image Classification
          |
          v
    Results and Reports
          |
          v
       Frontend
```

---

## 📂 Project Structure

```text
main/
│
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── patients.py
│   │   │   ├── predict.py
│   │   │   ├── reports.py
│   │   │   ├── sessions.py
│   │   │   ├── settings.py
│   │   │   └── verify.py
│   │   │
│   │   ├── auth.py
│   │   ├── config.py
│   │   ├── database.py
│   │   └── ml.py
│   │
│   ├── main.py
│   └── requirements.txt
│
├── front_end/
│   ├── public/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
│
└── README.md
```

*This is an overview of the main project components.*

---

## ⚙️ Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/lockey815/main.git
cd main
```

### 2. Backend Setup

Navigate to the backend directory:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate the environment.

**Windows:**

```bash
venv\Scripts\activate
```

**Linux/macOS:**

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the backend directory.

Example configuration:

```env
DATABASE_URL=your_postgresql_connection_string
SECRET_KEY=your_secure_secret_key

ADMIN_EMAIL=your_admin_email
ADMIN_PASSWORD=your_admin_password

HF_MODEL_REPO=Lockey815/LeukNet-ResNet50
HF_MODEL_FILENAME=leuknet_float16.tflite
HF_MODEL_REVISION=main

TFLITE_NUM_THREADS=1
```

Use the exact variable names expected by your backend configuration.

**Important:** Never upload your actual database credentials, passwords, or secret keys to GitHub.

### 4. Start the Backend

From the `backend` directory:

```bash
uvicorn main:app --reload --port 8000
```

Backend documentation:

```text
http://localhost:8000/docs
```

Health endpoint:

```text
http://localhost:8000/api/health
```

### 5. Frontend Setup

Open another terminal and navigate to the frontend:

```bash
cd front_end
```

Install dependencies:

```bash
npm install
```

Create a `.env` file:

```env
VITE_API_URL=http://localhost:8000
```

Start the frontend:

```bash
npm run dev
```

The frontend will normally run at:

```text
http://localhost:5173
```

Build for production:

```bash
npm run build
```

---

## 🧠 Machine Learning Model

LeukNet uses a ResNet50-based deep learning model for blood cell image classification.

The model is hosted on Hugging Face.

**Model Repository:**

[Lockey815/LeukNet-ResNet50](https://huggingface.co/Lockey815/LeukNet-ResNet50)

The deployed model uses TensorFlow Lite to reduce model storage requirements and support more efficient deployment.

### Model Configuration

| Variable | Description |
|---|---|
| `HF_MODEL_REPO` | Hugging Face model repository |
| `HF_MODEL_FILENAME` | Model filename |
| `HF_MODEL_REVISION` | Model repository revision |
| `TFLITE_NUM_THREADS` | Inference thread count |

---

## 🌐 Deployment

LeukNet uses the following services:

| Platform | Purpose |
|---|---|
| [Cloudflare Pages](https://pages.cloudflare.com/) | Frontend hosting |
| [Render](https://render.com/) | Backend hosting |
| [Supabase](https://supabase.com/) | PostgreSQL database |
| [Hugging Face](https://huggingface.co/) | Model hosting |

### Backend Deployment – Render

Configure the Render service:

**Root Directory**

```text
backend
```

**Build Command**

```bash
pip install -r requirements.txt
```

**Start Command**

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Configure all required environment variables in the Render dashboard.

### Frontend Deployment – Cloudflare Pages

**Build Command**

```bash
npm run build
```

**Build Output Directory**

```text
dist
```

Set the production environment variable:

```env
VITE_API_URL=https://your-backend-url.onrender.com
```

Replace the example URL with your actual backend URL.

Ensure that the backend CORS configuration allows your deployed frontend domain.

---

## 🔍 API Documentation

FastAPI provides interactive API documentation.

| Endpoint | Purpose |
|---|---|
| `/` | API information |
| `/docs` | Swagger API documentation |
| `/openapi.json` | OpenAPI specification |
| `/api/health` | Backend and model health status |

The health endpoint reports whether the machine learning model has initialized successfully.

---

## 🔐 Security

- Store sensitive credentials in environment variables.
- Never commit `.env` files.
- Use strong production secret keys.
- Restrict CORS to trusted frontend domains.
- Use HTTPS for production communication.
- Protect authenticated endpoints and sensitive records.

---

## ⚠️ Disclaimer

LeukNet is a software and machine learning project intended to support blood cell image analysis and research.

Its predictions should not be considered a standalone medical diagnosis or a replacement for professional laboratory evaluation and clinical judgment.

Appropriate validation is required before any clinical application.

---

## 👨‍💻 Developer

**LeukNet Development Team**

GitHub: [@lockey815](https://github.com/lockey815)

---

**Built with React, FastAPI, TensorFlow Lite and PostgreSQL.**
