import joblib
import pandas as pd
import numpy as np


DATASET_PATH = "../ethereum_fraud_detection/transaction_dataset.csv"
MODEL_PATH = "models/fraud_detection_rf_kaggle.joblib"
FEATURES_PATH = "models/fraud_detection_rf_kaggle_features.joblib"
SENT_ENCODER_PATH = "models/le_sent.joblib"
REC_ENCODER_PATH = "models/le_rec.joblib"


# ============================================================
# COLUMN NORMALIZATION
# ============================================================

def normalize_column(name):
    name = str(name).strip()

    replacements = {
        "Avg min between sent tnx":
            "Avg_min_between_sent_tnx",

        "Avg min between received tnx":
            "Avg_min_between_received_tnx",

        "Time Diff between first and last (Mins)":
            "Time_Diff_between_first_and_last_(Mins)",

        "Sent tnx":
            "Sent_tnx",

        "Received Tnx":
            "Received_Tnx",

        "Number of Created Contracts":
            "Number_of_Created_Contracts",

        "Unique Received From Addresses":
            "Unique_Received_From_Addresses",

        "Unique Sent To Addresses":
            "Unique_Sent_To_Addresses",

        "min value received":
            "min_value_received",

        "max value received":
            "max_value_received",

        "avg val received":
            "avg_val_received",

        "min val sent":
            "min_val_sent",

        "max val sent":
            "max_val_sent",

        "avg val sent":
            "avg_val_sent",

        "min value sent to contract":
            "min_value_sent_to_contract",

        "max val sent to contract":
            "max_val_sent_to_contract",

        "avg value sent to contract":
            "avg_value_sent_to_contract",

        "total transactions (including tnx to create contract":
            "total_transactions_(including_tnx_to_create_contract",

        "total Ether sent":
            "total_Ether_sent",

        "total ether received":
            "total_ether_received",

        "total ether sent contracts":
            "total_ether_sent_contracts",

        "total ether balance":
            "total_ether_balance",

        "Total ERC20 tnxs":
            "Total_ERC20_tnxs",

        "ERC20 total Ether received":
            "ERC20_total_Ether_received",

        "ERC20 total ether sent":
            "ERC20_total_ether_sent",

        "ERC20 total Ether sent contract":
            "ERC20_total_Ether_sent_contract",

        "ERC20 uniq sent addr":
            "ERC20_uniq_sent_addr",

        "ERC20 uniq rec addr":
            "ERC20_uniq_rec_addr",

        "ERC20 uniq sent addr.1":
            "ERC20_uniq_sent_addr.1",

        "ERC20 uniq rec contract addr":
            "ERC20_uniq_rec_contract_addr",

        "ERC20 avg time between sent tnx":
            "ERC20_avg_time_between_sent_tnx",

        "ERC20 avg time between rec tnx":
            "ERC20_avg_time_between_rec_tnx",

        "ERC20 avg time between rec 2 tnx":
            "ERC20_avg_time_between_rec_2_tnx",

        "ERC20 avg time between contract tnx":
            "ERC20_avg_time_between_contract_tnx",

        "ERC20 min val rec":
            "ERC20_min_val_rec",

        "ERC20 max val rec":
            "ERC20_max_val_rec",

        "ERC20 avg val rec":
            "ERC20_avg_val_rec",

        "ERC20 min val sent":
            "ERC20_min_val_sent",

        "ERC20 max val sent":
            "ERC20_max_val_sent",

        "ERC20 avg val sent":
            "ERC20_avg_val_sent",

        "ERC20 min val sent contract":
            "ERC20_min_val_sent_contract",

        "ERC20 max val sent contract":
            "ERC20_max_val_sent_contract",

        "ERC20 avg val sent contract":
            "ERC20_avg_val_sent_contract",

        "ERC20 uniq sent token name":
            "ERC20_uniq_sent_token_name",

        "ERC20 uniq rec token name":
            "ERC20_uniq_rec_token_name",

        "ERC20 most sent token type":
            "ERC20_most_sent_token_type",

        "ERC20_most_rec_token_type":
            "ERC20_most_rec_token_type",
    }

    return replacements.get(name, name)


# ============================================================
# LOAD DATASET
# ============================================================

print("=" * 70)
print("SINGLE WALLET FRAUD TEST")
print("=" * 70)

print("\nLoading dataset...")

df = pd.read_csv(DATASET_PATH)

print("Dataset shape:", df.shape)


# ============================================================
# NORMALIZE DATASET COLUMNS
# ============================================================

rename_map = {}

for column in df.columns:
    normalized = normalize_column(column)

    if normalized != column:
        rename_map[column] = normalized

df = df.rename(columns=rename_map)


# ============================================================
# LOAD MODEL
# ============================================================

model = joblib.load(MODEL_PATH)
feature_names = joblib.load(FEATURES_PATH)

le_sent = joblib.load(SENT_ENCODER_PATH)
le_rec = joblib.load(REC_ENCODER_PATH)

print("\nModel loaded.")
print("Model expects:", model.n_features_in_, "features")
print("Feature file contains:", len(feature_names), "features")


# ============================================================
# CHECK FEATURES
# ============================================================

print("\nChecking feature mapping...")

missing = [
    feature
    for feature in feature_names
    if feature not in df.columns
]

if missing:
    print("\nERROR: Missing features:")

    for feature in missing:
        print(" -", feature)

    print("\nAvailable normalized columns:")
    for column in df.columns:
        print(" -", column)

    raise SystemExit(1)


print("SUCCESS: All 47 model features are present.")


# ============================================================
# ENCODE TOKEN FEATURES
# ============================================================

def encode_with_unknown(series, encoder):

    known = set(encoder.classes_)

    return series.astype(str).apply(
        lambda x: encoder.transform([x])[0]
        if x in known
        else -1
    )


df["ERC20_most_sent_token_type"] = encode_with_unknown(
    df["ERC20_most_sent_token_type"],
    le_sent
)

df["ERC20_most_rec_token_type"] = encode_with_unknown(
    df["ERC20_most_rec_token_type"],
    le_rec
)


# ============================================================
# CREATE MODEL INPUT
# ============================================================

X = df[feature_names].copy()

print("\nX shape before conversion:", X.shape)

# Everything must be numeric
X = X.apply(pd.to_numeric, errors="coerce")

# Replace infinity
X = X.replace([np.inf, -np.inf], np.nan)

# Fill missing values
X = X.fillna(X.median(numeric_only=True))
X = X.fillna(0)

print("X shape after conversion:", X.shape)


# ============================================================
# TEST ONE WALLET
# ============================================================

row_number = 0

wallet = X.iloc[[row_number]]

prediction = model.predict(wallet)[0]
probability = model.predict_proba(wallet)[0]


# ============================================================
# DISPLAY RESULT
# ============================================================

print("\n" + "=" * 70)
print("WALLET RESULT")
print("=" * 70)

print("Wallet address:", df.iloc[row_number]["Address"])

print("Actual FLAG:", df.iloc[row_number]["FLAG"])

print(
    "Prediction:",
    "FRAUD" if prediction == 1 else "NORMAL"
)

print("Probability Normal:", round(probability[0], 4))
print("Probability Fraud:", round(probability[1], 4))

print("=" * 70)