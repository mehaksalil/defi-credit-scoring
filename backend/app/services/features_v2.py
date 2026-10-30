"""
Step 3b: Extended feature engineering for the Kaggle
"Ethereum Fraud Detection Dataset" schema.

This module computes the 47 features expected by the trained
RandomForest fraud model from LIVE Etherscan transaction data.

IMPORTANT:
-----------
The Kaggle model was trained on a static dataset. Live Etherscan
data is not guaranteed to have been generated using exactly the
same preprocessing rules.

Therefore:

    - Direct transaction counts/sums are relatively reliable.
    - Contract-related features are approximations unless the live
      transaction data contains enough information to identify the
      actual contract interaction.
    - Some ERC20 contract-specific features cannot be reproduced
      exactly from token-transfer events alone.
    - Token-name features depend on the fields returned by
      blockchain_data.py.

This module is intended to make the live pipeline internally
consistent and compatible with the trained 47-feature model.
It does NOT magically make the Kaggle model validated on live data.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ============================================================
# EXACT FEATURE ORDER EXPECTED BY THE KAGGLE MODEL
# ============================================================

FEATURE_NAMES_V2 = [
    "Avg_min_between_sent_tnx",
    "Avg_min_between_received_tnx",
    "Time_Diff_between_first_and_last_(Mins)",
    "Sent_tnx",
    "Received_Tnx",
    "Number_of_Created_Contracts",
    "Unique_Received_From_Addresses",
    "Unique_Sent_To_Addresses",
    "min_value_received",
    "max_value_received",
    "avg_val_received",
    "min_val_sent",
    "max_val_sent",
    "avg_val_sent",
    "min_value_sent_to_contract",
    "max_val_sent_to_contract",
    "avg_value_sent_to_contract",
    "total_transactions_(including_tnx_to_create_contract",
    "total_Ether_sent",
    "total_ether_received",
    "total_ether_sent_contracts",
    "total_ether_balance",
    "Total_ERC20_tnxs",
    "ERC20_total_Ether_received",
    "ERC20_total_ether_sent",
    "ERC20_total_Ether_sent_contract",
    "ERC20_uniq_sent_addr",
    "ERC20_uniq_rec_addr",
    "ERC20_uniq_sent_addr.1",
    "ERC20_uniq_rec_contract_addr",
    "ERC20_avg_time_between_sent_tnx",
    "ERC20_avg_time_between_rec_tnx",
    "ERC20_avg_time_between_rec_2_tnx",
    "ERC20_avg_time_between_contract_tnx",
    "ERC20_min_val_rec",
    "ERC20_max_val_rec",
    "ERC20_avg_val_rec",
    "ERC20_min_val_sent",
    "ERC20_max_val_sent",
    "ERC20_avg_val_sent",
    "ERC20_min_val_sent_contract",
    "ERC20_max_val_sent_contract",
    "ERC20_avg_val_sent_contract",
    "ERC20_uniq_sent_token_name",
    "ERC20_uniq_rec_token_name",
    "ERC20_most_sent_token_type",
    "ERC20_most_rec_token_type",
]


# ============================================================
# GENERAL HELPERS
# ============================================================

def _empty_series(dtype=float) -> pd.Series:
    return pd.Series(dtype=dtype)


def _avg_gap_minutes(timestamps: pd.Series) -> float:
    """
    Average gap in minutes between consecutive timestamps.

    Returns 0 when fewer than two timestamps exist.
    """
    if timestamps is None or len(timestamps) < 2:
        return 0.0

    values = pd.to_numeric(timestamps, errors="coerce").dropna()

    if len(values) < 2:
        return 0.0

    values = np.sort(values.to_numpy(dtype=np.float64))

    gaps = np.diff(values) / 60.0

    if len(gaps) == 0:
        return 0.0

    return float(np.mean(gaps))


def _safe_stats(values: pd.Series) -> tuple[float, float, float]:
    """
    Return:

        min, max, mean

    for a numeric series.

    Returns (0, 0, 0) for an empty or unusable series.
    """
    if values is None or len(values) == 0:
        return 0.0, 0.0, 0.0

    values = pd.to_numeric(values, errors="coerce")
    values = values.replace([np.inf, -np.inf], np.nan).dropna()

    if len(values) == 0:
        return 0.0, 0.0, 0.0

    return (
        float(values.min()),
        float(values.max()),
        float(values.mean()),
    )


def _normalise_string(value) -> str:
    """
    Normalise a token/string value.

    Values such as:
        None
        NaN
        ""
        "Unknown"
        "unknown"
        "N/A"

    are treated as missing.
    """
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    value = str(value).strip()

    if not value:
        return ""

    if value.lower() in {
        "unknown",
        "nan",
        "none",
        "null",
        "n/a",
        "na",
        "-",
    }:
        return ""

    return value


def _normalise_address_series(series: pd.Series) -> pd.Series:
    """
    Convert address series to lowercase strings.
    """
    if series is None:
        return pd.Series(dtype=str)

    return series.fillna("").astype(str).str.strip().str.lower()


def _get_column(
    df: pd.DataFrame,
    candidates: list[str],
    default=None,
) -> pd.Series:
    """
    Return the first usable column from a list of possible names.

    This makes the feature pipeline tolerant of small naming
    differences in blockchain_data.py.
    """
    for column in candidates:
        if column in df.columns:
            return df[column]

    if default is not None:
        return pd.Series([default] * len(df), index=df.index)

    return pd.Series(index=df.index, dtype=object)


def _numeric_series(
    df: pd.DataFrame,
    candidates: list[str],
    default=0.0,
) -> pd.Series:
    """
    Return a numeric series from the first available candidate column.
    """
    series = _get_column(df, candidates, default=default)

    return pd.to_numeric(
        series,
        errors="coerce",
    ).fillna(default)


# ============================================================
# TOKEN SYMBOL / NAME HANDLING
# ============================================================

def _find_token_name_series(token_df: pd.DataFrame) -> pd.Series:
    """
    Find the best available token-name/symbol column.

    Different versions of Etherscan parsing code may expose the
    token identity under different column names.

    Priority:
        token_symbol
        token_name
        symbol
        TokenSymbol
        TokenName
        tokenSymbol
        tokenName

    We deliberately do NOT use a generic "Unknown" value if a
    more informative column exists.
    """

    candidates = [
        "token_symbol",
        "token_name",
        "symbol",
        "TokenSymbol",
        "TokenName",
        "tokenSymbol",
        "tokenName",
        "token_type",
        "Token",
    ]

    for column in candidates:
        if column in token_df.columns:
            series = token_df[column].apply(_normalise_string)

            # If this column actually contains useful values,
            # use it.
            useful = series[series != ""]

            if len(useful) > 0:
                return series

    # Nothing useful was exposed by the live parser.
    return pd.Series(
        [""] * len(token_df),
        index=token_df.index,
        dtype=str,
    )


def _get_token_values(token_df: pd.DataFrame) -> pd.Series:
    """
    Convert token transfer values into human-readable token amounts.

    Expected live fields:
        value_raw
        token_decimal

    Falls back gracefully if decimal information is unavailable.
    """

    if len(token_df) == 0:
        return _empty_series(float)

    raw = _numeric_series(
        token_df,
        [
            "value_raw",
            "value",
            "Value",
        ],
        default=0.0,
    )

    decimals = _numeric_series(
        token_df,
        [
            "token_decimal",
            "token_decimals",
            "tokenDecimal",
            "decimals",
        ],
        default=0.0,
    )

    decimals = decimals.clip(lower=0, upper=36)

    divisor = np.power(10.0, decimals)

    divisor = divisor.replace(0, 1)

    values = raw / divisor

    values = values.replace(
        [np.inf, -np.inf],
        np.nan,
    ).fillna(0.0)

    return values.astype(float)


# ============================================================
# TOKEN ENCODING
# ============================================================

def _safe_encode(
    token_name: str,
    encoder,
) -> float:
    """
    Encode a token name using the LabelEncoder saved during
    model training.

    VERY IMPORTANT:
    ----------------
    We never fit a new encoder here.

    The RandomForest was trained using the integer values generated
    by the original LabelEncoder. Therefore inference must use the
    exact same encoder.

    If a live token does not exist in the training vocabulary,
    we use the encoder's "Unknown" class when available.

    If "Unknown" is absent, -1 is used.
    """

    token_name = _normalise_string(token_name)

    if encoder is None:
        return -1.0

    classes = list(getattr(encoder, "classes_", []))

    if not classes:
        return -1.0

    # Exact token available in training vocabulary.
    if token_name in classes:
        try:
            return float(
                encoder.transform([token_name])[0]
            )
        except Exception:
            pass

    # Use the training-time Unknown class if available.
    unknown_candidates = [
        "Unknown",
        "unknown",
        "UNKNOWN",
    ]

    for unknown in unknown_candidates:
        if unknown in classes:
            try:
                return float(
                    encoder.transform([unknown])[0]
                )
            except Exception:
                pass

    # Last-resort numeric fallback.
    return -1.0


# ============================================================
# TOKEN DIRECTION
# ============================================================

def _get_token_direction(
    token_df: pd.DataFrame,
    wallet: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split token transfers into outgoing and incoming transfers.

    Preferred approach:
        use is_outgoing if blockchain_data.py already calculated it.

    Fallback:
        compare from_address against the wallet address.
    """

    if len(token_df) == 0:
        return token_df.copy(), token_df.copy()

    if "is_outgoing" in token_df.columns:
        outgoing_mask = (
            token_df["is_outgoing"]
            .fillna(False)
            .astype(bool)
        )

        outgoing = token_df[outgoing_mask].copy()
        incoming = token_df[~outgoing_mask].copy()

        return outgoing, incoming

    from_addresses = _normalise_address_series(
        _get_column(
            token_df,
            [
                "from_address",
                "from",
                "fromAddress",
            ],
            default="",
        )
    )

    outgoing_mask = from_addresses == wallet

    outgoing = token_df[outgoing_mask].copy()
    incoming = token_df[~outgoing_mask].copy()

    return outgoing, incoming


# ============================================================
# NORMAL TRANSACTION DIRECTION
# ============================================================

def _get_transaction_direction(
    df: pd.DataFrame,
    wallet: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split normal transactions into outgoing and incoming.
    """

    if len(df) == 0:
        return df.copy(), df.copy()

    if "is_outgoing" in df.columns:
        outgoing_mask = (
            df["is_outgoing"]
            .fillna(False)
            .astype(bool)
        )

        outgoing = df[outgoing_mask].copy()
        incoming = df[~outgoing_mask].copy()

        return outgoing, incoming

    from_addresses = _normalise_address_series(
        _get_column(
            df,
            [
                "from_address",
                "from",
                "fromAddress",
            ],
            default="",
        )
    )

    outgoing_mask = from_addresses == wallet

    outgoing = df[outgoing_mask].copy()
    incoming = df[~outgoing_mask].copy()

    return outgoing, incoming


# ============================================================
# CONTRACT-LIKE TRANSACTIONS
# ============================================================

def _get_contract_like_transactions(
    outgoing: pd.DataFrame,
) -> pd.DataFrame:
    """
    Approximate contract interactions using transaction calldata.

    This is NOT perfect contract detection.

    A transaction with non-empty calldata is treated as
    contract-like.

    This matches the strategy used by the previous implementation,
    while keeping the approximation explicit.
    """

    if len(outgoing) == 0:
        return outgoing.copy()

    input_data = _get_column(
        outgoing,
        [
            "input",
            "input_data",
            "data",
        ],
        default="0x",
    )

    input_data = (
        input_data
        .fillna("0x")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    mask = (
        (input_data != "")
        & (input_data != "0x")
        & (input_data != "0x0")
    )

    return outgoing[mask].copy()


# ============================================================
# MAIN FEATURE FUNCTION
# ============================================================

def compute_features_v2(
    df: pd.DataFrame,
    token_df: pd.DataFrame,
    wallet_address: str,
    sent_token_encoder=None,
    rec_token_encoder=None,
) -> pd.Series:
    """
    Compute the 47-column Kaggle feature vector.

    Parameters
    ----------
    df:
        Normal ETH transaction DataFrame returned by
        blockchain_data.get_transactions().

    token_df:
        ERC20 transfer DataFrame returned by
        blockchain_data.get_token_transactions().

    wallet_address:
        Wallet being evaluated.

    sent_token_encoder:
        LabelEncoder saved during Kaggle model training.

    rec_token_encoder:
        LabelEncoder saved during Kaggle model training.

    Returns
    -------
    pd.Series
        Exactly 47 features in FEATURE_NAMES_V2 order.
    """

    # --------------------------------------------------------
    # Defensive copies
    # --------------------------------------------------------

    if df is None:
        df = pd.DataFrame()

    if token_df is None:
        token_df = pd.DataFrame()

    df = df.copy()
    token_df = token_df.copy()

    wallet = str(wallet_address).strip().lower()

    out: dict[str, float] = {}

    # --------------------------------------------------------
    # NORMAL TRANSACTIONS
    # --------------------------------------------------------

    outgoing, incoming = _get_transaction_direction(
        df,
        wallet,
    )

    # --------------------------------------------------------
    # TIMING
    # --------------------------------------------------------

    out["Avg_min_between_sent_tnx"] = (
        _avg_gap_minutes(
            _get_column(
                outgoing,
                ["timestamp", "time_stamp", "timeStamp"],
            )
        )
        if len(outgoing)
        else 0.0
    )

    out["Avg_min_between_received_tnx"] = (
        _avg_gap_minutes(
            _get_column(
                incoming,
                ["timestamp", "time_stamp", "timeStamp"],
            )
        )
        if len(incoming)
        else 0.0
    )

    all_timestamps = _numeric_series(
        df,
        [
            "timestamp",
            "time_stamp",
            "timeStamp",
        ],
        default=np.nan,
    )

    all_timestamps = all_timestamps.replace(
        [np.inf, -np.inf],
        np.nan,
    ).dropna()

    if len(all_timestamps) >= 2:
        out["Time_Diff_between_first_and_last_(Mins)"] = float(
            (
                all_timestamps.max()
                - all_timestamps.min()
            )
            / 60.0
        )
    else:
        out["Time_Diff_between_first_and_last_(Mins)"] = 0.0

    # --------------------------------------------------------
    # TRANSACTION COUNTS
    # --------------------------------------------------------

    out["Sent_tnx"] = float(len(outgoing))

    out["Received_Tnx"] = float(len(incoming))

    # Created-contract transactions.
    #
    # If blockchain_data exposes contract_address, use it.
    # Otherwise default to zero rather than inventing a value.
    if len(df):
        from_addresses = _normalise_address_series(
            _get_column(
                df,
                [
                    "from_address",
                    "from",
                    "fromAddress",
                ],
                default="",
            )
        )

        contract_addresses = (
            _get_column(
                df,
                [
                    "contract_address",
                    "contractAddress",
                ],
                default="",
            )
            .fillna("")
            .astype(str)
            .str.strip()
        )

        out["Number_of_Created_Contracts"] = float(
            (
                (from_addresses == wallet)
                & (contract_addresses != "")
            ).sum()
        )
    else:
        out["Number_of_Created_Contracts"] = 0.0

    # --------------------------------------------------------
    # UNIQUE ADDRESSES
    # --------------------------------------------------------

    incoming_from = _normalise_address_series(
        _get_column(
            incoming,
            [
                "from_address",
                "from",
                "fromAddress",
            ],
            default="",
        )
    )

    outgoing_to = _normalise_address_series(
        _get_column(
            outgoing,
            [
                "to_address",
                "to",
                "toAddress",
            ],
            default="",
        )
    )

    incoming_from = incoming_from[incoming_from != ""]
    outgoing_to = outgoing_to[outgoing_to != ""]

    out["Unique_Received_From_Addresses"] = float(
        incoming_from.nunique()
    )

    out["Unique_Sent_To_Addresses"] = float(
        outgoing_to.nunique()
    )

    # --------------------------------------------------------
    # ETH VALUE FEATURES
    # --------------------------------------------------------

    recv_wei = _numeric_series(
        incoming,
        [
            "value_wei",
            "value",
            "valueWei",
        ],
        default=0.0,
    )

    sent_wei = _numeric_series(
        outgoing,
        [
            "value_wei",
            "value",
            "valueWei",
        ],
        default=0.0,
    )

    recv_eth = recv_wei / 1e18
    sent_eth = sent_wei / 1e18

    (
        out["min_value_received"],
        out["max_value_received"],
        out["avg_val_received"],
    ) = _safe_stats(recv_eth)

    (
        out["min_val_sent"],
        out["max_val_sent"],
        out["avg_val_sent"],
    ) = _safe_stats(sent_eth)

    # --------------------------------------------------------
    # CONTRACT-LIKE ETH TRANSACTIONS
    # --------------------------------------------------------

    contract_like = _get_contract_like_transactions(
        outgoing
    )

    contract_wei = _numeric_series(
        contract_like,
        [
            "value_wei",
            "value",
            "valueWei",
        ],
        default=0.0,
    )

    contract_eth = contract_wei / 1e18

    (
        out["min_value_sent_to_contract"],
        out["max_val_sent_to_contract"],
        out["avg_value_sent_to_contract"],
    ) = _safe_stats(contract_eth)

    # --------------------------------------------------------
    # TOTAL ETH FEATURES
    # --------------------------------------------------------

    out[
        "total_transactions_(including_tnx_to_create_contract"
    ] = float(len(df))

    out["total_Ether_sent"] = (
        float(sent_eth.sum())
        if len(sent_eth)
        else 0.0
    )

    out["total_ether_received"] = (
        float(recv_eth.sum())
        if len(recv_eth)
        else 0.0
    )

    out["total_ether_sent_contracts"] = (
        float(contract_eth.sum())
        if len(contract_eth)
        else 0.0
    )

    out["total_ether_balance"] = (
        out["total_ether_received"]
        - out["total_Ether_sent"]
    )

    # ========================================================
    # ERC20 FEATURES
    # ========================================================

    token_out, token_in = _get_token_direction(
        token_df,
        wallet,
    )

    # --------------------------------------------------------
    # TOKEN VALUES
    # --------------------------------------------------------

    token_out_val = _get_token_values(token_out)
    token_in_val = _get_token_values(token_in)

    # --------------------------------------------------------
    # TOKEN COUNT
    # --------------------------------------------------------

    out["Total_ERC20_tnxs"] = float(
        len(token_df)
    )

    # --------------------------------------------------------
    # TOTAL TOKEN VALUES
    # --------------------------------------------------------

    out["ERC20_total_Ether_received"] = (
        float(token_in_val.sum())
        if len(token_in_val)
        else 0.0
    )

    out["ERC20_total_ether_sent"] = (
        float(token_out_val.sum())
        if len(token_out_val)
        else 0.0
    )

    # --------------------------------------------------------
    # TOKEN ADDRESS FEATURES
    # --------------------------------------------------------

    token_in_from = _normalise_address_series(
        _get_column(
            token_in,
            [
                "from_address",
                "from",
                "fromAddress",
            ],
            default="",
        )
    )

    token_out_to = _normalise_address_series(
        _get_column(
            token_out,
            [
                "to_address",
                "to",
                "toAddress",
            ],
            default="",
        )
    )

    token_in_from = token_in_from[
        token_in_from != ""
    ]

    token_out_to = token_out_to[
        token_out_to != ""
    ]

    out["ERC20_uniq_sent_addr"] = float(
        token_out_to.nunique()
    )

    out["ERC20_uniq_rec_addr"] = float(
        token_in_from.nunique()
    )

    # --------------------------------------------------------
    # DUPLICATE ERC20 ADDRESS FEATURE
    # --------------------------------------------------------
    #
    # The Kaggle dataset contains both:
    #
    #   ERC20 uniq sent addr
    #   ERC20 uniq sent addr.1
    #
    # The latter is ambiguous in the source dataset.
    #
    # We preserve the same value rather than inventing another
    # unrelated signal.

    out["ERC20_uniq_sent_addr.1"] = (
        out["ERC20_uniq_sent_addr"]
    )

    # --------------------------------------------------------
    # ERC20 CONTRACT FEATURES
    # --------------------------------------------------------
    #
    # Token transfer events do not directly tell us whether the
    # receiving address is an EOA or a smart contract.
    #
    # Therefore these remain conservative fallbacks.
    #
    # IMPORTANT:
    # We do NOT falsely claim that all token transfers were
    # sent to contracts.

    out["ERC20_uniq_rec_contract_addr"] = 0.0

    # --------------------------------------------------------
    # ERC20 TIMING
    # --------------------------------------------------------

    token_out_ts = _get_column(
        token_out,
        [
            "timestamp",
            "time_stamp",
            "timeStamp",
        ],
        default=np.nan,
    )

    token_in_ts = _get_column(
        token_in,
        [
            "timestamp",
            "time_stamp",
            "timeStamp",
        ],
        default=np.nan,
    )

    all_token_ts = _get_column(
        token_df,
        [
            "timestamp",
            "time_stamp",
            "timeStamp",
        ],
        default=np.nan,
    )

    out["ERC20_avg_time_between_sent_tnx"] = (
        _avg_gap_minutes(token_out_ts)
        if len(token_out)
        else 0.0
    )

    out["ERC20_avg_time_between_rec_tnx"] = (
        _avg_gap_minutes(token_in_ts)
        if len(token_in)
        else 0.0
    )

    # The original Kaggle column is ambiguous.
    #
    # We retain the received-transfer timing rather than creating
    # an unrelated arbitrary value.

    out["ERC20_avg_time_between_rec_2_tnx"] = (
        out["ERC20_avg_time_between_rec_tnx"]
    )

    # Combined token-transfer timing.
    out["ERC20_avg_time_between_contract_tnx"] = (
        _avg_gap_minutes(all_token_ts)
        if len(token_df)
        else 0.0
    )

    # --------------------------------------------------------
    # ERC20 VALUE STATISTICS
    # --------------------------------------------------------

    (
        out["ERC20_min_val_rec"],
        out["ERC20_max_val_rec"],
        out["ERC20_avg_val_rec"],
    ) = _safe_stats(token_in_val)

    (
        out["ERC20_min_val_sent"],
        out["ERC20_max_val_sent"],
        out["ERC20_avg_val_sent"],
    ) = _safe_stats(token_out_val)

    # --------------------------------------------------------
    # ERC20 CONTRACT VALUE FEATURES
    # --------------------------------------------------------
    #
    # Exact contract detection is unavailable from a plain token
    # transfer event.
    #
    # Therefore we use zero rather than incorrectly treating every
    # token transfer as a contract interaction.
    #
    # This is especially important because the previous version
    # made:
    #
    #     ERC20_total_Ether_sent_contract
    #
    # equal to ALL ERC20 sent value.
    #
    # That produced extremely large live-vs-Kaggle differences.

    out["ERC20_total_Ether_sent_contract"] = 0.0

    out["ERC20_min_val_sent_contract"] = 0.0
    out["ERC20_max_val_sent_contract"] = 0.0
    out["ERC20_avg_val_sent_contract"] = 0.0

    # ========================================================
    # TOKEN NAME FEATURES
    # ========================================================

    token_names = _find_token_name_series(
        token_df
    )

    # Attach the discovered names to outgoing/incoming
    # subsets using the original indexes.
    token_df = token_df.copy()
    token_df["_resolved_token_name"] = token_names

    if len(token_out):
        token_out_names = (
            token_df.loc[
                token_out.index,
                "_resolved_token_name",
            ]
            .apply(_normalise_string)
        )
    else:
        token_out_names = pd.Series(
            dtype=str
        )

    if len(token_in):
        token_in_names = (
            token_df.loc[
                token_in.index,
                "_resolved_token_name",
            ]
            .apply(_normalise_string)
        )
    else:
        token_in_names = pd.Series(
            dtype=str
        )

    # Only count actual known token names.
    valid_out_names = token_out_names[
        token_out_names != ""
    ]

    valid_in_names = token_in_names[
        token_in_names != ""
    ]

    out["ERC20_uniq_sent_token_name"] = float(
        valid_out_names.nunique()
    )

    out["ERC20_uniq_rec_token_name"] = float(
        valid_in_names.nunique()
    )

    # --------------------------------------------------------
    # MOST COMMON TOKEN
    # --------------------------------------------------------

    if len(valid_out_names):
        most_sent_token = (
            valid_out_names
            .value_counts()
            .index[0]
        )
    else:
        most_sent_token = ""

    if len(valid_in_names):
        most_rec_token = (
            valid_in_names
            .value_counts()
            .index[0]
        )
    else:
        most_rec_token = ""

    # --------------------------------------------------------
    # LABEL ENCODING
    # --------------------------------------------------------

    out["ERC20_most_sent_token_type"] = (
        _safe_encode(
            most_sent_token,
            sent_token_encoder,
        )
    )

    out["ERC20_most_rec_token_type"] = (
        _safe_encode(
            most_rec_token,
            rec_token_encoder,
        )
    )

    # ========================================================
    # FINAL SANITISATION
    # ========================================================

    result = pd.Series(
        out,
        dtype=float,
    )

    # Guarantee every expected feature exists.
    for feature in FEATURE_NAMES_V2:
        if feature not in result.index:
            result[feature] = 0.0

    # Exact order expected by RandomForest.
    result = result[
        FEATURE_NAMES_V2
    ]

    # Convert invalid values.
    result = result.replace(
        [np.inf, -np.inf],
        np.nan,
    )

    result = result.fillna(0.0)

    return result