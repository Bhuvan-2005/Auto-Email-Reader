#!/home/bhuvan/Documents/Projects/autoEmailReader/venv/bin/python3
"""Analyze emails using kiro-cli with parallel processing."""

import subprocess
import json
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

sys.path.insert(0, str(Path(__file__).parent))
from database_adapter import get_unanalyzed_emails, store_analysis

# Thread-safe print
print_lock = threading.Lock()


ANALYSIS_PROMPT = """You are analyzing emails for a final-year student. Your task is to:
1. Summarize the email in 3 sentences
2. Assign a priority score (0-10)
3. Extract any deadlines mentioned
4. Decide if it should be trashed

PRIORITY SCORING:
- 9-10: Job offers, interview invitations, internship opportunities, project collaborations from companies
- 6-8: Networking from professionals, career events, academic deadlines, important university notices
- 3-5: General newsletters (tech/career related), course updates, social notifications
- 1-2: Marketing emails, promotional spam, unimportant social media notifications
- 0: Obvious spam, phishing, scams

AUTO-TRASH RULE: Only recommend trash if priority ≤ 2

DEADLINE EXTRACTION: Look for phrases like "apply by", "deadline", "due date", "interview on", etc.

Email to analyze:
---
From: {sender}
Subject: {subject}
Body:
{body}
---

Respond with ONLY valid JSON in this exact format:
{{
  "summary": "Brief 3 sentence summary",
  "priority": 7,
  "deadlines": [
    {{"date": "2026-04-20", "description": "Application deadline"}},
    {{"date": "2026-04-25", "description": "Interview scheduled"}}
  ],
  "should_trash": false,
  "reasoning": "Why this priority was assigned"
}}

If no deadlines, use empty array: "deadlines": []
"""


def analyze_email_with_kiro(sender, subject, body):
    """Analyze a single email using kiro-cli."""
    prompt = ANALYSIS_PROMPT.format(
        sender=sender,
        subject=subject,
        body=body[:2000]  # Limit body length
    )
    
    try:
        # Call kiro-cli with temperature=0 for consistency
        import os
        env = os.environ.copy()
        env['KIRO_TEMPERATURE'] = '0'
        
        result = subprocess.run(
            ['kiro-cli', 'chat', '--no-interactive', '--trust-all-tools', prompt],
            capture_output=True,
            text=True,
            timeout=60,
            env=env
        )
        
        if result.returncode != 0:
            print(f"Error from kiro-cli: {result.stderr}")
            return None
        
        # Extract JSON from response
        response = result.stdout.strip()
        
        # Try to find JSON in response
        start = response.find('{')
        end = response.rfind('}') + 1
        
        if start == -1 or end == 0:
            print(f"No JSON found in response")
            return None
        
        json_str = response[start:end]
        analysis = json.loads(json_str)
        
        return analysis
        
    except subprocess.TimeoutExpired:
        print("Kiro-cli timeout")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print(f"Response was: {response}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def analyze_single_email(email_data):
    """Analyze a single email (for parallel processing)."""
    email_id, sender, subject, body, received_at = email_data
    
    with print_lock:
        print(f"\nAnalyzing: {subject[:50]}...")
    
    analysis = analyze_email_with_kiro(sender, subject, body)
    
    if analysis:
        store_analysis(
            email_id,
            analysis['summary'],
            analysis['priority'],
            analysis.get('deadlines', []),
            analysis.get('should_trash', False),
            analysis.get('reasoning', '')
        )
        with print_lock:
            print(f"  ✓ Priority: {analysis['priority']}, Trash: {analysis.get('should_trash', False)}")
        return True
    else:
        # Store default analysis if kiro fails
        store_analysis(
            email_id,
            f"Email from {sender}: {subject}",
            5,  # Default medium priority
            [],
            False,
            "Analysis failed, assigned default priority"
        )
        with print_lock:
            print(f"  ✗ Analysis failed, using defaults")
        return False


def analyze_all_unanalyzed():
    """Analyze all unanalyzed emails in parallel."""
    emails = get_unanalyzed_emails()
    
    if not emails:
        print("No unanalyzed emails")
        return
    
    print(f"Analyzing {len(emails)} emails in parallel (max 5 at a time)...")
    
    success_count = 0
    
    # Process up to 5 emails in parallel
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(analyze_single_email, email): email for email in emails}
        
        for future in as_completed(futures):
            if future.result():
                success_count += 1
    
    print(f"\n✓ Successfully analyzed {success_count}/{len(emails)} emails")


if __name__ == '__main__':
    analyze_all_unanalyzed()
