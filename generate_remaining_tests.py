#!/usr/bin/env python
"""Generate remaining 30 regression test files (3 scenarios × 10 variations each)."""

import json
from pathlib import Path


def generate_unclear_intent_tests():
    """Generate 10 unclear intent scenario tests."""
    tests = []

    scenarios = [
        {
            "num": 1,
            "desc": "Vague complaint - customer unclear about actual issue",
            "turns": ["Something's not right", "I don't know exactly", "Just not happy"],
            "expected_outcome": "clarification_needed",
            "forbidden": ["I guarantee", "definitely"]
        },
        {
            "num": 2,
            "desc": "Multiple issues mentioned - unclear which to address",
            "turns": ["My bill is wrong and service is slow", "And the app crashes", "I don't know what to do"],
            "expected_outcome": "clarification_needed",
            "forbidden": []
        },
        {
            "num": 3,
            "desc": "Non-native speaker - language barrier",
            "turns": ["My service is... problem", "Not work good", "How fix"],
            "expected_outcome": "clarification_needed",
            "forbidden": []
        },
        {
            "num": 4,
            "desc": "Elderly customer confused about service",
            "turns": ["I don't understand the plan", "What's a data limit", "Is this the same company"],
            "expected_outcome": "clarification_needed",
            "forbidden": []
        },
        {
            "num": 5,
            "desc": "Technical jargon confusion",
            "turns": ["My LTE isn't working", "What's a SIM card", "Is that important"],
            "expected_outcome": "clarification_needed",
            "forbidden": []
        },
        {
            "num": 6,
            "desc": "Unclear if cancellation intent or just complaints",
            "turns": ["I'm so frustrated", "Maybe I should leave", "I don't know what to do"],
            "expected_outcome": "clarification_needed",
            "forbidden": []
        },
        {
            "num": 7,
            "desc": "Account sharing confusion",
            "turns": ["I share my account with family", "Bills are confusing", "Whose plan is this"],
            "expected_outcome": "clarification_needed",
            "forbidden": []
        },
        {
            "num": 8,
            "desc": "Business account confusion",
            "turns": ["Our company account has issues", "I'm not sure who owns it", "Need to talk to someone else"],
            "expected_outcome": "clarification_needed",
            "forbidden": []
        },
        {
            "num": 9,
            "desc": "Caller confused about product",
            "turns": ["Is this the TV service", "Do you do internet", "What else do you offer"],
            "expected_outcome": "clarification_needed",
            "forbidden": []
        },
        {
            "num": 10,
            "desc": "Unclear if this is personal or business issue",
            "turns": ["I need help with a line", "It's for my company maybe", "I'm not sure anymore"],
            "expected_outcome": "clarification_needed",
            "forbidden": []
        }
    ]

    for s in scenarios:
        test = {
            "scenario_id": f"unclear_intent_{s['num']:02d}",
            "scenario_type": "unclear_intent",
            "difficulty": "medium",
            "description": s["desc"],
            "turns": [{"speaker": "user", "text": t} for t in s["turns"]],
            "expected_outcome": s["expected_outcome"],
            "expected_skill": "account_lookup",
            "max_turns_allowed": 6,
            "required_guardrail_checks": ["no_forbidden_phrases"],
            "forbidden_phrases_in_agent_response": s["forbidden"],
            "pass_criteria": {
                "outcome_matches": True,
                "max_turns_respected": True,
                "all_guardrail_checks_pass": True,
                "no_forbidden_phrases_in_responses": True
            }
        }
        tests.append(test)

    return tests


def generate_successful_retention_tests():
    """Generate 10 successful retention scenario tests."""
    tests = []

    scenarios = [
        {
            "num": 1,
            "desc": "Loyal customer appreciates proactive retention call",
            "turns": ["Oh, you're calling to help me?", "That's great service", "Let me hear the offer"],
            "expected_outcome": "retained_with_offer",
            "discount": 15
        },
        {
            "num": 2,
            "desc": "20% discount immediately accepted",
            "turns": ["I'm thinking about canceling", "20% sounds good", "Yes, I'll take it"],
            "expected_outcome": "retained_with_offer",
            "discount": 20
        },
        {
            "num": 3,
            "desc": "Customer prefers plan upgrade over discount",
            "turns": ["I want more data", "You can add data?", "Yes, upgrade me"],
            "expected_outcome": "retained_with_upgrade",
            "discount": 0
        },
        {
            "num": 4,
            "desc": "Goodwill credit accepted as retention",
            "turns": ["I had billing issues", "You can refund that?", "Great, I'll stay"],
            "expected_outcome": "retained_with_credit",
            "discount": 0
        },
        {
            "num": 5,
            "desc": "Feature addition retains customer",
            "turns": ["I don't have international roaming", "You can add it?", "Perfect, yes"],
            "expected_outcome": "retained_with_features",
            "discount": 0
        },
        {
            "num": 6,
            "desc": "Manager callback convinces customer",
            "turns": ["This is really frustrating", "A manager will call me?", "OK I'll wait"],
            "expected_outcome": "retained_pending_manager",
            "discount": 0
        },
        {
            "num": 7,
            "desc": "Technical issue resolution retains customer",
            "turns": ["My data is too slow", "You can optimize my line?", "Yes that would help"],
            "expected_outcome": "retained_technical_fix",
            "discount": 0
        },
        {
            "num": 8,
            "desc": "Plan optimization retains customer",
            "turns": ["I'm paying too much", "Let me review your usage", "Oh I can save money?"],
            "expected_outcome": "retained_with_optimization",
            "discount": 0
        },
        {
            "num": 9,
            "desc": "Long-term loyalty recognized with special offer",
            "turns": ["I've been with you for 10 years", "We appreciate loyal customers", "What's the offer"],
            "expected_outcome": "retained_loyalty_bonus",
            "discount": 25
        },
        {
            "num": 10,
            "desc": "Family plan consolidation retains all lines",
            "turns": ["My kids have separate accounts", "You can combine them?", "Yes, do that now"],
            "expected_outcome": "retained_family_plan",
            "discount": 0
        }
    ]

    for s in scenarios:
        test = {
            "scenario_id": f"successful_retention_{s['num']:02d}",
            "scenario_type": "successful_retention",
            "difficulty": "easy",
            "description": s["desc"],
            "turns": [{"speaker": "user", "text": t} for t in s["turns"]],
            "expected_outcome": s["expected_outcome"],
            "expected_skill": "retention_offer",
            "max_turns_allowed": 5,
            "required_guardrail_checks": ["discount_not_exceeded", "no_forbidden_phrases"],
            "forbidden_phrases_in_agent_response": ["I guarantee", "I promise"],
            "pass_criteria": {
                "outcome_matches": True,
                "max_turns_respected": True,
                "all_guardrail_checks_pass": True,
                "no_forbidden_phrases_in_responses": True
            }
        }
        tests.append(test)

    return tests


def generate_topic_switch_tests():
    """Generate 10 topic switch scenario tests."""
    tests = []

    scenarios = [
        {
            "num": 1,
            "desc": "Starts technical issue, ends in cancellation",
            "turns": ["My internet is slow", "I've tried rebooting", "Actually I want to cancel"],
            "skill_sequence": ["technical_escalation", "retention_offer"],
            "expected_outcome": "escalated"
        },
        {
            "num": 2,
            "desc": "Billing complaint becomes cancellation",
            "turns": ["My bill is wrong", "It's been wrong for months", "I'm canceling"],
            "skill_sequence": ["account_lookup", "retention_offer"],
            "expected_outcome": "escalated"
        },
        {
            "num": 3,
            "desc": "Starts wanting to downgrade, ends asking to pause",
            "turns": ["Downgrade me to basic", "Actually I'm leaving town", "Can I just pause instead"],
            "skill_sequence": ["plan_downgrade", "pause_service"],
            "expected_outcome": "paused"
        },
        {
            "num": 4,
            "desc": "Service question becomes cancellation request",
            "turns": ["What's included in premium", "Is it worth the price", "No, I'm canceling"],
            "skill_sequence": ["account_lookup", "retention_offer"],
            "expected_outcome": "escalated"
        },
        {
            "num": 5,
            "desc": "Coverage check becomes cancelation",
            "turns": ["Does this work in Hawaii", "You don't cover there?", "Then I need to cancel"],
            "skill_sequence": ["account_lookup", "retention_offer"],
            "expected_outcome": "escalated"
        },
        {
            "num": 6,
            "desc": "Device question becomes plan change",
            "turns": ["Can I get a new phone", "How much would it cost", "I want to upgrade my plan instead"],
            "skill_sequence": ["account_lookup", "plan_downgrade"],
            "expected_outcome": "upgraded"
        },
        {
            "num": 7,
            "desc": "Technical issue reported, customer actually wants features",
            "turns": ["I can't use video calling", "Oh wait I don't have that feature", "Add it to my plan"],
            "skill_sequence": ["technical_escalation", "plan_downgrade"],
            "expected_outcome": "upgraded"
        },
        {
            "num": 8,
            "desc": "Starts with complaint, ends with pause request",
            "turns": ["Service has been terrible", "I need a break from this", "Can I pause for a month"],
            "skill_sequence": ["retention_offer", "pause_service"],
            "expected_outcome": "paused"
        },
        {
            "num": 9,
            "desc": "Account info leads to discovering better plan",
            "turns": ["What's my current usage", "I'm using way more than I thought", "Show me better plans"],
            "skill_sequence": ["account_lookup", "plan_downgrade"],
            "expected_outcome": "upgraded"
        },
        {
            "num": 10,
            "desc": "Escalation issue becomes simple account question",
            "turns": ["I have a legal complaint about billing", "Actually can you just explain the charges", "Oh I understand now"],
            "skill_sequence": ["technical_escalation", "account_lookup"],
            "expected_outcome": "resolved"
        }
    ]

    for s in scenarios:
        test = {
            "scenario_id": f"topic_switch_{s['num']:02d}",
            "scenario_type": "topic_switch",
            "difficulty": "hard",
            "description": s["desc"],
            "turns": [{"speaker": "user", "text": t} for t in s["turns"]],
            "skill_sequence": s["skill_sequence"],
            "expected_outcome": s["expected_outcome"],
            "max_turns_allowed": 7,
            "required_guardrail_checks": ["skill_detection", "state_transition"],
            "forbidden_phrases_in_agent_response": [],
            "pass_criteria": {
                "skill_sequence_correct": True,
                "max_turns_respected": True,
                "state_transitions_valid": True,
                "outcome_matches": True
            }
        }
        tests.append(test)

    return tests


def main():
    """Generate and save all 30 remaining test files."""
    test_dir = Path("tests/conversations")
    test_dir.mkdir(parents=True, exist_ok=True)

    print("Generating remaining 30 regression test files...\n")

    # Generate unclear intent tests
    print("Generating 10 'unclear_intent' scenario tests...")
    unclear_tests = generate_unclear_intent_tests()
    for test in unclear_tests:
        filename = test_dir / f"scenario_008_unclear_intent_{test['scenario_id'].split('_')[-1]}.json"
        with open(filename, "w") as f:
            json.dump(test, f, indent=2)
        print(f"  ✓ {filename.name}")

    # Generate successful retention tests
    print("\nGenerating 10 'successful_retention' scenario tests...")
    success_tests = generate_successful_retention_tests()
    for test in success_tests:
        filename = test_dir / f"scenario_009_successful_retention_{test['scenario_id'].split('_')[-1]}.json"
        with open(filename, "w") as f:
            json.dump(test, f, indent=2)
        print(f"  ✓ {filename.name}")

    # Generate topic switch tests
    print("\nGenerating 10 'topic_switch' scenario tests...")
    switch_tests = generate_topic_switch_tests()
    for test in switch_tests:
        filename = test_dir / f"scenario_010_topic_switch_{test['scenario_id'].split('_')[-1]}.json"
        with open(filename, "w") as f:
            json.dump(test, f, indent=2)
        print(f"  ✓ {filename.name}")

    print("\n" + "="*60)
    print("✅ Generated 30 additional regression test files")
    print("="*60)
    print(f"\nTotal tests now available: 100/100")
    print(f"  • Scenario 1-7: 70 tests (previously created)")
    print(f"  • Scenario 8: 10 tests (unclear_intent)")
    print(f"  • Scenario 9: 10 tests (successful_retention)")
    print(f"  • Scenario 10: 10 tests (topic_switch)")
    print(f"\nRun regression suite: python tests/regression_test_runner.py")


if __name__ == "__main__":
    main()
