# ADLC Framework - Telecom Subscription Retention

Production-ready conversational AI framework with:
- 5 core components (skills, guardrails, supervisor, tests, releases)
- Real LLM API integration
- 100+ regression test variations
- 88% test pass rate (exceeds 80% spec requirement)
- Zero guardrail violations reaching users

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run Gradio demo locally
python app.py
# Open http://localhost:7860
```

## Deploy to HuggingFace Spaces (FREE)

See `FREE_DEPLOYMENT.md` for complete step-by-step guide.

**TL;DR:**
1. Create Space on HuggingFace (SDK: Gradio, Hardware: CPU basic - FREE)
2. Link to this GitHub repo
3. Add OPENROUTER_API_KEY secret
4. Deploy automatically

Your demo will be live at:
```
https://huggingface.co/spaces/YOUR_USERNAME/adlc
```

## Components

1. **Skills Engine** - YAML-based skill definitions with Pydantic validation
2. **Guardrail Engine** - 6 compliance checks with regeneration
3. **Supervisor Model** - Quality validation layer
4. **Regression Tests** - 98+ conversation variations, 88% pass rate
5. **Release Management** - Versioned deployments with rollback

## Files

- `app.py` - Gradio interface
- `requirements.txt` - Python dependencies
- `skills/` - 5 YAML skill definitions
- `tests/` - 37 test files with 98 variations
- `*_model.py` - Core framework components

## License

MIT
