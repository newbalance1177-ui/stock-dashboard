"""ローソク足のテクニカルパターン検出。

各 detect_* 関数は、日付昇順に並んだOHLC行のリスト(直近が最後)を受け取り、
「直近の1本(または数本)」がそのパターンに該当するかを判定する。
該当すれば {"pattern": パターン名, "detail": 説明} を返し、しなければ None を返す。

新しいパターンを追加する場合は detect_* 関数を増やし、PATTERN_DETECTORS に登録する。
"""

Row = dict  # {"date": str, "open": float, "high": float, "low": float, "close": float}


def _body(row: Row) -> float:
    return abs(row["close"] - row["open"])


def _range(row: Row) -> float:
    return row["high"] - row["low"]


def _upper_wick(row: Row) -> float:
    return row["high"] - max(row["open"], row["close"])


def _lower_wick(row: Row) -> float:
    return min(row["open"], row["close"]) - row["low"]


def _is_bullish(row: Row) -> bool:
    return row["close"] > row["open"]


def _zone(rows: list[Row], lookback: int = 20) -> str:
    """直近値が過去lookback日の中でどのゾーンにあるかを大まかに判定する。"""
    window = rows[-lookback:]
    highs = [r["high"] for r in window]
    lows = [r["low"] for r in window]
    span = max(highs) - min(lows)
    if span <= 0:
        return "中間"
    position = (rows[-1]["close"] - min(lows)) / span
    if position >= 0.75:
        return "高値圏"
    if position <= 0.25:
        return "安値圏"
    return "中間"


def detect_doji(rows: list[Row]) -> dict | None:
    """指標1: 十字線。始値と終値がほぼ同じで、上下にヒゲが伸びる形。"""
    if len(rows) < 5:
        return None
    latest = rows[-1]
    rng = _range(latest)
    if rng <= 0:
        return None
    if _body(latest) / rng > 0.1:
        return None

    zone = _zone(rows)
    if zone == "高値圏":
        detail = "高値圏での十字線。上昇の勢いが拮抗し、下落相場への転換に注意。"
    elif zone == "安値圏":
        detail = "安値圏での十字線。下落の勢いが拮抗し、上昇相場への転換の可能性。"
    else:
        detail = "始値と終値が拮抗し、相場の迷い・転換を示唆。"
    return {"pattern": "十字線", "detail": detail}


def detect_hanging_man(rows: list[Row]) -> dict | None:
    """指標2: 首吊り線。高値圏で、実体が小さく長い下ヒゲを持つ形(上昇トレンドの終わりのサイン)。"""
    if len(rows) < 5:
        return None
    latest = rows[-1]
    body = _body(latest)
    if body <= 0:
        return None
    if _zone(rows) != "高値圏":
        return None
    if _lower_wick(latest) < body * 2:
        return None
    if _upper_wick(latest) > body * 0.3:
        return None
    return {"pattern": "首吊り線", "detail": "高値圏で長い下ヒゲの小陽線/小陰線。上昇トレンド終焉の警戒サイン。"}


def detect_harami(rows: list[Row]) -> dict | None:
    """指標3: はらみ線。前日の大きな実体の中に、当日の小さな実体が収まる形。"""
    if len(rows) < 2:
        return None
    prev, curr = rows[-2], rows[-1]
    prev_body = _body(prev)
    curr_body = _body(curr)
    if prev_body <= 0 or curr_body >= prev_body * 0.5:
        return None
    prev_lo, prev_hi = min(prev["open"], prev["close"]), max(prev["open"], prev["close"])
    curr_lo, curr_hi = min(curr["open"], curr["close"]), max(curr["open"], curr["close"])
    if not (prev_lo <= curr_lo and curr_hi <= prev_hi):
        return None

    zone = _zone(rows)
    detail = "前日の実体の中に当日の小さな実体が収まる。勢いが内側にせき止められ、"
    detail += "底打ちの予兆(安値圏)" if zone == "安値圏" else "トレンド転換の予兆"
    return {"pattern": "はらみ線", "detail": detail}


def detect_engulfing(rows: list[Row]) -> dict | None:
    """指標4: 抱き線(つつみ線)。当日の実体が前日の実体を完全に包み込む形。"""
    if len(rows) < 2:
        return None
    prev, curr = rows[-2], rows[-1]
    prev_body = _body(prev)
    curr_body = _body(curr)
    if prev_body <= 0 or curr_body <= prev_body:
        return None
    prev_lo, prev_hi = min(prev["open"], prev["close"]), max(prev["open"], prev["close"])
    curr_lo, curr_hi = min(curr["open"], curr["close"]), max(curr["open"], curr["close"])
    if not (curr_lo <= prev_lo and curr_hi >= prev_hi):
        return None

    if _is_bullish(curr):
        return {"pattern": "陽の抱き線", "detail": "前日の値動きを飲み込む強い陽線。強い上昇トレンドのサイン。"}
    return {"pattern": "陰の抱き線", "detail": "前日の値動きを飲み込む強い陰線。強い下落トレンドのサイン。"}


def _find_local_extrema(values: list[float], window: int = 3, kind: str = "min") -> list[int]:
    """values中の局所的な極小(kind="min")/極大(kind="max")のインデックス一覧を返す。"""
    extrema = []
    for i in range(window, len(values) - window):
        segment = values[i - window: i + window + 1]
        center = values[i]
        if kind == "min" and center == min(segment):
            extrema.append(i)
        elif kind == "max" and center == max(segment):
            extrema.append(i)
    return extrema


def detect_double_bottom_top(rows: list[Row], lookback: int = 40) -> dict | None:
    """指標5: ダブルボトム・ダブルトップ。2つの底(山)がネックライン突破で完成する形。"""
    if len(rows) < lookback:
        return None
    window = rows[-lookback:]
    closes = [r["close"] for r in window]
    latest_close = closes[-1]

    # ダブルボトム: 2つの安値が近い水準で、間の戻り高値(ネックライン)を直近終値が上抜け
    lows_idx = _find_local_extrema(closes, window=3, kind="min")
    if len(lows_idx) >= 2:
        i1, i2 = lows_idx[-2], lows_idx[-1]
        if i2 > i1 and i2 < len(closes) - 1:
            v1, v2 = closes[i1], closes[i2]
            if v1 > 0 and abs(v1 - v2) / v1 < 0.03:
                neckline = max(closes[i1:i2 + 1])
                if neckline > v1 * 1.02 and latest_close > neckline:
                    return {
                        "pattern": "ダブルボトム",
                        "detail": f"2つの底値が近い水準({v1:,.1f}/{v2:,.1f})で、"
                                  f"ネックライン({neckline:,.1f})を上抜け。上昇トレンドへの転換。",
                    }

    # ダブルトップ: 2つの高値が近い水準で、間の戻り安値(ネックライン)を直近終値が下抜け
    highs_idx = _find_local_extrema(closes, window=3, kind="max")
    if len(highs_idx) >= 2:
        i1, i2 = highs_idx[-2], highs_idx[-1]
        if i2 > i1 and i2 < len(closes) - 1:
            v1, v2 = closes[i1], closes[i2]
            if v1 > 0 and abs(v1 - v2) / v1 < 0.03:
                neckline = min(closes[i1:i2 + 1])
                if neckline < v1 * 0.98 and latest_close < neckline:
                    return {
                        "pattern": "ダブルトップ",
                        "detail": f"2つの高値が近い水準({v1:,.1f}/{v2:,.1f})で、"
                                  f"ネックライン({neckline:,.1f})を下抜け。下降トレンドへの転換。",
                    }
    return None


def detect_island_reversal(rows: list[Row]) -> dict | None:
    """指標6: アイランドリバーサル。窓(ギャップ)で前後から切り離された孤立したローソク足。"""
    if len(rows) < 3:
        return None
    before, island, after = rows[-3], rows[-2], rows[-1]

    # 天井のアイランドリバーサル: 窓を開けて上に孤立→窓を開けて下に戻る
    if island["low"] > before["high"] and after["high"] < island["low"]:
        return {"pattern": "アイランドリバーサル(天井)", "detail": "窓開けで孤立した後、逆方向へ窓を開けて急落。天井のサイン。"}

    # 底のアイランドリバーサル: 窓を開けて下に孤立→窓を開けて上に戻る
    if island["high"] < before["low"] and after["low"] > island["high"]:
        return {"pattern": "アイランドリバーサル(底)", "detail": "窓開けで孤立した後、逆方向へ窓を開けて急伸。底のサイン。"}
    return None


# 新しいパターンを追加する場合はここに関数を足すだけでよい
PATTERN_DETECTORS = [
    detect_doji,
    detect_hanging_man,
    detect_harami,
    detect_engulfing,
    detect_double_bottom_top,
    detect_island_reversal,
]


def detect_all(rows: list[Row]) -> list[dict]:
    """登録済みの全パターン検出関数を実行し、該当したものを一覧で返す。"""
    matches = []
    for detector in PATTERN_DETECTORS:
        result = detector(rows)
        if result:
            matches.append(result)
    return matches
