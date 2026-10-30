import joblib
import pandas as pd
import numpy as np

from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
)


DATASET_PATH = "../ethereum_fraud_detection/transaction_dataset.csv"
MODEL_PATH = "models/fraud_detection_rf_kaggle.joblib"
FEATURES_PATH = "models/fraud_detection_rf_kaggle_features.joblib"


def normalize_column(name):
    """
    Convert dataset column names into the naming convention
    used by the trained Random Forest.
    """
    name = str(name).strip()

    replacements = {
        "Avg min between sent tnx": "Avg_min_between_sent_tnx",
        "Avg min between received tnx": "Avg_min_between_received_tnx",
        "Time Diff between first and last (Mins)": "Time_Diff_between_first_and_last_(Mins)",
        "Sent tnx": "Sent_tnx",
        "Received Tnx": "Received_Tnx",
        "Number of Created Contracts": "Number_of_Created_Contracts",
        "Unique Received From Addresses": "Unique_Received_From_Addresses",
        "Unique Sent To Addresses": "Unique_Sent_To_Addresses",
        "min value received": "min_value_received",
        "max value received": "max_value_received",
        "avg val received": "avg_val_received",
        "min val sent": "min_val_sent",
        "max val sent": "max_val_sent",
        "avg val sent": "avg_val_sent",
        "min value sent to contract": "min_value_sent_to_contract",
        "max val sent to contract": "max_val_sent_to_contract",
        "avg value sent to contract": "avg_value_sent_to_contract",
        "total transactions (including tnx to create contract": "total_transactions_(including_tnx_to_create_contract",
        "total Ether sent": "total_Ether_sent",
        "total ether received": "total_ether_received",
        "total ether sent contracts": "total_ether_sent_contracts",
        "total ether balance": "total_ether_balance",
        "Total ERC20 tnxs": "Total_ERC20_tnxs",
        "ERC20 total Ether received": "ERC20_total_Ether_received",
        "ERC20 total ether sent": "ERC20_total_ether_sent",
        "ERC20 total Ether sent contract": "ERC20_total_Ether_sent_contract",
        "ERC20 uniq sent addr": "ERC20_uniq_sent_addr",
        "ERC20 uniq rec addr": "ERC20_uniq_rec_addr",
        "ERC20 uniq sent addr.1": "ERC20_uniq_sent_addr.1",
        "ERC20 uniq rec contract addr": "ERC20_uniq_rec_contract_addr",
        "ERC20 avg time between sent tnx": "ERC20_avg_time_between_sent_tnx",
        "ERC20 avg time between rec tnx": "ERC20_avg_time_between_rec_tnx",
        "ERC20 avg time between rec 2 tnx": "ERC20_avg_time_between_rec_2_tnx",
        "ERC20 avg time between contract tnx": "ERC20_avg_time_between_contract_tnx",
        "ERC20 min val rec": "ERC20_min_val_rec",
        "ERC20 max val rec": "ERC20_max_val_rec",
        "ERC20 avg val rec": "ERC20_avg_val_rec",
        "ERC20 min val sent": "ERC20_min_val_sent",
        "ERC20 max val sent": "ERC20_max_val_sent",
        "ERC20 avg val sent": "ERC20_avg_val_sent",
        "ERC20 min val sent contract": "ERC20_min_val_sent_contract",
        "ERC20 max val sent contract": "ERC20_max_val_sent_contract",
        "ERC20 avg val sent contract": "ERC20_avg_val_sent_contract",
        "ERC20 uniq sent token name": "ERC20_uniq_sent_token_name",
        "ERC20 uniq rec token name": "ERC20_uniq_rec_token_name",
        "ERC20 most sent token type": "ERC20_most_sent_token_type",
        "ERC20_most_rec_token_type": "ERC20_most_rec_token_type",
    }

    return replacements.get(name, name)


print("=" * 70)
print("KAGGLE FRAUD MODEL VALIDATION")
print("=" * 70)

# ---------------------------------------------------------------------
# 1. Load dataset
# ---------------------------------------------------------------------

print("\nLoading dataset...")

df = pd.read_csv(DATASET_PATH)

print(f"Dataset shape: {df.shape}")

print("\nFLAG distribution:")
print(df["FLAG"].value_counts())

print("\nFLAG percentage:")
print(df["FLAG"].value_counts(normalize=True))

# ---------------------------------------------------------------------
# 2. Load model and exact feature list
# ---------------------------------------------------------------------

print("\nLoading saved Random Forest...")

model = joblib.load(MODEL_PATH)
feature_names = joblib.load(FEATURES_PATH)

print("Model type:", type(model))
print("Model expects:", model.n_features_in_, "features")
print("Feature file contains:", len(feature_names), "features")

# ---------------------------------------------------------------------
# 3. Rename dataset columns
# ---------------------------------------------------------------------

print("\n" + "=" * 70)
print("MAPPING DATASET COLUMNS")
print("=" * 70)

rename_map = {}

for column in df.columns:
    normalized = normalize_column(column)

    if normalized != column:
        rename_map[column] = normalized

df = df.rename(columns=rename_map)

print("\nMapped columns:")

for original, normalized in rename_map.items():
    print(f"  {original!r}")
    print(f"       -> {normalized!r}")

# ---------------------------------------------------------------------
# 4. Check exact feature availability
# ---------------------------------------------------------------------

print("\n" + "=" * 70)
print("CHECKING FEATURE MAPPING")
print("=" * 70)

missing = [
    feature
    for feature in feature_names
    if feature not in df.columns
]

if missing:
    print("\nERROR: Missing features:")

    for feature in missing:
        print("  -", repr(feature))

    raise SystemExit(1)

print("\nSUCCESS: All 47 model features are present.")

# ---------------------------------------------------------------------
# 5. Build X and y
# ---------------------------------------------------------------------

X = df[feature_names].copy()
y = df["FLAG"].astype(int)

print("\nX shape:", X.shape)
print("y shape:", y.shape)

# Convert everything to numeric
for column in X.columns:
    X[column] = pd.to_numeric(X[column], errors="coerce")

# Replace invalid values
X = X.replace([np.inf, -np.inf], np.nan)

# Fill missing values using column medians
X = X.fillna(X.median(numeric_only=True))

# Some columns may still be completely empty
X = X.fillna(0)

print("\nFinal X shape:", X.shape)

# ---------------------------------------------------------------------
# 6. Predictions
# ---------------------------------------------------------------------

print("\n" + "=" * 70)
print("RUNNING MODEL")
print("=" * 70)

predictions = model.predict(X)

probabilities = model.predict_proba(X)[:, 1]

# ---------------------------------------------------------------------
# 7. Metrics
# ---------------------------------------------------------------------

accuracy = accuracy_score(y, predictions)
precision = precision_score(y, predictions, zero_division=0)
recall = recall_score(y, predictions, zero_division=0)
f1 = f1_score(y, predictions, zero_division=0)
auc = roc_auc_score(y, probabilities)

print("\n" + "=" * 70)
print("MODEL PERFORMANCE")
print("=" * 70)

print(f"\nAccuracy : {accuracy:.4f}")
print(f"Precision: {precision:.4f}")
print(f"Recall   : {recall:.4f}")
print(f"F1 Score : {f1:.4f}")
print(f"ROC-AUC  : {auc:.4f}")

# ---------------------------------------------------------------------
# 8. Confusion matrix
# ---------------------------------------------------------------------

print("\n" + "=" * 70)
print("CONFUSION MATRIX")
print("=" * 70)

cm = confusion_matrix(y, predictions)

print(cm)

print("\nFormat:")
print("[[TN FP]")
print(" [FN TP]]")

# ---------------------------------------------------------------------
# 9. Classification report
# ---------------------------------------------------------------------

print("\n" + "=" * 70)
print("CLASSIFICATION REPORT")
print("=" * 70)

print(
    classification_report(
        y,
        predictions,
        target_names=["Normal", "Fraud"],
        zero_division=0,
    )
)

# ---------------------------------------------------------------------
# 10. Prediction distribution
# ---------------------------------------------------------------------

print("=" * 70)
print("PREDICTION DISTRIBUTION")
print("=" * 70)

unique, counts = np.unique(predictions, return_counts=True)

for label, count in zip(unique, counts):
    name = "Fraud" if label == 1 else "Normal"
    print(f"{name}: {count}")

print("\nValidation completed successfully.")