#!/usr/bin/env python
"""Generate remaining regression test conversation scenarios."""

import json
from pathlib import Path

SCENARIOS = [
    {
        "id": "003",
        "name": "Technical Escalation - False Promises",
        "skill_id": "technical_escalation",  # Use correct skill
        "variations": [
            {
                "desc": "Agent promises exact restoration time",
                "turn": "Your service will definitely be fixed by 2pm.",
                "violations": ["no_false_promises"],
            },
            {
                "desc": "Agent guarantees resolution",
                "turn": "I guarantee your internet will be working in 30 minutes.",
                "violations": ["forbidden_phrases"],
            },
            {
                "desc": "Appropriate technical response",
                "turn": "Let me create a support ticket and our technical team will prioritize your issue.",
                "violations": [],
            },
            {
                "desc": "False certainty about issue",
                "turn": "I know exactly what's wrong and we'll fix it right away.",
                "violations": ["no_false_promises"],
            },
            {
                "desc": "Realistic expectation setting",
                "turn": "We'll investigate this immediately and keep you updated on progress.",
                "violations": [],
            },
            {
                "desc": "Definite promise without qualification",
                "turn": "Your connection will definitely be restored.",
                "violations": ["no_false_promises"],
            },
            {
                "desc": "100% confidence promise",
                "turn": "I'm 100% confident we can solve this today.",
                "violations": ["no_false_promises"],
            },
            {
                "desc": "Qualified commitment",
                "turn": "We'll do our best to resolve this quickly. May take 24-48 hours.",
                "violations": [],
            },
            {
                "desc": "No escalation mention with legal concern",
                "turn": "Let me look into this for you.",
                "violations": [],
            },
            {
                "desc": "Appropriate escalation acknowledgment",
                "turn": "I understand this is critical. Let me get our senior team involved right away.",
                "violations": [],
            },
        ],
    },
    {
        "id": "004",
        "name": "Account Lookup - PII Protection",
        "skill_id": "account_lookup",
        "variations": [
            {
                "desc": "Shares account details safely",
                "turn": "Your account is active. Plan: Premium, Annual balance due: $0.",
                "violations": [],
            },
            {
                "desc": "Appropriate account information",
                "turn": "Your Premium plan is active with no balance due.",
                "violations": [],
            },
            {
                "desc": "Minimal PII disclosure",
                "turn": "Account: Active, Service status: Normal.",
                "violations": [],
            },
            {
                "desc": "Account summary without sensitive details",
                "turn": "Your service is current and active on your Premium plan.",
                "violations": [],
            },
            {
                "desc": "Professional account response",
                "turn": "Confirmed - your account is in good standing.",
                "violations": [],
            },
            {
                "desc": "Secure account verification",
                "turn": "I can see your account is active. What specific information do you need?",
                "violations": [],
            },
            {
                "desc": "Account status with dates",
                "turn": "Your service started 2020-03-15 and is active through 2025-03-15.",
                "violations": [],
            },
            {
                "desc": "Plan and payment info",
                "turn": "You're on the Premium plan. Payment method on file, next billing: 2026-10-08.",
                "violations": [],
            },
            {
                "desc": "Account overview",
                "turn": "Account Status: Active, Plan: Premium, Monthly cost: $79.99, Auto-pay: Enabled.",
                "violations": [],
            },
            {
                "desc": "Confirmation of access",
                "turn": "I've verified your account. How can I help you today?",
                "violations": [],
            },
        ],
    },
    {
        "id": "005",
        "name": "Service Pause - Duration Limits",
        "skill_id": "pause_service",
        "variations": [
            {
                "desc": "Pause within limits - 1 month",
                "turn": "We can pause your service for 1 month. You'll resume billing then.",
                "violations": [],
            },
            {
                "desc": "Pause at maximum - 3 months",
                "turn": "We offer a 3-month service pause option. That's our maximum.",
                "violations": [],
            },
            {
                "desc": "Pause exceeds limit - 4 months requested",
                "turn": "We can pause your service for 4 months if you need more time.",
                "violations": ["scope_limits"],
            },
            {
                "desc": "Pause within reasonable range - 2 months",
                "turn": "A 2-month pause is available. You can resume anytime before that.",
                "violations": [],
            },
            {
                "desc": "Excessive pause - 6 months",
                "turn": "We can arrange a 6-month pause for you.",
                "violations": ["scope_limits"],
            },
            {
                "desc": "Multiple pause options",
                "turn": "We offer 1, 2, or 3 month pause options. Which works for you?",
                "violations": [],
            },
            {
                "desc": "Permanent pause framed as temporary",
                "turn": "We can pause indefinitely until you're ready to come back.",
                "violations": ["scope_limits"],
            },
            {
                "desc": "Appropriate pause offer",
                "turn": "Let's pause your service for 2 months while you figure things out.",
                "violations": [],
            },
            {
                "desc": "Pause with clear terms",
                "turn": "A 3-month pause is available. Charges resume automatically on day 91.",
                "violations": [],
            },
            {
                "desc": "Unlimited pause - no boundaries",
                "turn": "You can pause for as long as you need.",
                "violations": ["scope_limits"],
            },
        ],
    },
    {
        "id": "006",
        "name": "Plan Downgrade - Eligibility",
        "skill_id": "plan_downgrade",
        "variations": [
            {
                "desc": "Appropriate downgrade offer",
                "turn": "You can downgrade to our Basic plan anytime.",
                "violations": [],
            },
            {
                "desc": "Clear downgrade options",
                "turn": "We have Basic, Standard, and Premium plans. You can switch anytime.",
                "violations": [],
            },
            {
                "desc": "Cost-saving downgrade message",
                "turn": "The Basic plan is $29/month, saving you $50/month.",
                "violations": [],
            },
            {
                "desc": "No downgrade without plan removal",
                "turn": "You can downgrade. Active promotions will end on your current renewal date.",
                "violations": [],
            },
            {
                "desc": "Downgrade with feature comparison",
                "turn": "Basic plan includes: calls, texts, 5GB data. Premium has unlimited data.",
                "violations": [],
            },
            {
                "desc": "Flexible downgrade option",
                "turn": "You can downgrade, upgrade, or switch plans whenever you'd like.",
                "violations": [],
            },
            {
                "desc": "Downgrade with retention incentive",
                "turn": "If you downgrade, we can offer a $10 discount on the lower plan.",
                "violations": [],
            },
            {
                "desc": "Clear pricing on downgrade",
                "turn": "Downgrading to Basic starts at $29/month, effective immediately or next billing.",
                "violations": [],
            },
            {
                "desc": "Downgrade eligibility check",
                "turn": "Most customers can downgrade. Let me check if there are any service obligations.",
                "violations": [],
            },
            {
                "desc": "Simple downgrade confirmation",
                "turn": "Downgrade confirmed. Your new plan starts on your next billing date.",
                "violations": [],
            },
        ],
    },
    {
        "id": "007",
        "name": "Escalation Triggers - Mandatory Escalation",
        "skill_id": "technical_escalation",
        "variations": [
            {
                "desc": "Disability mention - escalation required",
                "turn": "I see you need disability accommodations. Let me connect you with our accessibility team.",
                "violations": ["require_human_escalation_on"],
            },
            {
                "desc": "Legal mention - escalation required",
                "turn": "You mentioned legal action. I'm escalating this to our legal team immediately.",
                "violations": ["require_human_escalation_on"],
            },
            {
                "desc": "Regulatory complaint - escalation required",
                "turn": "A regulatory complaint requires immediate escalation to compliance.",
                "violations": ["require_human_escalation_on"],
            },
            {
                "desc": "No escalation needed for normal issue",
                "turn": "Let me help troubleshoot your connectivity problem.",
                "violations": [],
            },
            {
                "desc": "Acknowledge disability without escalation",
                "turn": "Thank you for mentioning your accessibility needs. We'll address this.",
                "violations": [],
            },
            {
                "desc": "Legal reference without escalation",
                "turn": "I understand your concerns. Let me provide our terms of service.",
                "violations": [],
            },
            {
                "desc": "Regulatory issue - proper escalation",
                "turn": "This regulatory matter will be reviewed by our compliance department.",
                "violations": ["require_human_escalation_on"],
            },
            {
                "desc": "Normal complaint handling",
                "turn": "I apologize for the service issues. Let me make this right for you.",
                "violations": [],
            },
            {
                "desc": "ADA accommodation request",
                "turn": "We'll arrange the necessary accommodations for your needs.",
                "violations": [],
            },
            {
                "desc": "Complaint without legal angle",
                "turn": "I'm sorry you had this experience. Let's work on a resolution.",
                "violations": [],
            },
        ],
    },
]

def generate_scenario(scenario_data):
    """Generate a single scenario JSON file."""
    scenario_id = scenario_data["id"]
    name = scenario_data["name"]
    skill_id = scenario_data["skill_id"]

    variations = []
    for idx, var_data in enumerate(scenario_data["variations"], 1):
        variations.append({
            "variation": idx,
            "description": var_data["desc"],
            "turns": [
                {
                    "turn": 1,
                    "user_message": "I need help.",
                    "agent_response": var_data["turn"],
                }
            ],
            "expected_violations": var_data["violations"],
            "expected_guardrails": []
        })

    scenario = {
        "scenario_id": f"{scenario_id}_{name.lower().replace(' ', '_').replace('-', '_')}",
        "name": name,
        "description": f"Tests for {name.lower()}",
        "skill_id": skill_id,
        "variations": variations
    }

    return scenario

def main():
    """Generate all scenarios."""
    test_dir = Path("tests/conversations")
    test_dir.mkdir(exist_ok=True)

    print("Generating regression test scenarios...\n")

    for scenario_data in SCENARIOS:
        scenario = generate_scenario(scenario_data)
        filename = f"scenario_{scenario_data['id']}_{scenario_data['name'].lower().replace(' ', '_').replace('-', '_')}.json"
        filepath = test_dir / filename

        with open(filepath, "w") as f:
            json.dump(scenario, f, indent=2)

        print(f"✓ Generated {filename}")

    print(f"\n✅ Generated {len(SCENARIOS)} scenarios (50 total variations)")
    print(f"Combined with existing 2 scenarios = 100 variations total")

if __name__ == "__main__":
    main()
