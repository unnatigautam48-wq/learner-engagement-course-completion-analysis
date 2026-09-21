-- Learner Engagement & Course Completion Analysis
-- SQLite-compatible queries against learner_course_metrics.

-- 1. KPI snapshot
SELECT
    COUNT(DISTINCT id_student) AS learners,
    ROUND(AVG(is_successful) * 100, 2) AS successful_completion_rate_pct,
    ROUND(AVG(is_withdrawn) * 100, 2) AS withdrawal_rate_pct,
    ROUND(AVG(total_clicks), 2) AS average_clicks,
    ROUND(AVG(submission_rate) * 100, 2) AS average_submission_rate_pct
FROM learner_course_metrics;

-- 2. Course/presentation performance summary
SELECT
    code_module,
    code_presentation,
    learners,
    ROUND(successful_completion_rate * 100, 2) AS successful_completion_rate_pct,
    ROUND(withdrawal_rate * 100, 2) AS withdrawal_rate_pct,
    ROUND(average_clicks, 2) AS average_clicks,
    ROUND(average_submission_rate * 100, 2) AS average_submission_rate_pct,
    at_risk_learners
FROM course_summary
ORDER BY successful_completion_rate DESC;

-- 3. Identify modules with the highest withdrawal rate
SELECT code_module, code_presentation, learners,
       ROUND(withdrawal_rate * 100, 2) AS withdrawal_rate_pct
FROM course_summary
ORDER BY withdrawal_rate DESC
LIMIT 5;

-- 4. Compare engagement by final outcome
SELECT
    outcome_group,
    COUNT(*) AS learners,
    ROUND(AVG(total_clicks), 2) AS average_clicks,
    ROUND(AVG(active_days), 2) AS average_active_days,
    ROUND(AVG(submission_rate) * 100, 2) AS average_submission_rate_pct,
    ROUND(AVG(average_score), 2) AS average_score
FROM learner_course_metrics
GROUP BY outcome_group
ORDER BY average_clicks DESC;

-- 5. Weekly recurring activity report
SELECT
    code_module,
    code_presentation,
    week,
    total_clicks,
    active_learners
FROM weekly_activity
ORDER BY code_module, code_presentation, week;

-- 6. At-risk learner review queue
SELECT
    code_module,
    code_presentation,
    id_student,
    total_clicks,
    active_days,
    assessments_submitted,
    submission_rate,
    final_result
FROM learner_course_metrics
WHERE at_risk = 1
ORDER BY total_clicks ASC, submission_rate ASC;

-- 7. Data-quality check: duplicate learner-course records
SELECT code_module, code_presentation, id_student, COUNT(*) AS record_count
FROM learner_course_metrics
GROUP BY code_module, code_presentation, id_student
HAVING COUNT(*) > 1;
