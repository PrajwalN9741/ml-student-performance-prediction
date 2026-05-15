import os
import io
import json
from datetime import datetime

from flask import Flask, render_template, request, send_file
import pandas as pd
import joblib
from fpdf import FPDF

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

app = Flask(__name__)

# ---------- PATH SETUP (ABSOLUTE) ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "outputs")
CHART_FOLDER = os.path.join(BASE_DIR, "static", "charts")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(CHART_FOLDER, exist_ok=True)

# ---------- MODEL + METRICS LOAD ----------
MODEL = joblib.load(os.path.join(BASE_DIR, "model.pkl"))

try:
    with open(os.path.join(BASE_DIR, "algo_metrics.json"), "r") as f:
        ALGO_METRICS = json.load(f)
except Exception:
    ALGO_METRICS = None

# Default dataset path (used for default predictions on GET)
DEFAULT_DATA_FILE = os.path.join(UPLOAD_FOLDER, "student_data.csv")

# ---------- TRAINING DATA PREVIEW ----------
TRAIN_TABLE_HTML = None
try:
    if os.path.exists(DEFAULT_DATA_FILE):
        if DEFAULT_DATA_FILE.endswith(".csv"):
            _train_df = pd.read_csv(DEFAULT_DATA_FILE)
        elif DEFAULT_DATA_FILE.endswith((".xlsx", ".xls")):
            _train_df = pd.read_excel(DEFAULT_DATA_FILE)
        else:
            _train_df = None

        if _train_df is not None:
            TRAIN_TABLE_HTML = _train_df.head(20).to_html(
                classes="table table-striped table-sm table-bordered align-middle mb-0",
                index=False,
            )
except Exception as e:
    print("Error loading training dataset preview:", e)
    TRAIN_TABLE_HTML = None


def create_charts(df):
    """
    Create charts from dataframe with predictions and
    return dict of chart metadata (filename + title + description).
    """
    charts = {}

    # -------- 1) Pass vs Fail count --------
    if "Predicted" in df.columns:
        plt.figure()
        counts = df["Predicted"].value_counts()
        counts = counts.reindex(["yes", "no"]).fillna(0)
        counts.plot(kind="bar")
        plt.title("Count of Predicted Pass vs Fail")
        plt.xlabel("Prediction")
        plt.ylabel("Number of Students")
        file1 = os.path.join(CHART_FOLDER, "predicted_counts.png")
        plt.tight_layout()
        plt.savefig(file1)
        plt.close()
        charts["predicted_counts"] = {
            "file": "charts/predicted_counts.png",
            "title": "Predicted Pass/Fail Distribution",
            "desc": (
                "This bar chart shows how many students are predicted to pass and how many are "
                "predicted to fail. It gives a quick overview of overall performance in the dataset."
            ),
        }

    # -------- 2) Average study time by prediction --------
    if "studytime" in df.columns and "Predicted" in df.columns:
        try:
            plt.figure()
            df.groupby("Predicted")["studytime"].mean().plot(kind="bar")
            plt.title("Average Study Time by Prediction")
            plt.xlabel("Prediction")
            plt.ylabel("Average Study Time (scale 1–4)")
            file2 = os.path.join(CHART_FOLDER, "studytime_by_pred.png")
            plt.tight_layout()
            plt.savefig(file2)
            plt.close()
            charts["studytime_by_pred"] = {
                "file": "charts/studytime_by_pred.png",
                "title": "Study Time vs Performance",
                "desc": (
                    "This chart compares the average study time (1–4 scale) for students predicted "
                    "to pass vs those predicted to fail. Higher bars for 'pass' usually indicate "
                    "that more study time is linked with better performance."
                ),
            }
        except Exception:
            pass

    # -------- 3) Absences histogram --------
    if "absences" in df.columns:
        try:
            plt.figure()
            df["absences"].plot(kind="hist", bins=15)
            plt.title("Distribution of Absences")
            plt.xlabel("Number of Absences")
            plt.ylabel("Number of Students")
            file3 = os.path.join(CHART_FOLDER, "absences_hist.png")
            plt.tight_layout()
            plt.savefig(file3)
            plt.close()
            charts["absences_hist"] = {
                "file": "charts/absences_hist.png",
                "title": "Absence Distribution",
                "desc": (
                    "This histogram shows how often students are absent from school. "
                    "A long tail to the right means some students have very high absence counts, "
                    "which can negatively impact their chance of passing."
                ),
            }
        except Exception:
            pass

    # -------- 4) Average failures by prediction --------
    if "failures" in df.columns and "Predicted" in df.columns:
        try:
            plt.figure()
            df.groupby("Predicted")["failures"].mean().plot(kind="bar")
            plt.title("Average Past Failures by Prediction")
            plt.xlabel("Prediction")
            plt.ylabel("Average Number of Past Failures")
            file4 = os.path.join(CHART_FOLDER, "failures_by_pred.png")
            plt.tight_layout()
            plt.savefig(file4)
            plt.close()
            charts["failures_by_pred"] = {
                "file": "charts/failures_by_pred.png",
                "title": "Past Failures vs Performance",
                "desc": (
                    "This chart shows the average number of previous subject failures for students "
                    "predicted to pass vs fail. Higher average failures for the 'fail' bar indicate "
                    "that past academic history is strongly related to current risk."
                ),
            }
        except Exception:
            pass

    # -------- 5) Correlation heatmap --------
    try:
        df_heat = df.copy()
        num_cols = [
            "age", "Medu", "Fedu", "traveltime", "studytime",
            "failures", "famrel", "freetime", "goout",
            "Dalc", "Walc", "health", "absences",
        ]
        if "Predicted" in df_heat.columns:
            df_heat["Predicted_num"] = (df_heat["Predicted"] == "yes").astype(int)
        else:
            df_heat["Predicted_num"] = 0

        num_cols_for_corr = [c for c in num_cols if c in df_heat.columns] + ["Predicted_num"]

        if len(num_cols_for_corr) >= 2:
            corr = df_heat[num_cols_for_corr].corr()

            plt.figure(figsize=(8, 6))
            plt.imshow(corr, cmap="coolwarm", interpolation="nearest")
            plt.colorbar()
            plt.xticks(range(len(corr.columns)), corr.columns, rotation=90, fontsize=7)
            plt.yticks(range(len(corr.index)), corr.index, fontsize=7)
            for i in range(len(corr.index)):
                for j in range(len(corr.columns)):
                    plt.text(
                        j,
                        i,
                        f"{corr.iloc[i, j]:.2f}",
                        ha="center",
                        va="center",
                        fontsize=5,
                    )
            plt.title("Correlation Heatmap (Features vs Prediction)")
            plt.tight_layout()
            file5 = os.path.join(CHART_FOLDER, "corr_heatmap.png")
            plt.savefig(file5, dpi=200)
            plt.close()
            charts["corr_heatmap"] = {
                "file": "charts/corr_heatmap.png",
                "title": "Correlation Heatmap",
                "desc": (
                    "The heatmap shows correlations between numeric features (age, study time, "
                    "absences, etc.) and the predicted result. Values close to +1 or -1 indicate a "
                    "strong relationship with the pass/fail prediction."
                ),
            }
    except Exception:
        pass

    # -------- 6) Confusion matrices (raw counts + normalized) --------
    cm_raw_path = os.path.join(CHART_FOLDER, "confusion_matrix_raw.png")
    if os.path.exists(cm_raw_path):
        charts["confusion_matrix_raw"] = {
            "file": "charts/confusion_matrix_raw.png",
            "title": "Confusion Matrix (Counts)",
            "desc": (
                "This confusion matrix shows the number of students correctly and incorrectly "
                "classified as pass or fail. The diagonal cells are correct predictions; "
                "off-diagonal cells show misclassifications (e.g., predicted pass but actually failed)."
            ),
        }

    cm_norm_path = os.path.join(CHART_FOLDER, "confusion_matrix_norm.png")
    if os.path.exists(cm_norm_path):
        charts["confusion_matrix_norm"] = {
            "file": "charts/confusion_matrix_norm.png",
            "title": "Confusion Matrix (Normalized)",
            "desc": (
                "This matrix shows the percentage of correct and incorrect predictions within each "
                "true class (pass/fail). Each row sums to 100%, so you can easily see how well the "
                "model performs for failing students vs passing students."
            ),
        }

    # -------- 7) Algorithm comparison chart --------
    algo_chart_path = os.path.join(CHART_FOLDER, "algo_comparison.png")
    if os.path.exists(algo_chart_path):
        charts["algo_comparison"] = {
            "file": "charts/algo_comparison.png",
            "title": "Algorithm Accuracy Comparison",
            "desc": (
                "This bar chart compares the accuracy of different machine learning algorithms. "
                "Depending on training, it may show cross-validation mean accuracy or test accuracy. "
                "The highest bar represents the algorithm selected as the best model."
            ),
        }

    # -------- 8) Feature importance (Random Forest / XGBoost) --------
    feat_imp_path = os.path.join(CHART_FOLDER, "feature_importance.png")
    if os.path.exists(feat_imp_path):
        charts["feature_importance"] = {
            "file": "charts/feature_importance.png",
            "title": "Top Features (Best Tree-Based Model)",
            "desc": (
                "This chart ranks the most important input features for the best tree-based model "
                "(Random Forest or XGBoost). Features at the top contribute the most to the model's "
                "decisions about whether a student will pass or fail."
            ),
        }

    # -------- 9) ROC Curve --------
    roc_path = os.path.join(CHART_FOLDER, "roc_curve.png")
    if os.path.exists(roc_path):
        charts["roc_curve"] = {
            "file": "charts/roc_curve.png",
            "title": "ROC Curve Comparison (All Models)",
            "desc": (
                "The ROC (Receiver Operating Characteristic) curve compares the trade-off between the "
                "true positive rate and false positive rate across all trained models. A larger area "
                "under the curve (AUC) indicates a better-performing model."
            ),
        }

    return charts


def generate_feedback(df):
    """
    Create human-readable feedback/reasons for pass/fail
    based on averages and overall distribution.
    """
    feedback = []

    total = len(df)
    if total == 0 or "Predicted" not in df.columns:
        return feedback

    # Overall pass rate
    pass_rate = (df["Predicted"] == "yes").mean() * 100.0
    fail_rate = 100.0 - pass_rate
    feedback.append({
        "title": "Overall Pass vs Fail",
        "text": (
            f"In this dataset, about {pass_rate:.1f}% of students are predicted to pass and "
            f"{fail_rate:.1f}% are predicted to fail. This gives a high-level view of how strong "
            "the overall academic performance is for the selected group of students."
        ),
    })

    passed = df[df["Predicted"] == "yes"]
    failed = df[df["Predicted"] == "no"]

    def mean_safe(sub_df, col):
        return sub_df[col].mean() if col in sub_df.columns and not sub_df.empty else None

    # Study time
    mp = mean_safe(passed, "studytime")
    mf = mean_safe(failed, "studytime")
    if mp is not None and mf is not None:
        feedback.append({
            "title": "Study Time Impact",
            "text": (
                f"Students predicted to pass study on average {mp:.2f} (on a 1–4 scale), "
                f"while students predicted to fail study about {mf:.2f}. "
                "This suggests that increasing regular study time can significantly improve "
                "the chances of passing."
            ),
        })

    # Absences
    mp = mean_safe(passed, "absences")
    mf = mean_safe(failed, "absences")
    if mp is not None and mf is not None:
        feedback.append({
            "title": "Absences Impact",
            "text": (
                f"Students predicted to pass have around {mp:.1f} absences on average, "
                f"compared to {mf:.1f} for students predicted to fail. "
                "Higher absence counts are associated with a higher risk of failing, "
                "highlighting the importance of regular attendance."
            ),
        })

    # Previous failures
    mp = mean_safe(passed, "failures")
    mf = mean_safe(failed, "failures")
    if mp is not None and mf is not None:
        feedback.append({
            "title": "Previous Failures",
            "text": (
                f"On average, students predicted to pass have {mp:.2f} previous failures, "
                f"whereas those predicted to fail have {mf:.2f}. "
                "This indicates that students with more past failures are more likely to be at risk, "
                "and may need additional support or intervention."
            ),
        })

    # Going out / socialising
    mp = mean_safe(passed, "goout")
    mf = mean_safe(failed, "goout")
    if mp is not None and mf is not None:
        feedback.append({
            "title": "Social/Going Out Behaviour",
            "text": (
                f"The average 'going out' score (1–5) is {mp:.2f} for students predicted to pass "
                f"and {mf:.2f} for those predicted to fail. Moderate social activity is normal, "
                "but very high levels can reduce study time and lower academic performance."
            ),
        })

    # Alcohol consumption
    mp_d = mean_safe(passed, "Dalc")
    mf_d = mean_safe(failed, "Dalc")
    mp_w = mean_safe(passed, "Walc")
    mf_w = mean_safe(failed, "Walc")
    if mp_d is not None and mf_d is not None and mp_w is not None and mf_w is not None:
        feedback.append({
            "title": "Alcohol Consumption",
            "text": (
                f"Workday alcohol use (1–5) is about {mp_d:.2f} for predicted pass and "
                f"{mf_d:.2f} for predicted fail. Weekend alcohol use is {mp_w:.2f} (pass) vs "
                f"{mf_w:.2f} (fail). Higher alcohol consumption is linked to poorer performance, "
                "especially when combined with low study time and high absence rates."
            ),
        })

    # -------- Strategic Success Plan --------
    if not df.empty and "Probability(%)" in df.columns:
        # Identify "Swing Students" (those between 40% and 60%)
        # They are the most likely to be saved by intervention
        swing_students = df[(df["Probability(%)"] >= 40) & (df["Probability(%)"] <= 60)]
        swing_count = len(swing_students)
        swing_percent = (swing_count / total) * 100
        
        fail_count = len(df[df["Predicted"] == "no"])
        
        text = (
            f"The AI has identified <b>{swing_count} students ({swing_percent:.1f}%)</b> as 'Swing Students'—those on the "
            "border between passing and failing. These students represent your <b>highest ROI for intervention</b>. "
            "A small improvement in their study habits or attendance could flip their result to a PASS."
        )
        
        if fail_count > 0:
            text += (
                f"\n\nTo control the {fail_rate:.1f}% fail rate, we recommend a <b>Tiered Intervention Strategy</b>: "
                "1. Mentorship for Swing Students (40-60% prob). "
                "2. Intensive Tutoring for students with <30% probability."
            )

        feedback.append({
            "title": "Strategic Success Plan",
            "text": text,
        })

    return feedback


def get_model_info():
    """
    Returns info about which algorithm is best and how others performed.
    Supports dynamic reloading of algo_metrics.json.
    """
    metrics_path = os.path.join(os.getcwd(), "algo_metrics.json")
    try:
        with open(metrics_path, "r") as f:
            metrics_data = json.load(f)
    except Exception:
        metrics_data = None

    if not metrics_data:
        return {
            "name": "Unknown Model",
            "details": "Model information is not available.",
            "note": "Run train_model.py again to generate and save algorithm comparison results.",
            "algos": [],
        }

    best_name = metrics_data.get("best_model", "Unknown")
    selection_metric = metrics_data.get("selection_metric", "test_accuracy")
    metrics_dict = metrics_data.get("metrics", {})

    algo_rows = []
    text_lines = []

    for name, m in metrics_dict.items():
        cv_mean = m.get("cv_mean_accuracy", None)
        test_acc = m.get("test_accuracy", 0.0)

        if selection_metric == "cv_mean_accuracy" and cv_mean is not None:
            acc_used = cv_mean
            acc_label = "CV mean accuracy"
        else:
            acc_used = test_acc
            acc_label = "Test accuracy"

        acc_percent = float(acc_used) * 100.0

        prec = float(m.get("precision_pass", 0.0))
        rec = float(m.get("recall_pass", 0.0))
        f1 = float(m.get("f1_pass", 0.0))

        text_lines.append(
            f"{name}: {acc_percent:.2f}% ({acc_label}), "
            f"Precision={prec:.2f}, Recall={rec:.2f}, F1={f1:.2f}"
        )

        algo_rows.append({
            "name": name,
            "accuracy": round(acc_percent, 2),
            "precision": round(prec, 2),
            "recall": round(rec, 2),
            "f1": round(f1, 2),
            "is_best": (name == best_name),
        })

    if selection_metric == "cv_mean_accuracy":
        metric_text = (
            "The best model is selected using cross-validation mean accuracy "
            "(StratifiedKFold), which is more reliable for small datasets."
        )
    else:
        metric_text = (
            "The best model is selected based on its accuracy on the held-out test set."
        )

    details = (
        "The system evaluates multiple supervised learning algorithms on the student performance "
        "dataset: Logistic Regression, Support Vector Machines (with linear and RBF kernels), "
        "Random Forest, and XGBoost. These models are trained on the same preprocessed data and "
        "their performance is compared using accuracy, precision, recall and F1-score. "
        f"For this dataset, the best-performing algorithm is <b>{best_name}</b>. "
        + metric_text
    )

    note = (
        "Detailed performance of each algorithm:\n"
        + "\n".join(text_lines)
        + "\n\n"
          "• Logistic Regression: A simple and interpretable linear baseline model.\n"
          "• SVM (linear / RBF): Handles both linear and non-linear decision boundaries.\n"
          "• Random Forest: An ensemble of decision trees, very effective on tabular data.\n"
          "• XGBoost: A powerful gradient boosting algorithm, often strong on structured data."
    )

    return {
        "name": best_name,
        "details": details,
        "note": note,
        "algos": algo_rows,
    }


def run_predictions_on_dataframe(df):
    """
    Helper to run predictions on a dataframe and return:
    df_with_preds, out_path, charts, feedback
    """
    required_cols = list(MODEL.feature_names_in_)
    missing = [c for c in required_cols if c not in df.columns]

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    preds = MODEL.predict(df[required_cols])
    probs = MODEL.predict_proba(df[required_cols])[:, 1]

    df = df.copy()
    df["Predicted"] = ["yes" if p == 1 else "no" for p in preds]
    df["Probability(%)"] = (probs * 100).round(2)

    out_name = f"prediction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    out_path = os.path.join(OUTPUT_FOLDER, out_name)
    df.to_csv(out_path, index=False)

    charts = create_charts(df)
    feedback = generate_feedback(df)

    return df, out_path, charts, feedback


def load_default_dataset_results():
    """
    Load the default student dataset, run predictions,
    and return (table_html, out_path, charts, feedback, error).
    This is used for the first view when the page loads.
    """
    if not os.path.exists(DEFAULT_DATA_FILE):
        return None, None, None, None, "Default dataset file not found on server."

    try:
        if DEFAULT_DATA_FILE.endswith(".csv"):
            df = pd.read_csv(DEFAULT_DATA_FILE)
        elif DEFAULT_DATA_FILE.endswith((".xlsx", ".xls")):
            df = pd.read_excel(DEFAULT_DATA_FILE)
        else:
            return None, None, None, None, "Default dataset must be CSV or Excel."
    except Exception as e:
        return None, None, None, None, f"Error reading default dataset: {e}"

    try:
        df_pred, out_path, charts, feedback = run_predictions_on_dataframe(df)
    except Exception as e:
        return None, None, None, None, str(e)

    table_html = df_pred.head(20).to_html(
        classes="table table-bordered table-striped table-sm",
        index=False,
    )
    return table_html, out_path, charts, feedback, None


@app.route("/", methods=["GET", "POST"])
def upload_file():
    result_table = None
    download_file = None
    charts = None
    feedback = None
    model_info = get_model_info()
    error = None

    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            error = "Please select a CSV or Excel file to upload."
            return render_template(
                "upload.html",
                error=error,
                charts=charts,
                table=result_table,
                download_link=download_file,
                feedback=feedback,
                model_info=model_info,
                train_table=TRAIN_TABLE_HTML,
                active_tab="upload"
            )

        filename = file.filename
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)

        # Read CSV or Excel
        try:
            if filename.endswith(".csv"):
                df = pd.read_csv(path)
            elif filename.endswith((".xlsx", ".xls")):
                df = pd.read_excel(path)
            else:
                error = "Only CSV (.csv) or Excel (.xlsx, .xls) files are allowed."
                return render_template(
                    "upload.html",
                    error=error,
                    charts=charts,
                    table=result_table,
                    download_link=download_file,
                    feedback=feedback,
                    model_info=model_info,
                    train_table=TRAIN_TABLE_HTML,
                    active_tab="upload"
                )
        except Exception as e:
            error = f"Error reading file: {e}"
            return render_template(
                "upload.html",
                error=error,
                charts=charts,
                table=result_table,
                download_link=download_file,
                feedback=feedback,
                model_info=model_info,
                train_table=TRAIN_TABLE_HTML,
                active_tab="upload"
            )

        # Predict using helper
        try:
            df_pred, out_path, charts, feedback = run_predictions_on_dataframe(df)
        except Exception as e:
            error = str(e)
            return render_template(
                "upload.html",
                error=error,
                charts=None,
                table=None,
                download_link=None,
                feedback=None,
                model_info=model_info,
                train_table=TRAIN_TABLE_HTML,
                active_tab="upload"
            )

        result_table = df_pred.head(20).to_html(
            classes="table table-bordered table-striped table-sm",
            index=False,
        )
        download_file = out_path

        return render_template(
            "upload.html",
            table=result_table,
            download_link=download_file,
            charts=charts,
            feedback=feedback,
            model_info=model_info,
            error=error,
            train_table=TRAIN_TABLE_HTML,
            active_tab="upload"
        )

    # GET request -> show default dataset and its results if available
    result_table, download_file, charts, feedback, error_default = load_default_dataset_results()
    if error_default and not error:
        error = error_default

    return render_template(
        "upload.html",
        error=error,
        charts=charts,
        table=result_table,
        download_link=download_file,
        feedback=feedback,
        model_info=model_info,
        train_table=TRAIN_TABLE_HTML,
        active_tab="upload"
    )


def get_individual_insights(student_row):
    """
    Generate deep insights and actionable tips for a single student.
    """
    insights = {
        "strengths": [],
        "risks": [],
        "factors": [],
        "tips": []
    }
    
    # Impact mapping and Tip generation logic
    factors = [
        {
            "id": "studytime", "label": "Study Effort", "val": float(student_row["studytime"]), 
            "low": 1, "high": 4, "inverse": False,
            "tip": "Commit to at least 10+ hours of focused study per week. Break sessions into 50-minute blocks with 10-minute breaks to maximize retention."
        },
        {
            "id": "absences", "label": "Attendance", "val": float(student_row["absences"]), 
            "low": 0, "high": 20, "inverse": True,
            "tip": "Maintain an attendance rate above 95%. Missing just two consecutive classes can lead to a 15% drop in comprehension of core concepts."
        },
        {
            "id": "failures", "label": "Academic Foundation", "val": float(student_row["failures"]), 
            "low": 0, "high": 3, "inverse": True,
            "tip": "Schedule weekly 'foundation sessions' to review prerequisite materials from past subjects where difficulties occurred."
        },
        {
            "id": "goout", "label": "Social Balance", "val": float(student_row["goout"]), 
            "low": 1, "high": 5, "inverse": True,
            "tip": "Limit high-intensity social activities to weekends only. Try the 'Work First, Play Later' rule to ensure assignments are completed before socializing."
        },
        {
            "id": "Dalc", "label": "Daily Caffeine Habit", "val": float(student_row["Dalc"]), 
            "low": 0, "high": 5, "inverse": True,
            "tip": "Avoid excessive caffeine consumption during the school week. Even moderate levels late in the day can disrupt REM sleep."
        },
        {
            "id": "Walc", "label": "Weekend Caffeine Habit", "val": float(student_row["Walc"]), 
            "low": 0, "high": 5, "inverse": True,
            "tip": "Moderate weekend caffeine habits. Ensure that late-night consumption does not spill into Sunday evening."
        },
        {
            "id": "health", "label": "Physical Wellness", "val": float(student_row["health"]), 
            "low": 1, "high": 5, "inverse": False,
            "tip": "Prioritize 7-8 hours of sleep. Physical health is the engine of cognitive performance; consider light exercise to boost brain oxygenation."
        },
        {
            "id": "famsup", "label": "Family Academic Support", "val": float(2 if student_row.get("famsup", "yes") == "yes" else 0), 
            "low": 0, "high": 2, "inverse": False,
            "tip": "If home academic support is limited, proactively seek mentorship from teachers or join a specialized after-school study group."
        },
    ]

    # Calculate impacts and sort by 'criticality' (lowest impact first for risks)
    calculated_factors = []
    for f in factors:
        val = f["val"]
        if f["inverse"]:
            # Range 0 to high
            impact = max(-100, min(100, ((f["high"] - val) / f["high"] * 200) - 100))
        else:
            # Range low to high
            denom = (f["high"] - f["low"]) if (f["high"] - f["low"]) != 0 else 1
            impact = max(-100, min(100, ((val - f["low"]) / denom * 200) - 100))
            
        calculated_factors.append({
            "label": f["label"],
            "impact": impact,
            "val_display": int(val) if val.is_integer() else val,
            "tip": f["tip"]
        })

    # Sort so negative impacts (risks) come first in our internal processing
    calculated_factors.sort(key=lambda x: x["impact"])

    for cf in calculated_factors:
        insights["factors"].append({
            "label": cf["label"],
            "impact": cf["impact"],
            "val_display": cf["val_display"]
        })
        
        if cf["impact"] > 40:
            insights["strengths"].append(cf["label"])
        elif cf["impact"] < 0:
            insights["risks"].append(cf["label"])
            # Only add the tip if it's significant enough or we have few tips
            if cf["impact"] < -20 or len(insights["tips"]) < 2:
                insights["tips"].append(cf["tip"])

    # High-Priority / Strategic Tip: If the most negative factor is very bad, emphasize it
    if calculated_factors[0]["impact"] < -50:
        priority_tip = f"CRITICAL PRIORITY: {calculated_factors[0]['tip']}"
        if priority_tip not in insights["tips"]:
            insights["tips"].insert(0, priority_tip)

    # Default tip if everything is perfect
    if not insights["tips"]:
        insights["tips"].append("Maintain your current high-performance habits. Consider mentoring a peer to further solidify your own mastery of the subjects.")

    return insights


@app.route("/predict_manual", methods=["POST"])
def predict_manual():
    """
    Handle single student prediction from manual form entry with deep explanation.
    """
    model_info = get_model_info()
    
    try:
        data_dict = {}
        required_cols = list(MODEL.feature_names_in_)
        num_cols = [
            "age", "Medu", "Fedu", "traveltime", "studytime",
            "failures", "famrel", "freetime", "goout",
            "Dalc", "Walc", "health", "absences",
        ]

        for col in required_cols:
            val = request.form.get(col)
            if val is None:
                raise ValueError(f"Missing field: {col}")
            
            if col in num_cols:
                data_dict[col] = [float(val)]
            else:
                data_dict[col] = [val]

        df = pd.DataFrame(data_dict)
        df_pred, _, charts, feedback = run_predictions_on_dataframe(df)
        
        # New: Get deep insights for the single student
        individual_insights = get_individual_insights(df.iloc[0])
        
        # Result data for the UI
        prediction = df_pred.iloc[0]["Predicted"]
        probability = df_pred.iloc[0]["Probability(%)"]

        result_table = df_pred.to_html(
            classes="table table-bordered table-striped",
            index=False,
        )

        # Ensure all data is serializable and handle potential lists
        clean_student_data = {}
        for k, v in data_dict.items():
            val = v[0] if isinstance(v, list) else v
            # Ensure numbers stay numbers for insights calculation later if needed, 
            # but here we just want a clean dict for the PDF
            clean_student_data[k] = val

        return render_template(
            "upload.html",
            table=result_table,
            charts=charts,
            feedback=feedback,
            model_info=model_info,
            active_tab="manual",
            train_table=TRAIN_TABLE_HTML,
            individual_result={
                "prediction": prediction,
                "probability": probability,
                "insights": individual_insights,
                "student_data": clean_student_data,
            }
        )

    except Exception as e:
        return render_template(
            "upload.html",
            error=f"Prediction error: {str(e)}",
            model_info=model_info,
            active_tab="manual",
            train_table=TRAIN_TABLE_HTML,
        )


@app.route("/download")
def download_file():
    """
    Download the complete prediction CSV file.
    The 'file' query parameter should be the absolute path of the saved output CSV.
    """
    file_path = request.args.get("file", "")
    if not file_path:
        return "No file specified.", 400

    # Security: ensure path stays inside the outputs folder
    real_path = os.path.realpath(file_path)
    real_output = os.path.realpath(OUTPUT_FOLDER)
    if not real_path.startswith(real_output):
        return "Invalid file path.", 400

    if not os.path.exists(real_path):
        return "File not found.", 404

    filename = os.path.basename(real_path)
    return send_file(real_path, as_attachment=True, download_name=filename, mimetype="text/csv")


@app.route("/download_csv", methods=["POST"])
def download_csv_post():
    """OBSOLETE: User requested no CSV download."""
    return "CSV download disabled.", 410

class PredictionPDF(FPDF):
    """Custom FPDF subclass with branded header/footer."""

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_y(15)  # Start header block near the absolute page top
        self.set_fill_color(99, 102, 241)   # indigo
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, "  StudentLens - Student Performance Prediction Report",
                  border=0, align="L", fill=True)
        self.ln(15)  # Make sure the cursor moves cleanly past the header block
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10,
                  f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}   |   Page {self.page_no()}",
                  align="C")


def _build_pdf(df_pred, charts, feedback):
    """
    Build and return a PredictionPDF byte-string.
    df_pred  : full DataFrame with Predicted + Probability(%) columns
    charts   : dict from create_charts()
    feedback : list from generate_feedback()
    """

    # ── Unicode → ASCII sanitizer (fpdf2 built-in fonts are Latin-1 only) ──
    _UNICODE_MAP = {
        "\u2013": "-", "\u2014": "-",   # en/em dash
        "\u2018": "'", "\u2019": "'",   # left/right single quote
        "\u201c": '"', "\u201d": '"',   # left/right double quote
        "\u2026": "...",                # ellipsis
        "\u00b7": ".",                  # middle dot
        "\u2022": "*",                  # bullet
        "\u00a0": " ",                  # non-breaking space
    }

    def sanitize(text):
        if not isinstance(text, str):
            text = str(text)
        for src, dst in _UNICODE_MAP.items():
            text = text.replace(src, dst)
        # Final safety: drop anything outside Latin-1
        return text.encode("latin-1", errors="replace").decode("latin-1")

    pdf = PredictionPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(left=12, top=18, right=12)

    # ── COVER PAGE ────────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(99, 102, 241)
    pdf.ln(20)
    pdf.cell(0, 12, "Student Performance Prediction", align="C")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 8, "Complete Analysis Report", align="C")
    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 8, datetime.now().strftime("%d %B %Y, %H:%M"), align="C")
    pdf.ln(14)

    # Summary statistics box
    total = len(df_pred)
    passed = int((df_pred["Predicted"] == "yes").sum())
    failed = total - passed
    pass_pct = (passed / total * 100) if total else 0

    pdf.set_fill_color(238, 240, 255)
    pdf.set_draw_color(99, 102, 241)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(60, 60, 60)
    box_x = 60
    pdf.set_x(box_x)
    pdf.cell(180, 8, "  Summary Statistics", border="LTR", fill=True, align="L")
    pdf.ln(8)
    for label, value in [
        ("Total Students",  str(total)),
        ("Predicted PASS",  f"{passed}  ({pass_pct:.1f}%)"),
        ("Predicted FAIL",  f"{failed}  ({100-pass_pct:.1f}%)"),
    ]:
        pdf.set_x(box_x)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(90, 7, f"  {label}", border="L", fill=True)
        pdf.cell(90, 7, value, border="R", fill=True)
        pdf.ln(7)
    pdf.set_x(box_x)
    pdf.cell(180, 0, "", border="B")
    pdf.ln(4)

    # ── CHARTS PAGE(S) ────────────────────────────────────────────────
    chart_keys_ordered = [
        "predicted_counts", "studytime_by_pred", "absences_hist",
        "failures_by_pred", "algo_comparison", "feature_importance",
        "confusion_matrix_raw", "confusion_matrix_norm",
        "corr_heatmap", "roc_curve",
    ]

    # Gather existing chart paths
    chart_items = []
    for key in chart_keys_ordered:
        if key in charts:
            img_path = os.path.join(BASE_DIR, "static", charts[key]["file"])
            if os.path.exists(img_path):
                chart_items.append((charts[key]["title"], charts[key]["desc"], img_path))
    # Also catch any extra charts not in our ordered list
    for key, info in charts.items():
        if key not in chart_keys_ordered:
            img_path = os.path.join(BASE_DIR, "static", info["file"])
            if os.path.exists(img_path):
                chart_items.append((info["title"], info["desc"], img_path))

    # Two charts per row on landscape A4 (270 mm usable width)
    if chart_items:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 15)
        pdf.set_text_color(99, 102, 241)
        pdf.cell(0, 10, "Visual Analytics", align="L")
        pdf.ln(2)
        pdf.set_draw_color(200, 200, 220)
        pdf.set_line_width(0.3)
        pdf.line(12, pdf.get_y(), 285, pdf.get_y())
        pdf.ln(6)

        col_w = 130
        gap = 8
        img_h = 72
        start_x = 12

        for idx, (title, desc, img_path) in enumerate(chart_items):
            col = idx % 2
            if col == 0 and idx != 0:
                pdf.ln(img_h + 20)
            if col == 0:
                if pdf.get_y() + img_h + 22 > 190:
                    pdf.add_page()
                    pdf.set_font("Helvetica", "B", 15)
                    pdf.set_text_color(99, 102, 241)
                    pdf.cell(0, 10, "Visual Analytics (continued)", align="L")
                    pdf.ln(8)

            x_pos = start_x + col * (col_w + gap)
            y_pos = pdf.get_y()

            # Chart title
            pdf.set_xy(x_pos, y_pos)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(50, 50, 50)
            pdf.cell(col_w, 5, sanitize(title), align="L")

            # Image
            pdf.image(img_path, x=x_pos, y=y_pos + 6, w=col_w, h=img_h)

            # Description below image
            pdf.set_xy(x_pos, y_pos + img_h + 8)
            pdf.set_font("Helvetica", "I", 7)
            pdf.set_text_color(120, 120, 120)
            pdf.multi_cell(col_w, 3.5, sanitize(desc), align="L")

            # Reset Y for right-column to align with left
            if col == 0:
                pdf.set_xy(start_x, y_pos)

    # ── FEEDBACK / INSIGHTS ───────────────────────────────────────────
    if feedback:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 15)
        pdf.set_text_color(99, 102, 241)
        pdf.cell(0, 10, "Strategic Insights", align="L")
        pdf.ln(2)
        pdf.set_draw_color(200, 200, 220)
        pdf.line(12, pdf.get_y(), 285, pdf.get_y())
        pdf.ln(6)

        for item in feedback:
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(50, 50, 200)
            pdf.cell(0, 6, sanitize(item["title"]), align="L")
            pdf.ln(5)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(60, 60, 60)
            pdf.multi_cell(0, 5, sanitize(item["text"]), align="L")
            pdf.ln(4)

    # ── AI Model Validity (NEW) ─────────────────────────────
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(99, 102, 241)
    pdf.cell(0, 10, "AI Model Performance & Validity", align="L")
    pdf.ln(2)
    pdf.set_draw_color(200, 200, 220)
    pdf.line(12, pdf.get_y(), 285, pdf.get_y())
    pdf.ln(8)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(80, 80, 80)
    validation_text = (
        "The predictions in this report are powered by a high-accuracy machine learning model. "
        "Below are the performance metrics that validate the system's reliability for this dataset."
    )
    pdf.multi_cell(0, 5, validation_text)
    pdf.ln(10)

    # Charts for Validity (Landscape)
    img_w = 110
    img_h = 75
    left_x = 15
    right_x = 135
    chart_y = pdf.get_y()

    # 1. Confusion Matrix
    if "confusion_matrix_norm" in charts:
        cm_path = os.path.join(BASE_DIR, "static", charts["confusion_matrix_norm"]["file"])
        if os.path.exists(cm_path):
            pdf.set_xy(left_x, chart_y)
            pdf.image(cm_path, w=img_w, h=img_h)
            pdf.set_xy(left_x, chart_y + img_h + 2)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(img_w, 5, "Normalized Confusion Matrix (Self-Validation)", align="C")

    # 2. Algorithm Comparison
    if "algo_comparison" in charts:
        algo_path = os.path.join(BASE_DIR, "static", charts["algo_comparison"]["file"])
        if os.path.exists(algo_path):
            pdf.set_xy(right_x, chart_y)
            pdf.image(algo_path, w=img_w, h=img_h)
            pdf.set_xy(right_x, chart_y + img_h + 2)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(img_w, 5, "Model Accuracy Comparison", align="C")

    pdf.ln(20)
    
    # 3. Feature Importance (Centered below)
    if "feature_importance" in charts:
        fi_path = os.path.join(BASE_DIR, "static", charts["feature_importance"]["file"])
        if os.path.exists(fi_path):
            curr_y = pdf.get_y()
            if curr_y > 150:
                pdf.add_page()
                curr_y = 30
            pdf.set_xy(left_x + 75, curr_y)
            pdf.image(fi_path, w=img_w, h=img_h)
            pdf.set_xy(left_x + 75, curr_y + img_h + 2)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(img_w, 5, "Critical Performance Drivers (Feature Importance)", align="C")

    # ── FINAL OUTPUT ──────────────────────────────────────────────────
    # dataset table intentionally omitted — PDF shows results only
    try:
        # fpdf2: returns bytes
        return pdf.output()
    except Exception:
        # original fpdf: dest='S' returns string
        # then encode to bytes for BytesIO
        out = pdf.output(dest='S')
        if isinstance(out, (bytes, bytearray)):
            return out
        return out.encode("latin-1")


def _build_manual_pdf(prediction, probability, insights, student_data):
    """
    Build a compact PDF for a single manual-entry student result.
    prediction   : 'yes' or 'no'
    probability  : float (%)
    insights     : dict from get_individual_insights()
    student_data : dict of entered field values
    """
    # ── Unicode → ASCII sanitizer
    _UNICODE_MAP = {
        "\u2013": "-", "\u2014": "-",
        "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"',
        "\u2026": "...",
        "\u00b7": ".",
        "\u2022": "*",
        "\u00a0": " ",
    }

    def sanitize(text):
        if not isinstance(text, str):
            text = str(text)
        for src, dst in _UNICODE_MAP.items():
            text = text.replace(src, dst)
        return text.encode("latin-1", errors="replace").decode("latin-1")

    pdf = PredictionPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(left=15, top=18, right=15)
    pdf.add_page()

    # ── Title ────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(99, 102, 241)
    pdf.ln(10)
    pdf.cell(0, 10, "Individual Student Prediction", align="C")
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 6, datetime.now().strftime("%d %B %Y, %H:%M"), align="C")
    pdf.ln(12)

    # ── Result Box ───────────────────────────────────────────────────
    result_label = "PASS" if prediction == "yes" else "FAIL"
    r, g, b = (22, 163, 74) if prediction == "yes" else (220, 38, 38)
    pdf.set_fill_color(r, g, b)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 14, f"  Prediction: {result_label}   |   Confidence: {probability}%", fill=True, align="C")
    pdf.ln(10)

    def section_header(title):
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_fill_color(240, 244, 255)
        pdf.set_text_color(67, 56, 202)
        pdf.set_draw_color(99, 102, 241)
        pdf.set_line_width(0.8)
        pdf.cell(180, 10, f"  {title}", border="L", fill=True, align="L")
        pdf.ln(14)

    # ── AI Strategic Analysis (NEW) ──────────────────────────────────
    label_text = "Strategic Success Plan" if prediction == "no" else "AI Prediction Rationale"
    section_header(label_text)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(60, 60, 60)
    
    # Synthesize rationale based on prediction and insights
    risks = insights.get("risks", [])
    strengths = insights.get("strengths", [])
    
    if prediction == "yes":
        rationale = (
            f"Based on our predictive models, this student is likely to PASS with a confidence score of {probability}%. "
            "This positive outlook is primarily driven by "
        )
        if strengths:
            rationale += f"strong performance in factors like {', '.join(strengths[:3])}. "
        else:
            rationale += "a balanced profile across typical academic indicators. "
        
        if risks:
            rationale += (
                f"To further increase the passing probability, we suggest addressing minor concerns in {', '.join(risks[:2])}."
            )
    else:
        rationale = (
            f"The AI system predicts that this student is currently AT RISK of failing (Confidence: {probability}%). "
            f"Our analysis identifies '{risks[0] if risks else 'General Risk factors'}' as the primary area for intervention. "
        )
        if risks:
            rationale += f"Contributing risk factors include {', '.join(risks[:3])}. "
        
        rationale += (
            "We believe that immediate, targeted intervention in these areas can successfully shift this student "
            "toward a passing trajectory. Implementing the Action Plan below is highly recommended."
        )

    pdf.multi_cell(0, 5, sanitize(rationale), align="L")
    pdf.ln(8)

    # ── Key Input Values ─────────────────────────────────────────────
    section_header("Key Input Values")

    display_fields = [
        ("school", "School"),
        ("sex", "Gender"),
        ("age", "Age"),
        ("studytime", "Study Time (1-4)"),
        ("failures", "Past Failures"),
        ("absences", "Absences"),
        ("goout", "Going Out (1-5)"),
        ("health", "Health (1-5)"),
        ("Dalc", "Daily Caffeine (1-5)"),
        ("Walc", "Weekend Caffeine (1-5)"),
        ("famsup", "Family Academic Support"),
        ("higher", "Higher Ed Aspiration"),
    ]
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(50, 50, 50)
    col_w = 90
    
    # Filter and draw table
    table_data = []
    for field, label in display_fields:
        val = student_data.get(field, "-")
        # Handle formatting for some fields
        if field == "higher":
            val = "Yes" if str(val).lower() == "yes" else "No"
        elif field == "sex":
            val = "Female" if str(val).upper() == "F" else "Male"
        elif field == "school":
            val = "Gabriel Pereira" if str(val) == "GP" else "Mousinho da Silveira"
            
        table_data.append((label, val))

    pdf.set_draw_color(220, 225, 240)
    for idx, (label, val) in enumerate(table_data):
        fill = idx % 2 == 0
        pdf.set_fill_color(248, 250, 255) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.cell(col_w, 8, f"  {label}", border="B", fill=fill)
        pdf.cell(col_w, 8, sanitize(str(val)), border="B", fill=fill, align="C")
        pdf.ln(8)
    pdf.ln(10)

    # ── Factor Impact Analysis ────────────────────────────────────────
    if insights.get("factors"):
        section_header("Factor Impact Analysis")
        
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 4, "Impact represents the relative influence (positive/negative) of each factor on the prediction.", align="L")
        pdf.ln(6)

        for f in insights["factors"]:
            impact = f["impact"]
            label = sanitize(f["label"])
            val_display = sanitize(str(f["val_display"]))
            impact_str = f"{impact:+.0f}% Impact"
            
            color = (22, 163, 74) if impact > 0 else (220, 38, 38)
            
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(50, 50, 50)
            pdf.cell(80, 6, f"{label} (Value: {val_display})")
            
            pdf.set_text_color(*color)
            pdf.cell(100, 6, impact_str, align="R")
            pdf.ln(6)
            
            # Draw a subtle bar background
            bar_w = 180
            bar_h = 3
            pdf.set_fill_color(235, 235, 245)
            pdf.rect(pdf.get_x(), pdf.get_y(), bar_w, bar_h, "F")
            
            # Draw actual impact bar
            fill_w = abs(impact) * (bar_w / 100)
            pdf.set_fill_color(*color)
            if impact > 0:
                pdf.rect(pdf.get_x() + (bar_w/2), pdf.get_y(), fill_w/2, bar_h, "F")
            else:
                pdf.rect(pdf.get_x() + (bar_w/2) - (fill_w/2), pdf.get_y(), fill_w/2, bar_h, "F")
            
            pdf.ln(4)
        pdf.ln(6)

    # ── Strengths & Risks ─────────────────────────────────────────────
    strengths = insights.get("strengths", [])
    risks = insights.get("risks", [])
    if strengths or risks:
        section_header("Strengths & Risks Breakdown")
        
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(22, 163, 74)
        pdf.cell(90, 8, "    Positive Drivers", align="L")
        pdf.set_text_color(220, 38, 38)
        pdf.cell(90, 8, "    Risk Indicators", align="L")
        pdf.ln(8)
        
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(60, 60, 60)
        max_rows = max(len(strengths), len(risks), 1)
        for i in range(max_rows):
            s = sanitize(strengths[i]) if i < len(strengths) else "-"
            r = sanitize(risks[i]) if i < len(risks) else "-"
            pdf.cell(90, 6, f"      [+] {s}")
            pdf.cell(90, 6, f"      [-] {r}")
            pdf.ln(6)
        pdf.ln(8)

    # ── Action Plan / Tips ────────────────────────────────────────────
    tips = insights.get("tips", [])
    if tips:
        pdf.add_page()
        section_header("Personalized Action Plan for Success")
        
        for tip in tips:
            # Tip box
            pdf.set_fill_color(250, 251, 255)
            pdf.set_draw_color(220, 225, 255)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(99, 102, 241)
            pdf.cell(0, 6, "  Recommended Intervention:", border="LTR", fill=True, align="L")
            pdf.ln(6)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(50, 50, 50)
            pdf.multi_cell(0, 6, sanitize(f"  {tip}"), border="LBR", fill=True, align="L")
            pdf.ln(6)

    # ── Model Performance Analytics (NEW) ─────────────────────────────
    # Include charts to show the user the model's overall validity
    pdf.add_page()
    section_header("AI Model Performance & Validity")

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(80, 80, 80)
    validation_text = (
        "This prediction is powered by a high-accuracy machine learning model trained on historical "
        "student data. Below are the performance metrics that validate the system's reliability."
    )
    pdf.multi_cell(0, 5, validation_text)
    pdf.ln(5)

    chart_y = pdf.get_y()
    left_x = 15
    right_x = 105
    img_w = 85
    img_h = 60

    # 1. Confusion Matrix
    cm_path = os.path.join(CHART_FOLDER, "confusion_matrix_norm.png")
    if os.path.exists(cm_path):
        pdf.set_xy(left_x, chart_y)
        pdf.image(cm_path, w=img_w, h=img_h)
        pdf.set_xy(left_x, chart_y + img_h + 2)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(img_w, 5, "Normalized Confusion Matrix", align="C")

    # 2. Algorithm Comparison
    algo_path = os.path.join(CHART_FOLDER, "algo_comparison.png")
    if os.path.exists(algo_path):
        pdf.set_xy(right_x, chart_y)
        pdf.image(algo_path, w=img_w, h=img_h)
        pdf.set_xy(right_x, chart_y + img_h + 2)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(img_w, 5, "Algorithm Accuracy Comparison", align="C")

    pdf.ln(15)
    
    # Feature Importance (if tree-based model)
    fi_path = os.path.join(CHART_FOLDER, "feature_importance.png")
    if os.path.exists(fi_path):
        curr_y = pdf.get_y()
        if curr_y > 220:
            pdf.add_page()
            curr_y = 20
        pdf.set_xy(left_x + 45, curr_y) # Center it slightly
        pdf.image(fi_path, w=img_w, h=img_h)
        pdf.set_xy(left_x + 45, curr_y + img_h + 2)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(img_w, 5, "General Feature Importance (Model Level)", align="C")

    # ── FINAL OUTPUT ──────────────────────────────────────────────────
    try:
        # fpdf2: returns bytes
        return pdf.output()
    except Exception:
        # original fpdf: dest='S' returns string
        out = pdf.output(dest='S')
        if isinstance(out, (bytes, bytearray)):
            return out
        return out.encode("latin-1")


@app.route("/export_pdf", methods=["POST"])
def export_pdf():
    """
    Generate and download a PDF report with summary stats, charts, and insights
    (no raw dataset table). Expects POST with 'file' = path to saved prediction CSV.
    """
    file_path = request.form.get("file", "")
    if not file_path:
        return "No prediction file specified.", 400

    real_path = os.path.realpath(file_path)
    real_output = os.path.realpath(OUTPUT_FOLDER)
    if not real_path.startswith(real_output) or not os.path.exists(real_path):
        return "Invalid or missing prediction file.", 400

    try:
        df_pred = pd.read_csv(real_path)
    except Exception as e:
        return f"Could not read prediction data: {e}", 500

    charts = create_charts(df_pred)
    feedback = generate_feedback(df_pred)

    try:
        pdf_bytes = _build_pdf(df_pred, charts, feedback)
        if not isinstance(pdf_bytes, (bytes, bytearray)):
             # If builder returned the object instead of bytes, try to cast
             if hasattr(pdf_bytes, "output"):
                 # Try fpdf2 first
                 try:
                     pdf_bytes = pdf_bytes.output()
                 except:
                     pdf_bytes = pdf_bytes.output(dest='S').encode('latin-1')
             else:
                 pdf_bytes = str(pdf_bytes).encode('latin-1')
    except Exception as e:
        import traceback
        return f"PDF generation failed: {e}\n{traceback.format_exc()}", 500

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    download_name = f"StudentLens_Report_{timestamp}.pdf"

    return send_file(
        io.BytesIO(pdf_bytes),
        as_attachment=True,
        download_name=download_name,
        mimetype="application/pdf",
    )


@app.route("/export_pdf_manual", methods=["POST"])
def export_pdf_manual():
    """
    Generate and download a PDF for a single manual-entry student result.
    Expects POST fields: prediction, probability, insights (JSON), student_data (JSON).
    """
    try:
        prediction = request.form.get("prediction", "no")
        probability_str = request.form.get("probability", "0")
        try:
            probability = float(probability_str)
        except ValueError:
            probability = 0.0

        insights_raw = request.form.get("insights", "{}")
        student_data_raw = request.form.get("student_data", "{}")

        try:
            insights = json.loads(insights_raw)
        except json.JSONDecodeError as je:
            print(f"JSON error in insights: {je}")
            # Try a second pass if it was double-encoded or escaped
            insights = {}

        try:
            student_data = json.loads(student_data_raw)
        except json.JSONDecodeError as je:
            print(f"JSON error in student_data: {je}")
            student_data = {}

    except Exception as e:
        return f"Invalid form data: {e}", 400

    try:
        result = _build_manual_pdf(prediction, probability, insights, student_data)
        if not isinstance(result, (bytes, bytearray)):
             if hasattr(result, "output"):
                 try:
                     pdf_bytes = result.output()
                 except:
                     pdf_bytes = result.output(dest='S').encode('latin-1')
             else:
                 pdf_bytes = str(result).encode('latin-1')
        else:
            pdf_bytes = result
    except Exception as e:
        import traceback
        error_msg = f"PDF generation failed: {e}\n{traceback.format_exc()}"
        print(error_msg)
        return error_msg, 500

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    download_name = f"StudentLens_Manual_{timestamp}.pdf"

    return send_file(
        io.BytesIO(pdf_bytes),
        as_attachment=True,
        download_name=download_name,
        mimetype="application/pdf",
    )


@app.route("/research")
def research():
    return render_template("research.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)

