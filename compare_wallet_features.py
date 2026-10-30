import sys
import joblib
import pandas as pd
import numpy as np

sys.path.insert(0, "backend")

from app.services.blockchain_data import (
    get_transactions,
    get_token_transactions,
)
from app.services.features_v2 import compute_features_v2


# ============================================================
# CONFIG
# ============================================================

WALLET = "0x00009277775ac7d0d59eaad8fee3d10ac6c805e8"

DATASET_PATH = "ethereum_fraud_detection/transaction_dataset.csv"
MODEL_PATH = "backend/models/fraud_detection_rf_kaggle.joblib"
FEATURES_PATH = "backend/models/fraud_detection_rf_kaggle_features.joblib"
SENT_ENCODER_PATH = "backend/models/le_sent.joblib"
REC_ENCODER_PATH = "backend/models/le_rec.joblib"


# ============================================================
# FEATURE NAME MAPPING
# ============================================================

mapping = {
    "Avg_min_between_sent_tnx": "Avg min between sent tnx",
    "Avg_min_between_received_tnx": "Avg min between received tnx",
    "Time_Diff_between_first_and_last_(Mins)": "Time Diff between first and last (Mins)",
    "Sent_tnx": "Sent tnx",
    "Received_Tnx": "Received Tnx",
    "Number_of_Created_Contracts": "Number of Created Contracts",
    "Unique_Received_From_Addresses": "Unique Received From Addresses",
    "Unique_Sent_To_Addresses": "Unique Sent To Addresses",
    "min_value_received": "min value received",
    "max_value_received": "max value received ",
    "avg_val_received": "avg val received",
    "min_val_sent": "min val sent",
    "max_val_sent": "max val sent",
    "avg_val_sent": "avg val sent",
    "min_value_sent_to_contract": "min value sent to contract",
    "max_val_sent_to_contract": "max val sent to contract",
    "avg_value_sent_to_contract": "avg value sent to contract",
    "total_transactions_(including_tnx_to_create_contract":
        "total transactions (including tnx to create contract",
    "total_Ether_sent": "total Ether sent",
    "total_ether_received": "total ether received",
    "total_ether_sent_contracts": "total ether sent contracts",
    "total_ether_balance": "total ether balance",
    "Total_ERC20_tnxs": " Total ERC20 tnxs",
    "ERC20_total_Ether_received": " ERC20 total Ether received",
    "ERC20_total_ether_sent": " ERC20 total ether sent",
    "ERC20_total_Ether_sent_contract": " ERC20 total Ether sent contract",
    "ERC20_uniq_sent_addr": " ERC20 uniq sent addr",
    "ERC20_uniq_rec_addr": " ERC20 uniq rec addr",
    "ERC20_uniq_sent_addr.1": " ERC20 uniq sent addr.1",
    "ERC20_uniq_rec_contract_addr": " ERC20 uniq rec contract addr",
    "ERC20_avg_time_between_sent_tnx": " ERC20 avg time between sent tnx",
    "ERC20_avg_time_between_rec_tnx": " ERC20 avg time between rec tnx",
    "ERC20_avg_time_between_rec_2_tnx": " ERC20 avg time between rec 2 tnx",
    "ERC20_avg_time_between_contract_tnx": " ERC20 avg time between contract tnx",
    "ERC20_min_val_rec": " ERC20 min val rec",
    "ERC20_max_val_rec": " ERC20 max val rec",
    "ERC20_avg_val_rec": " ERC20 avg val rec",
    "ERC20_min_val_sent": " ERC20 min val sent",
    "ERC20_max_val_sent": " ERC20 max val sent",
    "ERC20_avg_val_sent": " ERC20 avg val sent",
    "ERC20_min_val_sent_contract": " ERC20 min val sent contract",
    "ERC20_max_val_sent_contract": " ERC20 max val sent contract",
    "ERC20_avg_val_sent_contract": " ERC20 avg val sent contract",
    "ERC20_uniq_sent_token_name": " ERC20 uniq sent token name",
    "ERC20_uniq_rec_token_name": " ERC20 uniq rec token name",
    "ERC20_most_sent_token_type": " ERC20 most sent token type",
    "ERC20_most_rec_token_type": " ERC20_most_rec_token_type",
}


# ============================================================
# LOAD MODEL
# ============================================================

print("=" * 80)
print("LIVE vs KAGGLE FEATURE COMPARISON")
print("=" * 80)

print("\nLoading model...")

model = joblib.load(MODEL_PATH)
feature_names = joblib.load(FEATURES_PATH)
sent_encoder = joblib.load(SENT_ENCODER_PATH)
rec_encoder = joblib.load(REC_ENCODER_PATH)

print("Model expects:", model.n_features_in_)
print("Features:", len(feature_names))


# ============================================================
# LOAD DATASET
# ============================================================

print("\nLoading Kaggle dataset...")

df = pd.read_csv(DATASET_PATH)

match = df[
    df["Address"].astype(str).str.lower()
    == WALLET.lower()
]

if match.empty:
    print("Wallet NOT found in Kaggle dataset.")
    sys.exit(1)

row = match.iloc[0]

print("Wallet found!")
print("Address:", row["Address"])
print("Actual FLAG:", row["FLAG"])


# ============================================================
# ORIGINAL KAGGLE FEATURES
# ============================================================

kaggle_features = {}

for feature in feature_names:

    if feature not in mapping:
        print("Missing mapping for:", feature)
        continue

    original_column = mapping[feature]

    if original_column not in df.columns:
        print("Dataset column missing:", original_column)
        continue

    kaggle_features[feature] = row[original_column]


kaggle_X = pd.DataFrame(
    [[kaggle_features[f] for f in feature_names]],
    columns=feature_names
)


# ============================================================
# ENCODE KAGGLE CATEGORICAL FEATURES
# ============================================================

def encode_value(value, encoder):

    value = str(value)

    known = set(encoder.classes_)

    if value in known:
        return encoder.transform([value])[0]

    return -1


kaggle_X["ERC20_most_sent_token_type"] = encode_value(
    kaggle_X["ERC20_most_sent_token_type"].iloc[0],
    sent_encoder
)

kaggle_X["ERC20_most_rec_token_type"] = encode_value(
    kaggle_X["ERC20_most_rec_token_type"].iloc[0],
    rec_encoder
)

kaggle_X = kaggle_X.apply(pd.to_numeric, errors="coerce")
kaggle_X = kaggle_X.replace([np.inf, -np.inf], np.nan)
kaggle_X = kaggle_X.fillna(0)


# ============================================================
# DATASET MODEL PREDICTION
# ============================================================

kaggle_probability = model.predict_proba(kaggle_X)[0][1]
kaggle_prediction = model.predict(kaggle_X)[0]


print("\n" + "=" * 80)
print("KAGGLE DATASET MODEL RESULT")
print("=" * 80)

print("Actual FLAG:", row["FLAG"])
print("Prediction:", "FRAUD" if kaggle_prediction else "NORMAL")
print("Fraud probability:", round(kaggle_probability, 6))


# ============================================================
# FETCH LIVE DATA
# ============================================================

print("\n" + "=" * 80)
print("FETCHING LIVE WALLET DATA")
print("=" * 80)

tx_df = get_transactions(WALLET, use_cache=True)
token_df = get_token_transactions(WALLET, use_cache=True)

print("Normal transactions:", len(tx_df))
print("Token transactions:", len(token_df))


# ============================================================
# COMPUTE LIVE FEATURES
# ============================================================

print("\nComputing live features...")

live_features = compute_features_v2(
    tx_df,
    token_df,
    WALLET,
    sent_encoder,
    rec_encoder
)


live_X = pd.DataFrame(
    [[live_features.get(f, np.nan) for f in feature_names]],
    columns=feature_names
)

live_X = live_X.apply(pd.to_numeric, errors="coerce")
live_X = live_X.replace([np.inf, -np.inf], np.nan)
live_X = live_X.fillna(0)


# ============================================================
# LIVE MODEL PREDICTION
# ============================================================

live_probability = model.predict_proba(live_X)[0][1]
live_prediction = model.predict(live_X)[0]


print("\n" + "=" * 80)
print("LIVE MODEL RESULT")
print("=" * 80)

print("Prediction:", "FRAUD" if live_prediction else "NORMAL")
print("Fraud probability:", round(live_probability, 6))


# ============================================================
# FEATURE COMPARISON
# ============================================================

comparison = []

for feature in feature_names:

    kaggle_value = kaggle_X.iloc[0][feature]
    live_value = live_X.iloc[0][feature]

    difference = abs(
        float(kaggle_value) - float(live_value)
    )

    if abs(float(kaggle_value)) > 1e-9:
        relative_difference = (
            difference / abs(float(kaggle_value))
        ) * 100
    else:
        relative_difference = 0 if difference == 0 else 100

    comparison.append({
        "Feature": feature,
        "Kaggle": kaggle_value,
        "Live": live_value,
        "Absolute Difference": difference,
        "Relative Difference %": relative_difference,
    })


comparison_df = pd.DataFrame(comparison)


# ============================================================
# SUMMARY
# ============================================================

exact_matches = (
    comparison_df["Absolute Difference"] < 1e-9
).sum()

close_matches = (
    comparison_df["Relative Difference %"] <= 5
).sum()

different = (
    comparison_df["Relative Difference %"] > 5
).sum()


print("\n" + "=" * 80)
print("FEATURE COMPARISON SUMMARY")
print("=" * 80)

print("Total features:", len(comparison_df))
print("Exact matches:", exact_matches)
print("Within 5%:", close_matches)
print("Different (>5%):", different)


# ============================================================
# SHOW BIGGEST DIFFERENCES
# ============================================================

print("\n" + "=" * 80)
print("TOP 15 FEATURE DIFFERENCES")
print("=" * 80)

top = comparison_df.sort_values(
    "Relative Difference %",
    ascending=False
).head(15)

print(
    top.to_string(
        index=False,
        float_format=lambda x: f"{x:.6f}"
    )
)


# ============================================================
# SAVE RESULT
# ============================================================

comparison_df.to_csv(
    "wallet_feature_comparison.csv",
    index=False
)

print("\nComparison saved to:")
print("wallet_feature_comparison.csv")

print("\n" + "=" * 80)
print("DONE")
print("=" * 80)