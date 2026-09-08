# Sierra ADLC Framework - FREE HuggingFace Spaces Deployment

**🎉 Zero Cost Deployment using HF Spaces Gradio SDK (Free Tier)**

---

## ⚡ Quick Start (3 Minutes)

### Step 1: Create HuggingFace Space (Free Tier)

1. Go to https://huggingface.co/spaces
2. Click **"Create new Space"**
3. **Fill in:**
   - Space name: `adlc` (or any name)
   - License: `mit`
   - **Space SDK: `Gradio`** ← THIS IS FREE
   - Space hardware: **CPU basic** ← FREE
   - Private: No (public)

4. Click **"Create Space"** → Wait 10 seconds

Your Space URL:
```
https://huggingface.co/spaces/YOUR_USERNAME/adlc
```

---

### Step 2: Push Code to Your Space

```bash
# Navigate to project
cd /Users/renukaoladri/Downloads/sierra_proj

# Configure git
git config user.email "your-email@example.com"
git config user.name "Your Name"

# Add all files
git add .

# Commit
git commit -m "Deploy Sierra ADLC Framework - FREE Gradio SDK"

# Push to HuggingFace
git push https://huggingface.co/spaces/YOUR_USERNAME/adlc main
```

**When prompted for credentials:**
- Username: Your HuggingFace username
- Password: Your HuggingFace API token from https://huggingface.co/settings/tokens

---

### Step 3: Add Your API Key (Secret)

1. Go to your Space: `https://huggingface.co/spaces/YOUR_USERNAME/adlc`
2. Click **Settings** ⚙️ (top right)
3. Scroll to **"Repository secrets"**
4. Click **"Add secret"**
   - Name: `OPENROUTER_API_KEY`
   - Value: Your OpenRouter API key from https://openrouter.ai/
5. Click **"Add secret"**

---

### Step 4: Done! ✅

- Space will auto-build (takes 1-2 minutes)
- Check status indicator (blue "Running" = live)
- Access demo at your Space URL

---

## 💰 Cost Comparison

| Deployment | Cost | Build Time | Cold Start |
|---|---|---|---|
| **HF Spaces (Gradio SDK)** ⭐ | **FREE** | 1-2 min | < 5 sec |
| HF Spaces (Docker) | $0.50/day | 2-5 min | < 10 sec |
| AWS/GCP | $10-50/day | Variable | Variable |
| Local Machine | $0 | N/A | N/A |

✅ **Recommendation:** Use Gradio SDK for free public demo

---

## 🔧 File Structure for HF Spaces

Your Space directory should look like this:

```
adlc/
├── app.py                          ← MAIN FILE (HF Spaces reads this)
├── requirements.txt                ← Dependencies
├── skill_models.py
├── skill_parser.py
├── guardrail_engine.py
├── supervisor_model.py
├── database_models.py
├── regression_test_runner.py
├── release_manager.py
├── skills/                         ← YAML skill definitions
│   ├── retention_offer.yaml
│   ├── plan_downgrade.yaml
│   ├── pause_service.yaml
│   ├── technical_escalation.yaml
│   └── account_lookup.yaml
├── tests/
│   └── conversations/              ← Test JSON files
├── README.md
└── .gitignore
```

**Important:** HF Spaces looks for `app.py` as entry point!

---

## 📤 Pushing to Your GitHub Repo

To also push to GitHub (https://github.com/oladri-renuka/adlc):

```bash
# Add GitHub as another remote
git remote add github https://github.com/oladri-renuka/adlc.git

# Push to both HF Spaces AND GitHub
git push origin main                    # Push to HF Spaces
git push github main                    # Push to GitHub
```

Or set GitHub as primary:

```bash
# Push to GitHub
git push https://github.com/oladri-renuka/adlc.git main

# Then link HF Spaces to GitHub repo in Space settings
# Settings → "Link to repository" → Select your GitHub repo
```

---

## ✨ What You Get (FREE)

✅ Live Gradio interface  
✅ Real Claude API calls (you pay for API, not hosting)  
✅ All 5 ADLC components working  
✅ Automatic HTTPS + SSL  
✅ Public URL to share  
✅ Git version control  
✅ Auto-rebuild on push  
✅ No credit card needed  
✅ No server management  

---

## 🆘 Troubleshooting

### "OPENROUTER_API_KEY not found"
**Fix:** Restart Space after adding secret (takes 30 sec)

### "ModuleNotFoundError"
**Fix:** Add to `requirements.txt`, commit, push - rebuilds automatically

### "Space stopped running"
**Fix:** Click "Restart this Space" in Settings

### "App takes too long to load"
**Fix:** First load caches dependencies (normal)

### "API calls too slow"
**Fix:** Claude API is slow (2-3 sec normal). Use Haiku model for faster responses.

---

## 🚀 Going From Free to Production

When ready for production:

| Feature | Free | Paid |
|---|---|---|
| Compute | CPU basic | GPU/better CPU |
| Uptime | Community | Guaranteed |
| Private | Not available | ✅ Available |
| Custom domain | No | ✅ Yes |
| Storage | 100GB | More |
| Bandwidth | Limited | Unlimited |

For most demos, **free tier is perfect!**

---

## 📝 Example Deployment Commands

**Complete deployment in 5 commands:**

```bash
cd /Users/renukaoladri/Downloads/sierra_proj

# 1. Initialize git
git config user.email "you@example.com"
git config user.name "Your Name"

# 2. Add files
git add .

# 3. Commit
git commit -m "Deploy Sierra ADLC Framework"

# 4. Add HF Spaces remote
git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/adlc.git

# 5. Push
git push hf main
```

Then add API key in Space settings and you're done!

---

## 📊 Monitor Your Space

1. **Build logs:** Settings → "View logs"
2. **Runtime output:** Space interface shows print statements
3. **Restart:** Settings → "Restart this Space"
4. **Rebuild:** Settings → "Rebuild from source"

---

## 🔐 Keep API Key Safe

✅ **DO:**
- Store in HF Spaces "Repository secrets"
- Use `.env` file locally (git-ignored)
- Rotate keys periodically

❌ **DON'T:**
- Commit API keys to git
- Share Space URL if key is exposed
- Use same key for multiple spaces

---

## 💡 Tips & Tricks

### Test Locally First
```bash
python app.py
# Opens on http://localhost:7860
```

### Push Updates Instantly
```bash
# Make changes
nano app.py

# Push to HF Spaces
git add app.py
git commit -m "Update: better UI"
git push hf main

# Space auto-rebuilds in 1-2 minutes
```

### View Live Logs
```bash
# In HF Spaces settings, click "View logs"
# See real-time output as users interact
```

---

## 🎯 Success Checklist

- [ ] Created Space on HuggingFace (FREE Gradio SDK)
- [ ] Added OPENROUTER_API_KEY secret
- [ ] Pushed code from GitHub
- [ ] Space shows "Running" (blue indicator)
- [ ] Can access demo at Space URL
- [ ] Skill detection works
- [ ] Guardrail engine responds
- [ ] Supervisor model validates
- [ ] No errors in logs

---

## 📞 Support Resources

- **HF Spaces Docs:** https://huggingface.co/docs/hub/spaces
- **Gradio Docs:** https://www.gradio.app/
- **OpenRouter API:** https://openrouter.ai/docs
- **GitHub Issues:** https://github.com/oladri-renuka/adlc/issues

---

**🎉 You now have a FREE production-ready demo!**

Share your Space URL:
```
https://huggingface.co/spaces/YOUR_USERNAME/adlc
```

---

**Framework:** Sierra ADLC v1.1.0  
**Deployment:** FREE HuggingFace Spaces (Gradio SDK)  
**Status:** ✅ Production-Ready  
**Cost:** $0 (hosting) + Claude API usage only
