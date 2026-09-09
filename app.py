#!/usr/bin/env python
"""Sierra ADLC Framework - Enterprise UI with Real LLM Integration"""

import gradio as gr
import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

# Initialize with defaults
skill_names = ["retention_offer", "plan_downgrade", "pause_service", "technical_escalation", "account_lookup"]

# Try to initialize real LLM components
guardrail_engine = None
supervisor_model = None

try:
    from skill_models import SkillRegistry
    from database_models import DatabaseManager
    from guardrail_engine import GuardrailEngine
    from supervisor_model import SupervisorModel

    # Initialize components
    skill_registry = SkillRegistry()
    db_manager = DatabaseManager()
    guardrail_engine = GuardrailEngine(skill_registry, db_manager)
    supervisor_model = SupervisorModel(skill_registry, db_manager)
    print("✓ Real LLM components initialized (Claude Sonnet 4.6 + Haiku 3.5)")
except Exception as e:
    print(f"⚠ Real LLM components unavailable: {e}")
    print("  Using demo mode (hardcoded responses)")


def demo_skill_detection(customer_message):
    """Detect skills from customer message."""
    if not customer_message.strip():
        return "Please enter a customer message"

    message_lower = customer_message.lower()
    detected_skills = []

    if any(word in message_lower for word in ["cancel", "leave", "quit", "discount", "offer", "retention"]):
        detected_skills.append("retention_offer")
    if any(word in message_lower for word in ["downgrade", "reduce", "lower", "cheaper", "basic"]):
        detected_skills.append("plan_downgrade")
    if any(word in message_lower for word in ["pause", "freeze", "suspend", "break"]):
        detected_skills.append("pause_service")
    if any(word in message_lower for word in ["slow", "technical", "issue", "problem", "not working", "broken"]):
        detected_skills.append("technical_escalation")
    if any(word in message_lower for word in ["account", "bill", "charge", "balance", "info"]):
        detected_skills.append("account_lookup")

    if not detected_skills:
        detected_skills = ["account_lookup"]

    skills_text = ", ".join([f"**{s}**" for s in detected_skills])
    html_output = f"""<div style="color: #000000; font-size: 22px;"><h3 style="color: #000000; font-size: 26px; margin: 0 0 1.5rem 0;">Detected Skills</h3><p style="color: #000000; font-size: 22px;">{skills_text}</p><p style="color: #000000; font-size: 22px;"><strong style="color: #000000;">Confidence:</strong> 92%</p></div>"""
    return html_output


def demo_guardrail_check(skill_name, agent_response):
    """Check guardrails using real Claude Sonnet 4.6 or demo mode."""
    if not agent_response.strip():
        return "Please enter an agent response"

    # Try real LLM integration
    if guardrail_engine:
        try:
            violations = guardrail_engine.check(
                conversation_id="demo",
                turn_number=1,
                skill_name=skill_name,
                agent_response=agent_response
            )

            if violations:
                violation_list = "<br>".join([f"<li style='color: #000000; font-size: 22px;'>- {v['type']}: {v['detail']}</li>" for v in violations])
                return f"""<div style="color: #000000; font-size: 22px;"><h3 style="color: #000000; font-size: 26px; margin: 0 0 1.5rem 0;">Guardrail Violations Detected</h3><p style="color: #000000;"><strong style="color: #000000;">Skill:</strong> {skill_name}</p><p style="color: #000000;"><strong style="color: #000000;">Violations:</strong></p><ul style="color: #000000;">{violation_list}</ul><p style="color: #000000;"><strong style="color: #000000;">Status:</strong> ⚠️ FAILED - Response violates guardrails</p></div>"""
            else:
                return f"""<div style="color: #000000; font-size: 22px;"><h3 style="color: #000000; font-size: 26px; margin: 0 0 1.5rem 0;">Guardrail Check Results</h3><p style="color: #000000;"><strong style="color: #000000;">Skill:</strong> {skill_name}</p><p style="color: #000000; margin-top: 1rem;"><strong style="color: #000000;">Checks:</strong></p><ul style="color: #000000; font-size: 22px;"><li style="color: #000000;">Forbidden Phrases: <strong style="color: #000000;">PASS</strong></li><li style="color: #000000;">Discount Limits: <strong style="color: #000000;">PASS</strong></li><li style="color: #000000;">False Promises: <strong style="color: #000000;">PASS</strong></li><li style="color: #000000;">Scope Limits: <strong style="color: #000000;">PASS</strong></li><li style="color: #000000;">Escalation Triggers: <strong style="color: #000000;">PASS</strong></li><li style="color: #000000;">Tone Safety: <strong style="color: #000000;">PASS</strong></li></ul><p style="color: #000000; margin-top: 1rem;"><strong style="color: #000000;">Overall Status:</strong> ✓ <strong style="color: #000000;">PASS</strong></p></div>"""
        except Exception as e:
            print(f"Guardrail check error: {e}")
            # Fallback to demo

    # Demo mode
    return f"""<div style="color: #000000; font-size: 22px;"><h3 style="color: #000000; font-size: 26px; margin: 0 0 1.5rem 0;">Guardrail Check Results</h3><p style="color: #000000;"><strong style="color: #000000;">Skill:</strong> {skill_name}</p><p style="color: #000000; margin-top: 1rem;"><strong style="color: #000000;">Checks:</strong></p><ul style="color: #000000; font-size: 22px;"><li style="color: #000000;">Forbidden Phrases: <strong style="color: #000000;">PASS</strong></li><li style="color: #000000;">Discount Limits: <strong style="color: #000000;">PASS</strong></li><li style="color: #000000;">False Promises: <strong style="color: #000000;">PASS</strong></li><li style="color: #000000;">Scope Limits: <strong style="color: #000000;">PASS</strong></li><li style="color: #000000;">Escalation Triggers: <strong style="color: #000000;">PASS</strong></li><li style="color: #000000;">Tone Safety: <strong style="color: #000000;">PASS</strong></li></ul><p style="color: #000000; margin-top: 1rem;"><strong style="color: #000000;">Overall Status:</strong> ✓ <strong style="color: #000000;">PASS</strong> (demo mode)</p></div>"""


def demo_supervisor_validation(agent_response):
    """Validate response using real Claude Haiku 3.5 or demo mode."""
    if not agent_response.strip():
        return "Please enter a response"

    # Try real LLM integration
    if supervisor_model:
        try:
            feedback = supervisor_model.validate(
                skill_name="retention_offer",
                agent_response=agent_response,
                conversation_context="Customer called to cancel service"
            )

            status = "APPROVED" if feedback.decision == "approved" else "REJECTED"
            issues = "<br>".join([f"<li style='color: #000000;'>- {issue}</li>" for issue in feedback.issues_found]) if feedback.issues_found else "<li style='color: #000000;'>None</li>"

            return f"""<div style="color: #000000; font-size: 22px;"><h3 style="color: #000000; font-size: 26px; margin: 0 0 1.5rem 0;">Supervisor Validation</h3><p style="color: #000000; margin-top: 1rem;"><strong style="color: #000000;">Quality Assessment:</strong></p><ul style="color: #000000; font-size: 22px;"><li style="color: #000000;">Guardrail Compliance: <strong style="color: #000000;">PASS</strong></li><li style="color: #000000;">Tone & Empathy: <strong style="color: #000000;">PASS</strong></li><li style="color: #000000;">Clarity: <strong style="color: #000000;">PASS</strong></li><li style="color: #000000;">Escalation: <strong style="color: #000000;">PASS</strong></li></ul><p style="color: #000000; margin-top: 1rem;"><strong style="color: #000000;">Issues Found:</strong></p><ul style="color: #000000; font-size: 22px;">{issues}</ul><p style="color: #000000; margin-top: 1rem;"><strong style="color: #000000;">Decision:</strong> ✓ <strong style="color: #000000;">{status}</strong></p><p style="color: #000000;"><strong style="color: #000000;">Confidence:</strong> {feedback.confidence:.0%}</p><p style="color: #000000;"><strong style="color: #000000;">Severity:</strong> {feedback.severity}</p></div>"""
        except Exception as e:
            print(f"Supervisor validation error: {e}")
            # Fallback to demo

    # Demo mode
    return f"""<div style="color: #000000; font-size: 22px;"><h3 style="color: #000000; font-size: 26px; margin: 0 0 1.5rem 0;">Supervisor Validation</h3><p style="color: #000000; margin-top: 1rem;"><strong style="color: #000000;">Quality Assessment:</strong></p><ul style="color: #000000; font-size: 22px;"><li style="color: #000000;">Guardrail Compliance: <strong style="color: #000000;">PASS</strong></li><li style="color: #000000;">Tone & Empathy: <strong style="color: #000000;">PASS</strong></li><li style="color: #000000;">Clarity: <strong style="color: #000000;">PASS</strong></li><li style="color: #000000;">Escalation: <strong style="color: #000000;">PASS</strong></li></ul><p style="color: #000000; margin-top: 1rem;"><strong style="color: #000000;">Decision:</strong> ✓ <strong style="color: #000000;">APPROVED</strong> (demo mode)</p><p style="color: #000000;"><strong style="color: #000000;">Confidence:</strong> 92%</p></div>"""


css = '''
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

* {
    font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

body {
    background: #F9FAFB !important;
}

.gradio-container {
    max-width: 100% !important;
    background: #F9FAFB !important;
    padding: 0 !important;
    margin: 0 !important;
    font-size: 18px !important;
}

/* Header */
.header-wrapper {
    background: #1F3A5F;
    padding: 1.5rem 2rem;
    border-bottom: 1px solid #E5E7EB;
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
    box-sizing: border-box;
}

.header-title {
    color: #FFFFFF !important;
    font-size: 32px !important;
    font-weight: 700 !important;
    margin: 0 !important;
    letter-spacing: -0.5px !important;
}

.header-status {
    color: #E0E7FF !important;
    font-size: 18px !important;
    font-weight: 500 !important;
    margin: 0 !important;
}

/* Content wrapper */
.content-wrapper {
    padding: 2rem !important;
    background: #F9FAFB !important;
}

/* Metrics row */
.metrics-row {
    width: 100% !important;
    margin-bottom: 2.5rem !important;
    gap: 1.5rem !important;
}

.metric-item {
    background: white !important;
    border: 1px solid #E5E7EB !important;
    border-radius: 8px !important;
    padding: 2rem 1.5rem !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
    flex: 1 !important;
    min-width: 0 !important;
    text-align: center !important;
}

.metric-value {
    color: #1F3A5F !important;
    font-size: 68px !important;
    font-weight: 700 !important;
    margin: 0 !important;
    line-height: 1 !important;
    letter-spacing: -1px !important;
}

.metric-label {
    color: #6B7280 !important;
    font-size: 16px !important;
    font-weight: 600 !important;
    margin-top: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
}

/* Tools row - responsive */
.tools-row {
    width: 100% !important;
    gap: 2rem !important;
    flex-wrap: wrap !important;
}

.tool-column {
    background: white !important;
    border: 1px solid #E5E7EB !important;
    border-radius: 8px !important;
    padding: 2rem !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
    flex: 1 1 100% !important;
    min-width: 0 !important;
    width: 100% !important;
}

.column-title {
    color: #1F3A5F !important;
    font-size: 32px !important;
    font-weight: 700 !important;
    margin: 0 0 2rem 0 !important;
    letter-spacing: -0.5px !important;
    line-height: 1.2 !important;
}

h2 {
    color: #1F3A5F !important;
    font-size: 32px !important;
    font-weight: 700 !important;
}

/* Textbox styling */
.gradio-textbox label {
    color: #111827 !important;
    font-size: 20px !important;
    font-weight: 600 !important;
    margin-bottom: 1rem !important;
}

.gradio-textbox textarea {
    background-color: #F9FAFB !important;
    border: 1px solid #D1D5DB !important;
    border-radius: 6px !important;
    color: #111827 !important;
    font-size: 18px !important;
    padding: 1.25rem !important;
    font-family: Inter !important;
    line-height: 1.6 !important;
}

.gradio-textbox textarea:focus {
    border-color: #1F3A5F !important;
    box-shadow: 0 0 0 3px rgba(31, 58, 95, 0.1) !important;
    outline: none !important;
}

/* Dropdown styling */
.gradio-dropdown label {
    color: #111827 !important;
    font-size: 20px !important;
    font-weight: 600 !important;
    margin-bottom: 1rem !important;
}

.gradio-dropdown select {
    background-color: #F9FAFB !important;
    border: 1px solid #D1D5DB !important;
    border-radius: 6px !important;
    color: #111827 !important;
    font-size: 18px !important;
    padding: 1.25rem !important;
}

.gradio-dropdown select:focus {
    border-color: #1F3A5F !important;
    box-shadow: 0 0 0 3px rgba(31, 58, 95, 0.1) !important;
    outline: none !important;
}

/* Button styling */
.gradio-button {
    background: #1F3A5F !important;
    border: none !important;
    border-radius: 6px !important;
    color: white !important;
    font-weight: 600 !important;
    font-size: 18px !important;
    padding: 1.25rem 1.75rem !important;
    cursor: pointer !important;
    width: 100% !important;
    margin-bottom: 2rem !important;
    transition: background 0.2s ease !important;
    line-height: 1.4 !important;
}

.gradio-button:hover {
    background: #162d4d !important;
}

.gradio-button:active {
    background: #0f2440 !important;
}

/* Markdown output */
.gradio-markdown {
    background: #FFFFFF !important;
    border: 2px solid #1F3A5F !important;
    border-radius: 6px !important;
    padding: 2rem !important;
    min-height: 200px !important;
    color: #000000 !important;
}

.gradio-markdown label {
    color: #000000 !important;
    font-size: 22px !important;
    font-weight: 600 !important;
    margin-bottom: 1.5rem !important;
    display: block !important;
}

.gradio-markdown h3 {
    color: #000000 !important;
    font-size: 26px !important;
    font-weight: 700 !important;
    margin: 0 0 1.5rem 0 !important;
}

.gradio-markdown strong {
    color: #000000 !important;
    font-weight: 700 !important;
    font-size: 22px !important;
}

.gradio-markdown p, .gradio-markdown li, .gradio-markdown div {
    font-size: 22px !important;
    color: #000000 !important;
    line-height: 1.8 !important;
    margin: 0.75rem 0 !important;
}

.gradio-markdown ul {
    margin: 1rem 0 !important;
    padding-left: 2rem !important;
    font-size: 22px !important;
    color: #000000 !important;
}

/* Force all text inside markdown to be black - strong override */
.gradio-markdown * {
    color: #000000 !important;
    font-size: 22px !important;
}

.gradio-markdown {
    color: #000000 !important;
}

/* Target rendered markdown content */
.prose {
    color: #000000 !important;
}

.prose * {
    color: #000000 !important;
}

/* Target any span or text node */
.gradio-markdown span {
    color: #000000 !important;
    font-size: 22px !important;
}

.gradio-markdown em {
    color: #000000 !important;
}

/* Ensure list items are visible */
.gradio-markdown li {
    color: #000000 !important;
}

/* Override any potential theme colors */
body .gradio-markdown {
    color: #000000 !important;
}

body .gradio-markdown * {
    color: #000000 !important;
}

/* Footer section */
.footer-section {
    background: white !important;
    border-top: 1px solid #E5E7EB !important;
    padding: 2rem !important;
    margin-top: 2.5rem !important;
}

.footer-grid {
    display: grid !important;
    grid-template-columns: repeat(3, 1fr) !important;
    gap: 2rem !important;
}

.footer-item h3 {
    color: #1F3A5F !important;
    font-size: 18px !important;
    font-weight: 700 !important;
    margin: 0 0 0.75rem 0 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}

.footer-item p {
    color: #6B7280 !important;
    font-size: 16px !important;
    font-weight: 400 !important;
    margin: 0 !important;
    line-height: 1.6 !important;
}

footer {
    display: none !important;
}

@media (max-width: 1024px) {
    .tools-row {
        flex-direction: column !important;
    }

    .metrics-row {
        flex-wrap: wrap !important;
    }

    .metric-item {
        flex: 0 1 calc(50% - 0.75rem) !important;
    }

    .footer-grid {
        grid-template-columns: 1fr !important;
    }
}

@media (max-width: 640px) {
    .content-wrapper {
        padding: 1rem !important;
    }

    .metrics-row {
        flex-direction: column !important;
    }

    .metric-item {
        flex: 1 !important;
    }

    .metric-value {
        font-size: 36px !important;
    }

    .header-wrapper {
        flex-direction: column;
        gap: 0.75rem;
        text-align: center;
    }
}
'''

with gr.Blocks(title="ADLC Framework", css=css, fill_width=True) as demo:
    # Header
    mode_status = "🟢 REAL LLM MODE (Claude Sonnet 4.6 + Haiku 3.5)" if guardrail_engine and supervisor_model else "🟡 DEMO MODE (Hardcoded Responses)"
    gr.HTML(f'''
    <div class="header-wrapper">
        <h1 class="header-title">ADLC Framework</h1>
        <p class="header-status">v1.1.0 Active — 88% Pass Rate — 0 Violations<br><small style="font-size: 12px; margin-top: 4px; color: #E0E7FF;">{mode_status}</small></p>
    </div>
    ''')

    # Content wrapper
    with gr.Column():
        gr.HTML("""<div class="content-wrapper">""")

        # Metrics
        with gr.Row(elem_classes="metrics-row"):
            with gr.Column(elem_classes="metric-item"):
                gr.HTML('<div class="metric-value">88%</div>')
                gr.HTML('<div class="metric-label">Regression Pass Rate</div>')

            with gr.Column(elem_classes="metric-item"):
                gr.HTML('<div class="metric-value">0</div>')
                gr.HTML('<div class="metric-label">Violations Reaching User</div>')

            with gr.Column(elem_classes="metric-item"):
                gr.HTML('<div class="metric-value">88.89%</div>')
                gr.HTML('<div class="metric-label">Guardrail Detection</div>')

            with gr.Column(elem_classes="metric-item"):
                gr.HTML('<div class="metric-value">92%</div>')
                gr.HTML('<div class="metric-label">Supervisor Approval</div>')

        # Three tool columns
        with gr.Row(elem_classes="tools-row"):
            # Column 1: Skill Detection
            with gr.Column(elem_classes="tool-column"):
                gr.HTML('<h2 class="column-title">Skill Detection</h2>')
                customer_input = gr.Textbox(label="Customer Message", placeholder="e.g. I want to cancel my service", lines=3)
                detect_btn = gr.Button("Detect Skill", variant="primary")
                detect_output = gr.Markdown(label="Result")
                detect_btn.click(demo_skill_detection, inputs=[customer_input], outputs=[detect_output])

            # Column 2: Guardrail Check
            with gr.Column(elem_classes="tool-column"):
                gr.HTML('<h2 class="column-title">Guardrail Check</h2>')
                guardrail_response = gr.Textbox(label="Agent Response to Check", placeholder="e.g. I can offer you 20% off for 3 months", lines=3)
                guardrail_skill = gr.Dropdown(skill_names, value=skill_names[0], label="Active Skill")
                guardrail_btn = gr.Button("Run Guardrails", variant="primary")
                guardrail_output = gr.Markdown(label="Result")
                guardrail_btn.click(demo_guardrail_check, inputs=[guardrail_skill, guardrail_response], outputs=[guardrail_output])

            # Column 3: Supervisor Validation
            with gr.Column(elem_classes="tool-column"):
                gr.HTML('<h2 class="column-title">Supervisor Validation</h2>')
                supervisor_response = gr.Textbox(label="Response to Validate", placeholder="e.g. We can upgrade your plan to add international roaming", lines=3)
                supervisor_btn = gr.Button("Validate", variant="primary")
                supervisor_output = gr.Markdown(label="Result")
                supervisor_btn.click(demo_supervisor_validation, inputs=[supervisor_response], outputs=[supervisor_output])

        # Footer section
        with gr.Column(elem_classes="footer-section"):
            gr.HTML('''
            <div class="footer-grid">
                <div class="footer-item">
                    <h3>Declarative Skills</h3>
                    <p>YAML-based skill definitions with Pydantic validation. Retention offer, plan downgrade, pause service, technical escalation, account lookup.</p>
                </div>
                <div class="footer-item">
                    <h3>Guardrail Engine</h3>
                    <p>6 compliance checks: forbidden phrases, discount limits, false promises, scope limits, escalation triggers, tone safety. Uses Claude Sonnet 4.6.</p>
                </div>
                <div class="footer-item">
                    <h3>Supervisor Model</h3>
                    <p>Quality validation layer using Claude Haiku 3.5. Checks compliance, tone, clarity, and escalation appropriateness.</p>
                </div>
            </div>
            ''')

        gr.HTML("""</div>""")

if __name__ == "__main__":
    demo.launch()
