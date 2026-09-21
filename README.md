Learner Engagement & Course Completion Analysis Dashboard
Project overview
This project analyzes learner engagement, assessment activity, and course outcomes using the Open University Learning Analytics Dataset (OULAD). The goal is to support a recurring reporting workflow: prepare data from multiple related sources, validate the joined dataset, compare course performance, identify engagement patterns, and create an operational review list for learners who may need follow-up.

The project uses real public data rather than simulated records. OULAD contains course, learner, assessment, registration, and virtual learning environment interaction data. The analysis is intentionally designed for a Data Analyst Intern portfolio: it emphasizes SQL, data cleaning, data validation, structured reporting, dashboard metrics, and business recommendations.

Business questions
Which course presentations have the highest withdrawal or lowest successful-completion rates?
How does learner engagement differ across successful, unsuccessful, and withdrawn outcomes?
Is assessment submission behavior associated with learner outcomes?
At which course weeks does learner activity change materially?
Which learners should be prioritised for a review queue based on low activity and non-submission signals?
Data source
The project uses the Open University Learning Analytics Dataset, downloaded from the UCI Machine Learning Repository. The original dataset paper is Kuzilek, Hlosta, and Zdrahal, Open University Learning Analytics Dataset, Scientific Data, 2017. The dataset is available under a CC BY 4.0 licence; attribution should be retained when sharing the project.

The source contains anonymised learner-level and interaction-level data. The original publication reports 32,593 students, 22 course presentations, assessment results, and 10,655,280 daily VLE interaction records.

Data model and preparation
The pipeline in src/build_analysis.py loads the learner, registration, assessment, course, and VLE tables. The large studentVle.csv file is processed in chunks and aggregated before joining, which avoids loading the complete clickstream into memory at once.

The analysis-ready grain is one row per code_module, code_presentation, and id_student. Key derived fields include total VLE clicks, active days, assessment submission rate, average assessment score, weighted assessment points, successful outcome flag, withdrawal flag, and an operational at-risk flag.

The at-risk definition is deliberately transparent rather than predictive: a learner is flagged when the final outcome is Withdrawn, or when total clicks are below the dataset median and no assessment has been submitted. This is a prioritisation rule for review, not a claim that a learner will definitely withdraw.

Outputs
Output	Purpose
outputs/dashboard.png	Static portfolio dashboard with outcomes, completion by module, engagement distributions, and weekly activity trend
outputs/course_summary.csv	Course-presentation KPI table
outputs/outcome_summary.csv	Outcome counts and shares
outputs/engagement_summary.csv	Engagement and submission metrics by outcome group
outputs/weekly_activity.csv	Recurring weekly activity report
outputs/data_quality_audit.csv	Basic completeness and duplicate checks
data/processed/learner_course_metrics.csv	Analysis-ready learner-course table
learner_engagement.db	SQLite database for SQL practice and reproducibility
sql/analysis_queries.sql	Reusable KPI, performance, review-queue, and quality-check queries
How to run
From the project root:

python3 src/build_analysis.py
The script expects the official OULAD CSV files under data/raw/oulad/. The raw archive is not committed to the project because the source clickstream is large; download it from UCI and extract the CSV files into that folder.

The project uses Python with Pandas, NumPy, Matplotlib, and Seaborn. A minimal environment can be created with:

pip install pandas numpy matplotlib seaborn
Verified findings
The current run produced 32,593 learner-course records. Overall, 47.20% of records had a successful outcome and 31.16% were withdrawals. Successful learners averaged 2,068.23 VLE clicks and 91.57 active days, compared with 313.95 clicks and 16.29 active days for withdrawn learners. Average assessment submission was 99.95% for successful learners and 45.86% for withdrawn learners. These are descriptive associations, not causal effects.

Among the course presentations in this dataset, AAA-2013J had the highest successful-outcome rate in the top-five result, at 72.58%, while EEE-2013J had a 57.89% successful-outcome rate and a 23.10% withdrawal rate. Course presentations should be compared carefully because the source documentation notes that B and J presentations may differ in structure.

The most important analytical story is the comparison between engagement and outcomes: successful learners should be compared with withdrawn and unsuccessful learners using both click volume and assessment submission behavior. The dashboard should be used to identify where follow-up or reporting improvements could be prioritised, not to make unsupported causal claims.

Limitations
The dataset is anonymised and reflects the Open University context, so findings should not be generalised to every learning platform. VLE clicks are a proxy for engagement and do not prove learning or causation. The dashboard is descriptive; it does not train or deploy a predictive model. Course presentations marked B and J may have different structures, so comparisons should be interpreted carefully and ideally segmented by presentation.
