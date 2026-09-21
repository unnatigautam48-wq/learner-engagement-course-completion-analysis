from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
with sqlite3.connect(ROOT / "learner_engagement.db") as conn:
    kpi = pd.read_sql_query("""
        SELECT COUNT(*) AS learner_course_rows,
               ROUND(AVG(is_successful)*100,2) AS success_pct,
               ROUND(AVG(is_withdrawn)*100,2) AS withdrawal_pct,
               ROUND(AVG(total_clicks),2) AS avg_clicks,
               ROUND(AVG(submission_rate)*100,2) AS submission_pct
        FROM learner_course_metrics
    """, conn)
    outcome = pd.read_sql_query("""
        SELECT outcome_group, COUNT(*) AS learners,
               ROUND(AVG(total_clicks),2) AS avg_clicks,
               ROUND(AVG(active_days),2) AS avg_active_days,
               ROUND(AVG(submission_rate)*100,2) AS avg_submission_pct
        FROM learner_course_metrics
        GROUP BY outcome_group ORDER BY avg_clicks DESC
    """, conn)
    courses = pd.read_sql_query("""
        SELECT code_module, code_presentation, learners,
               ROUND(successful_completion_rate*100,2) AS success_pct,
               ROUND(withdrawal_rate*100,2) AS withdrawal_pct
        FROM course_summary
        ORDER BY successful_completion_rate DESC LIMIT 5
    """, conn)
print("KPI\n", kpi.to_string(index=False))
print("\nOUTCOME\n", outcome.to_string(index=False))
print("\nTOP COURSE PRESENTATIONS\n", courses.to_string(index=False))
