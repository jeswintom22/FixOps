def send_alert(analysis, decision):
    print("\n========== ALERT ==========")

    print(f"Severity : {analysis.get('severity')}")
    print(f"Root Cause : {analysis.get('root_cause')}")
    print(f"Suggested Fix : {analysis.get('suggested_fix')}")

    print("\nDecision:")
    print(decision)

    print("========== END ALERT ==========\n")