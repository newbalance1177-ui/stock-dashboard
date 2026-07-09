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


def _is_bearish(row: Row) -> bool:
    return row["close"] < row["open"]


def _sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def _stddev(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    window = values[-period:]
    mean = sum(window) / period
    variance = sum((v - mean) ** 2 for v in window) / period
    return variance ** 0.5


def _rci(values: list[float], period: int) -> float | None:
    """順位相関指数(RCI)。-100(売られすぎ)〜+100(買われすぎ)で推移する。"""
    if len(values) < period:
        return None
    window = values[-period:]
    date_ranks = list(range(period, 0, -1))  # 最新の日を1位とする(直近ほど小さい順位)
    price_order = sorted(range(period), key=lambda i: window[i], reverse=True)
    price_ranks = [0] * period
    for rank, idx in enumerate(price_order, start=1):
        price_ranks[idx] = rank
    d_squared_sum = sum((d - p) ** 2 for d, p in zip(date_ranks, price_ranks))
    return (1 - 6 * d_squared_sum / (period * (period**2 - 1))) * 100


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


def detect_island_top(rows: list[Row]) -> dict | None:
    """指標6: アイランドリバーサル(天井)。窓を開けて上に孤立→逆方向へ窓を開けて急落する形。"""
    if len(rows) < 3:
        return None
    before, island, after = rows[-3], rows[-2], rows[-1]
    if island["low"] > before["high"] and after["high"] < island["low"]:
        return {"pattern": "アイランドリバーサル(天井)", "detail": "窓開けで孤立した後、逆方向へ窓を開けて急落。天井のサイン。"}
    return None


def detect_island_bottom(rows: list[Row]) -> dict | None:
    """指標7: アイランドボトム。下落相場の底値圏で、窓を開けて下に孤立→逆方向へ窓を開けて急伸する形。"""
    if len(rows) < 3:
        return None
    before, island, after = rows[-3], rows[-2], rows[-1]
    if island["high"] < before["low"] and after["low"] > island["high"]:
        return {"pattern": "アイランドボトム", "detail": "窓開けで孤立した後、逆方向へ窓を開けて急伸。絶望の底からの反転(全力買いの合図)。"}
    return None


def detect_gap_down_two_black(rows: list[Row]) -> dict | None:
    """指標8: 下放れ二本黒。窓を開けて下落し、その後2日連続の陰線が並ぶ形(下落継続の強い警戒サイン)。"""
    if len(rows) < 3:
        return None
    before, day1, day2 = rows[-3], rows[-2], rows[-1]
    if not (day1["high"] < before["low"]):  # 窓を開けて下落(ギャップダウン)
        return None
    if not (_is_bearish(day1) and _is_bearish(day2)):
        return None
    if not (day2["close"] < day1["close"]):  # 終値にかけてさらに売られ続けている
        return None
    return {"pattern": "下放れ二本黒", "detail": "窓を開けて急落した後、2日連続の陰線。「底なし沼」入りを警戒すべき暗黒のサイン。"}


def detect_gap_up_two_red(rows: list[Row]) -> dict | None:
    """指標9: 上放れ並び赤。窓を開けて急騰し、ほぼ同じ長さの陽線が2本並ぶ形(上昇継続の強いサイン)。"""
    if len(rows) < 3:
        return None
    before, day1, day2 = rows[-3], rows[-2], rows[-1]
    if not (day1["low"] > before["high"]):  # 窓を開けて上昇(ギャップアップ)
        return None
    if not (_is_bullish(day1) and _is_bullish(day2)):
        return None
    body1, body2 = _body(day1), _body(day2)
    if body1 <= 0 or body2 <= 0:
        return None
    if abs(body1 - body2) / max(body1, body2) > 0.4:  # ほぼ同じ長さ
        return None
    if min(day1["low"], day2["low"]) <= before["high"]:  # 窓を埋めさせていない
        return None
    return {"pattern": "上放れ並び赤", "detail": "窓を開けて急騰した後、ほぼ同じ長さの陽線が2本連続。上昇の本気度を示す強いサイン。"}


def detect_perfect_order(rows: list[Row], short: int = 5, mid: int = 25, long: int = 100, slope_lookback: int = 5) -> dict | None:
    """指標10: パンパカパン(パーフェクトオーダー)。短期・中期・長期の移動平均線が
    上から順に並び、すべて右肩上がりになっている状態(最強の上昇トレンドのサイン)。"""
    closes = [r["close"] for r in rows]
    if len(closes) < long + slope_lookback:
        return None

    short_now, short_past = _sma(closes, short), _sma(closes[:-slope_lookback], short)
    mid_now, mid_past = _sma(closes, mid), _sma(closes[:-slope_lookback], mid)
    long_now, long_past = _sma(closes, long), _sma(closes[:-slope_lookback], long)
    if None in (short_now, short_past, mid_now, mid_past, long_now, long_past):
        return None

    perfect_order = short_now > mid_now > long_now
    all_rising = short_now > short_past and mid_now > mid_past and long_now > long_past
    if perfect_order and all_rising:
        return {
            "pattern": "パンパカパン(PPP)",
            "detail": f"短期({short}日)>中期({mid}日)>長期({long}日)移動平均線が右肩上がりで並ぶ"
                      "「パーフェクトオーダー」。最強クラスの上昇トレンドのサイン。",
        }
    return None


def detect_oversold_bounce(rows: list[Row], drop_pct: float = 2.5, lookback: int = 3) -> dict | None:
    """買いの条件①: 材料なしの前日比-2.5%以上の急落からの反発を狙う逆張りシグナル。
    (急落した瞬間ではなく、そこから反発を確認した時点で検出する)"""
    if len(rows) < lookback + 2:
        return None
    for i in range(len(rows) - 1, max(len(rows) - 1 - lookback, 0), -1):
        prev, drop_day = rows[i - 1], rows[i]
        if prev["close"] <= 0:
            continue
        change_pct = (drop_day["close"] - prev["close"]) / prev["close"] * 100
        if change_pct <= -drop_pct:
            latest = rows[-1]
            if latest["close"] > drop_day["close"]:
                return {
                    "pattern": "急落からの反発",
                    "detail": f"{drop_day['date']}に材料なき前日比{change_pct:+.1f}%の急落。"
                              "そこから反発しつつあり、逆張りの買い場となる可能性(ニュースの有無は要確認)。",
                }
            return None
    return None


def detect_ma25_deviation_bounce(rows: list[Row], period: int = 25, deviation_pct: float = 5.0) -> dict | None:
    """買いの条件②: 25日移動平均線(適正価格の目安)から大きく下に乖離した後の反発。"""
    closes = [r["close"] for r in rows]
    ma = _sma(closes, period)
    if ma is None or ma <= 0:
        return None
    latest = rows[-1]
    deviation = (latest["close"] - ma) / ma * 100
    if deviation > -deviation_pct:
        return None
    if not _is_bullish(latest):  # 反発(陽線)を確認
        return None
    return {
        "pattern": "25日線からの乖離+反発",
        "detail": f"25日移動平均線から{deviation:+.1f}%乖離した後、反発の陽線。"
                  "「適正価格」への回帰(引力)が期待される逆張りポイント。",
    }


def detect_bollinger_oversold(rows: list[Row], period: int = 25) -> dict | None:
    """買いの条件③: ボリンジャーバンド-2σ/-3σまで売られすぎた状態(統計的な下落の限界点)。"""
    closes = [r["close"] for r in rows]
    ma = _sma(closes, period)
    sd = _stddev(closes, period)
    if ma is None or sd is None or sd <= 0:
        return None
    latest = rows[-1]
    lower_2sigma = ma - 2 * sd
    lower_3sigma = ma - 3 * sd
    if latest["low"] <= lower_3sigma:
        return {
            "pattern": "ボリンジャー-3σ到達",
            "detail": "株価が-3σ(統計上99.7%の範囲の外)まで到達。極限の売られすぎで、"
                      "移動平均線への回帰(反発)が高確率で期待される水準。",
        }
    if latest["low"] <= lower_2sigma:
        return {
            "pattern": "ボリンジャー-2σ到達",
            "detail": "株価が-2σ(統計上95.4%の範囲の外)まで到達。売られすぎの限界点に近く、"
                      "反発の可能性が高まっている水準。",
        }
    return None


def detect_rci_oversold(rows: list[Row], period: int = 9, threshold: float = -90.0) -> dict | None:
    """買いの条件④: RCI(順位相関指数)が-90%以下の「売られすぎの極致」。"""
    closes = [r["close"] for r in rows]
    rci = _rci(closes, period)
    if rci is None or rci > threshold:
        return None
    return {
        "pattern": "RCI売られすぎ",
        "detail": f"RCI({period}日)が{rci:.1f}%と-90%以下の売られすぎの極致。高確率でのリバウンドが期待される水準。",
    }


# 新しいパターンを追加する場合はここに関数を足すだけでよい
PATTERN_DETECTORS = [
    detect_doji,
    detect_hanging_man,
    detect_harami,
    detect_engulfing,
    detect_double_bottom_top,
    detect_island_top,
    detect_island_bottom,
    detect_gap_down_two_black,
    detect_gap_up_two_red,
    detect_perfect_order,
    detect_oversold_bounce,
    detect_ma25_deviation_bounce,
    detect_bollinger_oversold,
    detect_rci_oversold,
]


def detect_all(rows: list[Row]) -> list[dict]:
    """登録済みの全パターン検出関数を実行し、該当したものを一覧で返す。"""
    matches = []
    for detector in PATTERN_DETECTORS:
        result = detector(rows)
        if result:
            matches.append(result)
    return matches
