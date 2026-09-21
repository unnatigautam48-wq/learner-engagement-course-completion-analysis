from pathlib import Path
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "oulad"
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
for p in [PROCESSED, OUTPUTS]:
    p.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid", palette="deep")

# 1. Load the small reference and learner tables.
student_info = pd.read_csv(RAW / "studentInfo.csv")
student_registration = pd.read_csv(RAW / "studentRegistration.csv")
assessments = pd.read_csv(RAW / "assessments.csv")
student_assessment = pd.read_csv(RAW / "studentAssessment.csv")
courses = pd.read_csv(RAW / "courses.csv")
vle = pd.read_csv(RAW / "vle.csv")

# 2. Aggregate the large clickstream table in chunks to keep the workflow reproducible and memory-safe.
activity_parts = []
activity_cols = ["code_module", "code_presentation", "id_student", "date", "sum_click"]
for chunk in pd.read_csv(RAW / "studentVle.csv", usecols=activity_cols, chunksize=500_000):
    activity_parts.append(
        chunk.groupby(["code_module", "code_presentation", "id_student"], as_index=False)
        .agg(total_clicks=("sum_click", "sum"), active_days=("date", "nunique"), activity_rows=("sum_click", "size"))
    )
activity = pd.concat(activity_parts, ignore_index=True)
activity = (
    activity.groupby(["code_module", "code_presentation", "id_student"], as_index=False)
    .agg(total_clicks=("total_clicks", "sum"), active_days=("active_days", "sum"), activity_rows=("activity_rows", "sum"))
)

# 3. Build assessment features. Missing score rows are retained as non-submissions.
assessment_map = assessments[["id_assessment", "code_module", "code_presentation", "assessment_type", "date", "weight"]]
sa = student_assessment.merge(assessment_map, on="id_assessment", how="left", validate="many_to_one")
sa["score"] = pd.to_numeric(sa["score"], errors="coerce")
assessment_features = (
    sa.groupby(["code_module", "code_presentation", "id_student"], as_index=False)
    .agg(
        assessments_recorded=("id_assessment", "count"),
        assessments_submitted=("score", lambda s: s.notna().sum()),
        average_score=("score", "mean"),
    )
)
# Calculate weighted score separately because each learner has different assessment rows.
sa["weighted_points"] = sa["score"].fillna(0) * sa["weight"].fillna(0) / 100
weighted = sa.groupby(["code_module", "code_presentation", "id_student"], as_index=False).agg(weighted_score=("weighted_points", "sum"))
assessment_features = assessment_features.merge(weighted, on=["code_module", "code_presentation", "id_student"], how="left")

# 4. Create one analysis-ready learner-course table.
base = student_info.merge(
    student_registration[["code_module", "code_presentation", "id_student", "date_registration", "date_unregistration"]],
    on=["code_module", "code_presentation", "id_student"], how="left", validate="one_to_one"
)
base = base.merge(courses, on=["code_module", "code_presentation"], how="left", validate="many_to_one")
base = base.merge(activity, on=["code_module", "code_presentation", "id_student"], how="left")
base = base.merge(assessment_features, on=["code_module", "code_presentation", "id_student"], how="left")
for col in ["total_clicks", "active_days", "activity_rows", "assessments_recorded", "assessments_submitted"]:
    base[col] = base[col].fillna(0)
base["average_score"] = base["average_score"].fillna(0)
base["weighted_score"] = base["weighted_score"].fillna(0)
base["is_withdrawn"] = (base["final_result"].eq("Withdrawn")).astype(int)
base["is_successful"] = base["final_result"].isin(["Pass", "Distinction"]).astype(int)
base["is_completed"] = (~base["final_result"].eq("Withdrawn")).astype(int)
base["submission_rate"] = np.where(base["assessments_recorded"] > 0, base["assessments_submitted"] / base["assessments_recorded"], 0)
# Transparent operational definition for prioritising learners for follow-up.
click_median = base["total_clicks"].median()
base["at_risk"] = ((base["is_withdrawn"] == 1) | ((base["total_clicks"] < click_median) & (base["assessments_submitted"] == 0))).astype(int)
base["outcome_group"] = base["final_result"].replace({"Distinction": "Successful", "Pass": "Successful", "Fail": "Unsuccessful", "Withdrawn": "Withdrawn"})

# 5. Produce summary tables used by the dashboard and SQL layer.
course_summary = (
    base.groupby(["code_module", "code_presentation"], as_index=False)
    .agg(
        learners=("id_student", "nunique"),
        successful_completion_rate=("is_successful", "mean"),
        completion_rate=("is_completed", "mean"),
        withdrawal_rate=("is_withdrawn", "mean"),
        average_clicks=("total_clicks", "mean"),
        median_clicks=("total_clicks", "median"),
        average_active_days=("active_days", "mean"),
        average_score=("average_score", "mean"),
        average_submission_rate=("submission_rate", "mean"),
        at_risk_learners=("at_risk", "sum"),
    )
)
outcome_summary = base["outcome_group"].value_counts().rename_axis("outcome_group").reset_index(name="learners")
outcome_summary["share"] = outcome_summary["learners"] / outcome_summary["learners"].sum()
engagement_summary = (
    base.groupby("outcome_group", as_index=False)
    .agg(learners=("id_student", "size"), avg_clicks=("total_clicks", "mean"), median_clicks=("total_clicks", "median"), avg_active_days=("active_days", "mean"), avg_submission_rate=("submission_rate", "mean"), avg_score=("average_score", "mean"))
)
weekly_activity = None
# The source records use relative course days; this is useful for a recurring monitoring report.
activity_daily_parts = []
for chunk in pd.read_csv(RAW / "studentVle.csv", usecols=activity_cols, chunksize=500_000):
    activity_daily_parts.append(chunk.groupby(["code_module", "code_presentation", "date"], as_index=False).agg(total_clicks=("sum_click", "sum"), active_learners=("id_student", "nunique")))
activity_daily = pd.concat(activity_daily_parts, ignore_index=True).groupby(["code_module", "code_presentation", "date"], as_index=False).agg(total_clicks=("total_clicks", "sum"), active_learners=("active_learners", "sum"))
activity_daily["week"] = (activity_daily["date"] // 7) + 1
weekly_activity = activity_daily.groupby(["code_module", "code_presentation", "week"], as_index=False).agg(total_clicks=("total_clicks", "sum"), active_learners=("active_learners", "sum"))

# 6. Save clean data and dashboard-ready outputs.
base.to_csv(PROCESSED / "learner_course_metrics.csv", index=False)
course_summary.to_csv(OUTPUTS / "course_summary.csv", index=False)
outcome_summary.to_csv(OUTPUTS / "outcome_summary.csv", index=False)
engagement_summary.to_csv(OUTPUTS / "engagement_summary.csv", index=False)
weekly_activity.to_csv(OUTPUTS / "weekly_activity.csv", index=False)

# 7. Create a portable SQLite database for SQL practice and reproducibility.
db_path = ROOT / "learner_engagement.db"
with sqlite3.connect(db_path) as conn:
    base.to_sql("learner_course_metrics", conn, if_exists="replace", index=False)
    course_summary.to_sql("course_summary", conn, if_exists="replace", index=False)
    weekly_activity.to_sql("weekly_activity", conn, if_exists="replace", index=False)

# 8. Create a professional static dashboard image for portfolio use.
fig = plt.figure(figsize=(14, 8.5), constrained_layout=True)
gs = fig.add_gridspec(2, 2)
fig.suptitle("Learner Engagement & Course Completion Dashboard", fontsize=18, fontweight="bold")
ax1 = fig.add_subplot(gs[0, 0])
sns.barplot(data=outcome_summary, x="outcome_group", y="learners", ax=ax1, color="#2563eb")
ax1.set_title("Learner outcomes"); ax1.set_xlabel(""); ax1.set_ylabel("Learners")
for c in ax1.containers: ax1.bar_label(c, fmt="%.0f")
ax2 = fig.add_subplot(gs[0, 1])
cs = course_summary.sort_values("successful_completion_rate", ascending=False)
sns.barplot(data=cs, x="code_module", y="successful_completion_rate", hue="code_presentation", ax=ax2)
ax2.set_title("Successful completion by module"); ax2.set_xlabel("Module"); ax2.set_ylabel("Rate")
ax2.set_ylim(0, 1); ax2.yaxis.set_major_formatter(lambda x, pos: f"{x:.0%}")
ax3 = fig.add_subplot(gs[1, 0])
sns.boxplot(data=base, x="outcome_group", y="total_clicks", ax=ax3, showfliers=False)
ax3.set_title("Engagement differs by outcome"); ax3.set_xlabel(""); ax3.set_ylabel("Total VLE clicks")
ax4 = fig.add_subplot(gs[1, 1])
wa = weekly_activity.groupby("week", as_index=False).agg(total_clicks=("total_clicks", "sum"), active_learners=("active_learners", "sum"))
sns.lineplot(data=wa, x="week", y="active_learners", marker="o", ax=ax4, color="#059669")
ax4.set_title("Weekly active learner trend"); ax4.set_xlabel("Course week"); ax4.set_ylabel("Active learners")
fig.savefig(OUTPUTS / "dashboard.png", dpi=180, bbox_inches="tight")
plt.close(fig)

# 9. Save a data-quality audit.
quality = pd.DataFrame({
    "check": ["learner rows", "duplicate learner-course rows", "missing final result", "missing activity after fill", "missing average score after fill"],
    "value": [len(base), int(base.duplicated(["code_module", "code_presentation", "id_student"]).sum()), int(base["final_result"].isna().sum()), int(base["total_clicks"].isna().sum()), int(base["average_score"].isna().sum())]
})
quality.to_csv(OUTPUTS / "data_quality_audit.csv", index=False)
print(f"Built {len(base):,} learner-course rows and {len(course_summary):,} course-presentation summaries.")
print(f"SQLite database: {db_path}")
print(f"Dashboard: {OUTPUTS / 'dashboard.png'}")
