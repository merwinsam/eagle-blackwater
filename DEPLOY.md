# 🦅 Eagle by Blackwater — Deployment Guide
### Private web access for Merwin & Sherwin only

---

## Overview

The cleanest way to deploy Eagle privately is **Streamlit Community Cloud** — it's free, takes ~10 minutes, and gives you a private shareable URL. Only people you invite can access it.

---

## Step 1 — Push Eagle to a Private GitHub Repo

You need a GitHub account. If you don't have one, sign up at github.com.

**1a. Create a new PRIVATE repository**
- Go to github.com → New repository
- Name it `eagle-blackwater`
- Set visibility to **Private**
- Don't initialize with README

**1b. Push your local files to GitHub**

Open Terminal inside your `eagle/` folder:

```bash
cd /Users/merwinsamuel/Desktop/eagle

git init
git add .
git commit -m "Initial Eagle deployment"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/eagle-blackwater.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username.

---

## Step 2 — Handle Secrets Securely

**Do NOT push your `.env` file to GitHub.** Your API keys must be kept secret.

Make sure `.env` is in `.gitignore`:

```bash
echo ".env" >> .gitignore
echo "eagle_log.csv" >> .gitignore
git add .gitignore
git commit -m "Add gitignore"
git push
```

Your API keys will be added to Streamlit Cloud as **Secrets** in Step 3.

---

## Step 3 — Deploy on Streamlit Community Cloud

**3a. Sign up / log in**
- Go to **share.streamlit.io**
- Sign in with your GitHub account

**3b. Create a new app**
- Click **"New app"**
- Select your repository: `eagle-blackwater`
- Branch: `main`
- Main file path: `app.py`
- Click **"Advanced settings"**

**3c. Add your API keys as Secrets**

In the **Secrets** box, paste this (replace with your actual keys):

```toml
FMP_API_KEY = "7f79e8b2abf53bdddc8e39c4a4118e81"
OPENAI_API_KEY = "sk-proj-your-openai-key-here"
```

Click **Save** then **Deploy**.

**3d. Update `config.py` to read from Streamlit secrets**

Replace the top of `config.py` with this so it works both locally (from `.env`) and on the cloud (from Streamlit secrets):

```python
import os
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

def _get(key):
    # Try Streamlit secrets first (cloud), then env (local)
    try:
        return st.secrets[key]
    except:
        return os.getenv(key, "")

FMP_API_KEY  = _get("FMP_API_KEY")
OPENAI_API_KEY = _get("OPENAI_API_KEY")
```

Commit and push this change:

```bash
git add config.py
git commit -m "Use Streamlit secrets for cloud deployment"
git push
```

Streamlit Cloud will automatically redeploy.

---

## Step 4 — Restrict Access to Only You and Sherwin

Streamlit Community Cloud has built-in viewer access control.

**4a. After deployment:**
- Go to your app dashboard on share.streamlit.io
- Click the **⋮ menu** → **Settings** → **Sharing**
- Set **"Who can view this app"** to **"Only specific people"**
- Add your email and Sherwin's email
- Save

**4b. Anyone else who visits the URL will be blocked at the Streamlit level**, before they even see the Eagle login screen. You have two layers of security:
1. Streamlit Cloud access control (email-based)
2. Eagle's own login screen (username + password)

---

## Step 5 — Access Your App

After deployment your app will be live at:
```
https://YOUR_USERNAME-eagle-blackwater-app-XXXX.streamlit.app
```

Share this URL with Sherwin. Both of you log in with your credentials:

| User | Username | Password |
|------|----------|----------|
| Merwin | `merwinsam01` | `Merwin123` |
| Sherwin | `sherwinsam96` | `Sherwin123` |

---

## Updating the App Later

Any time you push changes to GitHub, Streamlit Cloud auto-redeploys:

```bash
# Make your changes, then:
git add .
git commit -m "Update Eagle"
git push
```

---

## Alternative: Deploy on a VPS (More Control)

If you want more control or the app gets heavier, you can deploy on a $5/month **DigitalOcean Droplet** or **AWS EC2 t2.micro**:

```bash
# On the server:
git clone https://github.com/YOUR_USERNAME/eagle-blackwater.git
cd eagle-blackwater
pip install -r requirements.txt

# Create .env with your keys
echo "FMP_API_KEY=your_key" > .env
echo "OPENAI_API_KEY=your_key" >> .env

# Run with nohup so it stays alive
nohup streamlit run app.py --server.port 8501 --server.headless true &
```

Then point a domain at your server IP, and use **Nginx** as a reverse proxy with **password protection** at the server level for an extra security layer.

For the VPS route, reach out — happy to walk through the Nginx config.

---

## Quick Summary

| Step | What to do |
|------|-----------|
| 1 | Create private GitHub repo, push code |
| 2 | Add `.env` to `.gitignore` |
| 3 | Deploy on share.streamlit.io, add API keys as Secrets |
| 4 | Set viewer access to specific emails only |
| 5 | Share URL with Sherwin, both log in |

Total time: ~15–20 minutes.
