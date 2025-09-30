Usage
=====

Command Line
------------

.. code-block:: bash

    git_reviewer

This will run the main application.

Python API
----------

.. code-block:: python

    from git_reviewer.api import review_repository

    # Review current repository
    nllm_results = review_repository()

    # Access structured results including the new explanation field
    for result in nllm_results.results:
        if result.status == "ok" and hasattr(result, 'json') and result.json:
            # Access the comprehensive explanation field
            explanation = result.json.get('explanation', {})
            print(f"Overview: {explanation.get('overview', 'N/A')}")

            # Detailed analysis of each file
            for analysis in explanation.get('detailed_analysis', []):
                print(f"File: {analysis['file']}")
                print(f"Purpose: {analysis['purpose']}")
                print(f"Technical Details: {analysis['technical_details']}")

Output Format
-------------

git-reviewer returns structured JSON with these key sections:

- **summary**: Overall assessment and readiness status
- **blocking_issues**: Critical problems requiring fixes
- **findings**: Non-blocking issues with severity levels
- **explanation**: **NEW** - Exhaustive documentation of all changes
- **security_review**: Security-specific analysis
- **performance_notes**: Performance considerations
- **testing_gaps**: Missing test coverage

The **explanation** field provides comprehensive change documentation:

.. code-block:: json

    {
      "explanation": {
        "overview": "High-level summary of all changes",
        "detailed_analysis": [
          {
            "file": "path/to/file.ext",
            "change_type": "modified",
            "lines_added": 10,
            "lines_removed": 5,
            "purpose": "What this change accomplishes",
            "technical_details": "How the change works",
            "dependencies": ["affected components"],
            "business_logic": "Why this change was needed",
            "implementation_notes": "Key decisions made"
          }
        ],
        "architectural_impact": "System-wide effects",
        "data_flow_changes": "How data flows differently",
        "integration_points": "Affected external systems",
        "behavioral_changes": "Changes in behavior",
        "rollback_considerations": "What's needed to undo changes"
      }
    }
