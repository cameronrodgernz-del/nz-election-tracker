"""NZ 2026 election tracker model.

1. Reads every national poll since the 2023 election (polls.csv).
2. Fits a smoothed trend per party with each pollster's lean estimated and removed.
3. Projects to election day and simulates the election many times, including
   the chance that all polls miss in the same direction.
4. Turns each simulated vote into seats using the Electoral Commission method
   (Sainte-Lague, 5% or one electorate, overhang seats kept), with a
   seat-by-seat model for National's electorates and the Maori seats.
5. Works out who can govern under the parties' stated positions.
Writes data.json for the page.
"""
import json, math, datetime as dt
import numpy as np
import pandas as pd

RNG = np.random.default_rng(20261107)
PARTIES = ["NAT", "LAB", "GRN", "ACT", "NZF", "TPM", "OPP", "OTH"]
RESULT_2023 = dict(NAT=38.08, LAB=26.92, GRN=11.61, ACT=8.64, NZF=6.09, TPM=3.08, OPP=2.22, OTH=3.36)
T0 = dt.date(2023, 10, 14)
EDAY = dt.date(2026, 11, 7)
TODAY = dt.datetime.now(dt.timezone(dt.timedelta(hours=13))).date()  # NZ date (NZDT)
ASOF = TODAY
NDAYS = (EDAY - T0).days

# Which pollsters define "no lean" (the centre the others are measured against).
# Weights reflect track record at the 2017-2023 elections and whether the
# poll is commissioned by a party or released selectively.
ANCHOR_W = {"Verian": 1.0, "Reid": 1.0, "Curia": 1.0, "Freshwater": 0.8,
            "Roy Morgan": 0.5, "Anacta": 0.6}  # Anacta is Talbot Mills renamed (from Sept 2026)
LEAN_WINDOW_DAYS = 480                    # leans estimated on the last ~16 months, recent polls weighted most
LEAN_HALF = 180                           # days for a poll's weight in the lean estimate to fall by ~63%
DEFF = 1.5                                # design effect on top of pure sampling error

# Pack-wide correction from past elections (final polls vs result, 2017/2020/2023):
# Greens finished below the final-poll average in 2017 and 2023 and level in 2020.
CORRECTION = {"GRN": -0.8}
# Size of an election-day miss shared by all polls (percentage points, 1 sd),
# set from the 2017, 2020 and 2023 final-poll misses.
SYS_SD = dict(NAT=2.6, LAB=2.3, GRN=1.4, ACT=1.0, NZF=1.2, TPM=0.6, OPP=1.3, OTH=0.8)


def load_polls(path="polls.csv"):
    df = pd.read_csv(path, parse_dates=["start", "end"])
    df["mid"] = df["start"] + (df["end"] - df["start"]) / 2
    df["day"] = (df["mid"].dt.date - T0).apply(lambda d: d.days)
    df["n"] = df["n"].fillna(1000)
    named = PARTIES[:-1]
    full = df[named].notna().all(axis=1)
    # 'Others' is whatever is left when every named party is reported
    df.loc[full & df["OTH"].isna(), "OTH"] = (100 - df.loc[full, named].sum(axis=1)).clip(lower=0.2)
    return df.sort_values("day").reset_index(drop=True)


def kalman(obs, q, x0, p0):
    """Random-walk trend, daily steps, scalar Kalman filter + RTS smoother.
    obs: list (len NDAYS+1) of lists of (y, r)."""
    n = NDAYS + 1
    xp = np.zeros(n); pp = np.zeros(n); xf = np.zeros(n); pf = np.zeros(n)
    x, p, ll = x0, p0, 0.0
    for t in range(n):
        if t > 0:
            p = p + q
        xp[t], pp[t] = x, p
        for y, r in obs[t]:
            s = p + r
            k = p / s
            v = y - x
            ll += -0.5 * (math.log(2 * math.pi * s) + v * v / s)
            x = x + k * v
            p = (1 - k) * p
        xf[t], pf[t] = x, p
    xs = xf.copy(); ps = pf.copy()
    for t in range(n - 2, -1, -1):
        c = pf[t] / pp[t + 1]
        xs[t] = xf[t] + c * (xs[t + 1] - xp[t + 1])
        ps[t] = pf[t] + c * c * (ps[t + 1] - pp[t + 1])
    return xs, ps, ll


def fit_party(df, party, iters=12):
    d = df[df[party].notna()].copy()
    pollsters = sorted(d["pollster"].unique())
    h = {j: 0.0 for j in pollsters}
    tau2 = {j: 0.5 if party in ("NAT", "LAB") else 0.25 for j in pollsters}
    q_grid = [0.004, 0.008, 0.015, 0.03, 0.06, 0.12]
    q = 0.03
    p = d[party].clip(lower=0.3) / 100
    d["s2"] = DEFF * p * (1 - p) / d["n"] * 1e4
    age = (pd.Timestamp(ASOF) - d["mid"]).dt.days.clip(lower=0)
    recent = age <= LEAN_WINDOW_DAYS
    d["w_recent"] = np.exp(-age / LEAN_HALF) * recent
    for it in range(iters):
        def build(qv):
            obs = [[] for _ in range(NDAYS + 1)]
            for _, r in d.iterrows():
                obs[int(r["day"])].append((r[party] - h[r["pollster"]], r["s2"] + tau2[r["pollster"]]))
            return obs
        obs = build(q)
        if it in (0, 4, 8):
            best = None
            for qv in q_grid:
                _, _, ll = kalman(obs, qv, RESULT_2023[party], 0.02)
                if best is None or ll > best[0]:
                    best = (ll, qv)
            q = best[1]
        xs, ps, _ = kalman(obs, q, RESULT_2023[party], 0.02)
        d["trend"] = xs[d["day"].astype(int).values]
        d["resid"] = d[party] - d["trend"]
        # pollster leans from recent polls, shrunk towards zero when evidence is thin
        newh = {}
        for j in pollsters:
            sel = d[(d["pollster"] == j) & (d["w_recent"] > 0)]
            if len(sel) == 0:
                newh[j] = 0.0
                continue
            w = sel["w_recent"] / (sel["s2"] + tau2[j])
            mean = float((w * sel["resid"]).sum() / w.sum())
            neff = float(w.sum() ** 2 / (w ** 2).sum())
            newh[j] = mean * neff / (neff + 1.5)
        # anchor: weighted average lean of the reference pollsters is zero
        act = [j for j in pollsters if (d[(d["pollster"] == j)]["w_recent"] > 0).any()]
        aw = np.array([ANCHOR_W.get(j, 0.5) for j in act])
        centre = float(np.sum(aw * np.array([newh[j] for j in act])) / aw.sum())
        h = {j: newh[j] - centre for j in pollsters}
        # extra (non-sampling) noise per pollster
        for j in pollsters:
            sel = d[d["pollster"] == j]
            e = sel[party] - h[j] - sel["trend"]
            floor = 0.3 if party in ("NAT", "LAB") else 0.12
            tau2[j] = max(floor, float((e ** 2 - sel["s2"]).mean())) if len(sel) >= 3 else 0.6
    obs = [[] for _ in range(NDAYS + 1)]
    for _, r in d.iterrows():
        obs[int(r["day"])].append((r[party] - h[r["pollster"]], r["s2"] + tau2[r["pollster"]]))
    xs, ps, _ = kalman(obs, q, RESULT_2023[party], 0.02)
    d["adj"] = d[party] - d["pollster"].map(h)
    return dict(xs=xs, ps=ps, q=q, h=h, tau2=tau2, pts=d[["mid", "pollster", party, "adj"]])


# ---------------------------------------------------------------- electorates
# General electorates on the 2025 boundaries: notional 2023 margin of National
# over Labour (percentage points). Positive = National ahead.
# Notional figures for the four seats that changed hands on paper (Waitakere,
# Henderson, Wigram, Wellington North) are The Tally Room's (tallyroom.com.au/62140);
# Kapiti and Kenepuru are the tracker's own estimates from their parts; seats whose
# boundaries moved a lot (Hutt South, Maungakiekie, Mount Roskill, Christchurch
# Central, Palmerston North, Mount Albert) are adjusted in the direction The Spinoff's
# area-by-area figures point; Port Waikato uses the party vote (Labour sat out the
# 2023 by-election). Everything else carries its 2023 margin (majority / ~380 votes).
NAT_HELD = {
    "Banks Peninsula": 1.0, "Mount Maunganui": 40.5, "Botany": 43.0, "Coromandel": 44.8,
    "East Cape": 8.2, "East Coast Bays": 53.6, "Hamilton East": 13.3, "Hamilton West": 17.1,
    "Henderson": 2.4, "Hutt South": 2.5, "Ilam": 25.0, "Invercargill": 26.0, "Kaikoura": 30.0,
    "Kaipara ki Mahurangi": 51.2, "Kapiti": 14.0, "Maungakiekie": 9.5, "Mount Roskill": 6.0,
    "Napier": 23.3, "New Plymouth": 18.4, "North Shore": 43.0, "Northcote": 24.4,
    "Northland": 16.0, "Pakuranga": 49.2, "Papakura": 35.4, "Port Waikato": 30.0,
    "Rangitata": 28.5, "Rangitikei": 25.8, "Rotorua": 23.5, "Selwyn": 50.0, "Southland": 45.3,
    "Takanini": 23.1, "Taranaki-King Country": 37.8, "Taupo": 43.4, "Tauranga": 24.7,
    "Tukituki": 26.6, "Upper Harbour": 29.5, "Waikato": 47.5, "Waimakariri": 34.2,
    "Wairarapa": 7.4, "Waitaki": 32.0, "West Coast-Tasman": 2.7, "Whanganui": 14.3,
    "Whangaparaoa": 61.5, "Whangarei": 30.1, "Wigram": 7.2,
}
LAB_HELD = {
    "Christchurch Central": -8.0, "Christchurch East": -6.3, "Dunedin": -21.0, "Glendene": -11.6,
    "Kenepuru": -15.0, "Mangere": -30.8, "Manurewa": -18.7, "Mount Albert": -0.3, "Nelson": -0.07,
    "Otahuhu": -21.0, "Palmerston North": -6.5, "Remutaka": -23.3, "Taieri": -3.8, "Waitakere": -0.9,
}
# Candidate changes since 2023 (points added to National's margin): about two points
# off a party whose MP is standing down, and a smaller lift for National MPs first
# elected in 2023 who face no former MP this time.
STANDING_DOWN = 2.0
FIRST_TERM = 1.5
CANDIDATE_ADJ = {
    "Kaipara ki Mahurangi": -STANDING_DOWN, "Papakura": -STANDING_DOWN, "Port Waikato": -STANDING_DOWN,
    "Whangarei": -STANDING_DOWN, "Waitakere": -STANDING_DOWN, "West Coast-Tasman": -STANDING_DOWN,
    "Christchurch Central": STANDING_DOWN, "Wigram": STANDING_DOWN,
    **{k: FIRST_TERM for k in ["East Cape", "Takanini", "Whanganui", "New Plymouth", "Napier", "Ilam",
                                "Tukituki", "Hamilton East", "Upper Harbour"]},
}
# 2026 electorate polls (National minus Labour, points)
SEAT_POLLS = {"Hutt South": -12.0, "Kapiti": -3.9, "Waitaki": 23.0,
              "West Coast-Tasman": 6.0, "Mount Albert": -3.0}
# Tamaki: open after ACT's Brooke van Velden stood down; National (Mahesh Muralidhar)
# against ACT (James Christmas), National won the party vote there with 52% in 2023.
TAMAKI_NAT_MARGIN = -2.0   # National minus ACT, points; sd 8 gives National about 40%
TAMAKI_LAB = 0.05
# Maori seats: chance each candidate wins, from the Whakaata Maori-Curia seat polls
# (21 Sept to 15 Oct 2026) and later news. Tamaki Makaurau: Kaipara 36, Leoni 34,
# Te Ohaere 23 of decided voters, then Leoni quit as Labour's candidate on 23 Oct but
# stays on the ballot.
MAORI = {
    "Hauraki-Waikato": {"TPM": 0.92, "LAB": 0.08},
    "Waiariki": {"TPM": 0.96, "GRN": 0.02, "LAB": 0.02},
    "Te Tai Hauauru": {"TPM": 0.80, "LAB": 0.20},
    "Tamaki Makaurau": {"TPM": 0.55, "GRN": 0.30, "LAB": 0.15},
    "Te Tai Tokerau": {"GRN": 0.45, "LAB": 0.25, "TPM": 0.18, "TTT": 0.12},
    "Ikaroa-Rawhiti": {"LAB": 0.88, "TPM": 0.08, "GRN": 0.04},
    "Te Tai Tonga": {"LAB": 0.82, "TPM": 0.07, "IND": 0.06, "GRN": 0.05},
}


def sainte_lague(votes, seats):
    names = list(votes)
    alloc = {k: 0 for k in names}
    v = np.array([votes[k] for k in names], dtype=float)
    a = np.zeros(len(names))
    for _ in range(seats):
        i = int(np.argmax(v / (2 * a + 1)))
        a[i] += 1
    for i, k in enumerate(names):
        alloc[k] = int(a[i])
    return alloc


def simulate(proj, nsim=20000, nat_overhang=True):
    m = np.array([proj[p]["mean"] for p in PARTIES])
    sd_trend = np.array([proj[p]["sd"] for p in PARTIES])
    sys_sd = np.array([SYS_SD[p] for p in PARTIES])
    corr = np.eye(len(PARTIES))
    corr[0, 1] = corr[1, 0] = -0.4
    cov = np.outer(sys_sd, sys_sd) * corr
    L = np.linalg.cholesky(cov)
    df_t = 5
    z = RNG.standard_normal((nsim, len(PARTIES)))
    chi = RNG.chisquare(df_t, nsim) / df_t
    sys = (z @ L.T) * math.sqrt((df_t - 2) / df_t) / np.sqrt(chi)[:, None]
    base = m + RNG.standard_normal((nsim, len(PARTIES))) * sd_trend
    votes = np.clip(base + sys, 0.05, None)
    votes = votes / votes.sum(axis=1, keepdims=True) * 100
    V = {p: votes[:, i] for i, p in enumerate(PARTIES)}

    # ---- electorates
    swing = 0.8 * ((V["NAT"] - RESULT_2023["NAT"]) - (V["LAB"] - RESULT_2023["LAB"]))
    nat_noise = RNG.standard_normal(nsim) * 2.0
    nat_seats = np.zeros(nsim)
    seat_win = {}
    for name, m23 in {**NAT_HELD, **LAB_HELD}.items():
        exp_margin = m23 + CANDIDATE_ADJ.get(name, 0.0) + swing + nat_noise
        if name in SEAT_POLLS:
            exp_margin = 0.6 * SEAT_POLLS[name] + 0.4 * exp_margin
            noise = 7.0
        else:
            noise = 6.0
        mar = exp_margin + RNG.standard_normal(nsim) * noise
        win = mar > 0
        seat_win[name] = win.mean()
        nat_seats += win
    # Auckland Central: National v Greens (July 2026 poll NAT 30, GRN 25)
    ac = 5 + 0.8 * ((V["NAT"] - 30.5) - (V["GRN"] - 10.4)) + RNG.standard_normal(nsim) * 7
    seat_win["Auckland Central"] = (ac > 0).mean()
    nat_seats += ac > 0
    # Tamaki: National v ACT, moving with how the two parties do against today's projection
    i_nat, i_act = PARTIES.index("NAT"), PARTIES.index("ACT")
    tm = TAMAKI_NAT_MARGIN + 0.5 * ((V["NAT"] - m[i_nat]) - (V["ACT"] - m[i_act])) + RNG.standard_normal(nsim) * 8
    lab_tm = RNG.random(nsim) < TAMAKI_LAB
    tam_nat = (tm > 0) & ~lab_tm
    seat_win["Tamaki"] = tam_nat.mean()
    nat_seats += tam_nat

    # Maori seats with a shared swing for Te Pati Maori
    tpm_shift = RNG.standard_normal(nsim) * 0.6
    elec = {k: np.zeros(nsim, dtype=int) for k in ["TPM", "TTT", "IND", "LAB", "GRN"]}
    maori_detail = {}
    for seat, probs in MAORI.items():
        names = list(probs)
        p = np.array([probs[k] for k in names])
        logit = np.log(p)
        logit_mat = np.tile(logit, (nsim, 1))
        if "TPM" in names:
            logit_mat[:, names.index("TPM")] += tpm_shift
        pm = np.exp(logit_mat)
        pm /= pm.sum(axis=1, keepdims=True)
        u = RNG.random(nsim)[:, None]
        pick = (pm.cumsum(axis=1) < u).sum(axis=1)
        maori_detail[seat] = {names[i]: float((pick == i).mean()) for i in range(len(names))}
        for i, k in enumerate(names):
            elec[k] += pick == i
    # Opportunity's leader in Mt Albert (polling fourth): small chance
    opp_elec = (RNG.random(nsim) < 0.02).astype(int)

    # ---- seats
    out = {k: np.zeros(nsim, dtype=int) for k in ["NAT", "LAB", "GRN", "ACT", "NZF", "TPM", "OPP", "TTT", "IND"]}
    total = np.zeros(nsim, dtype=int)
    over_by = {k: np.zeros(nsim, dtype=int) for k in ["NAT", "TPM", "TTT", "OPP"]}
    ttt_vote = np.minimum(0.3, V["OTH"])
    for s in range(nsim):
        pv = {"NAT": V["NAT"][s], "LAB": V["LAB"][s], "GRN": V["GRN"][s], "ACT": V["ACT"][s],
              "NZF": V["NZF"][s], "TPM": V["TPM"][s], "OPP": V["OPP"][s], "TTT": ttt_vote[s]}
        ew = {"NAT": int(nat_seats[s]) if nat_overhang else 1, "ACT": 1, "GRN": 1, "TPM": int(elec["TPM"][s]),
              "TTT": int(elec["TTT"][s]), "OPP": int(opp_elec[s]), "NZF": 0, "LAB": 1}
        qual = {k: v for k, v in pv.items() if v >= 5.0 or ew.get(k, 0) > 0}
        ind = int(elec["IND"][s])
        alloc = sainte_lague(qual, 120 - ind)
        tot = 120
        for k in pv:
            a = alloc.get(k, 0)
            e = ew.get(k, 0)
            seats_k = max(a, e) if k in qual else 0
            if seats_k > a:
                tot += seats_k - a
                if k in over_by:
                    over_by[k][s] = seats_k - a
            out[k][s] = seats_k
        out["IND"][s] = ind
        total[s] = tot
    return V, out, total, seat_win, maori_detail, nat_seats, over_by


def govern(out, total):
    maj = total // 2 + 1
    right = out["NAT"] + out["ACT"] + out["NZF"]
    left = out["LAB"] + out["GRN"] + out["TPM"] + out["TTT"] + out["IND"]
    opp = out["OPP"]
    R = right >= maj
    L = left >= maj
    LO = (~R) & (~L) & (left + opp >= maj)
    RO_only = (~R) & (~L) & (~LO) & (right + opp >= maj)
    hung = ~(R | L | LO | RO_only)
    # if Opportunity were open to both: it talks first to the bigger of National/Labour
    nat_big = out["NAT"] > out["LAB"]
    tie = out["NAT"] == out["LAB"]
    coin = RNG.random(len(total)) < 0.5
    first_right = nat_big | (tie & coin)
    r_w_opp = right + opp >= maj
    l_w_opp = left + opp >= maj
    soft_right = R | ((~R) & (~L) & ((first_right & r_w_opp) | (~first_right & ~l_w_opp & r_w_opp)))
    soft_left = L | ((~R) & (~L) & ((~first_right & l_w_opp) | (first_right & ~r_w_opp & l_w_opp)))
    return dict(
        right_alone=float(R.mean()), left_alone=float(L.mean()),
        left_with_opp=float(LO.mean()), right_needs_opp_only=float(RO_only.mean()),
        hung=float(hung.mean()),
        opp_decides=float(((~R) & (~L) & (r_w_opp | l_w_opp)).mean()),
        stated_luxon=float(R.mean()), stated_hipkins=float((L | LO).mean()),
        stated_stuck=float((RO_only | hung).mean()),
        soft_luxon=float(soft_right.mean()), soft_hipkins=float(soft_left.mean()),
        soft_hung=float((~soft_right & ~soft_left).mean()),
        right_seats=right, left_seats=left, maj=maj,
    )


def q(a, p):
    return float(np.percentile(a, p))


def run(asof, nsim=20000, full=True):
    global ASOF
    ASOF = asof
    df = load_polls()
    df = df[df["end"].dt.date <= asof].reset_index(drop=True)
    fits = {p: fit_party(df, p) for p in PARTIES}
    tday = (min(asof, EDAY) - T0).days
    proj = {}
    for p in PARTIES:
        f = fits[p]
        mean = f["xs"][NDAYS] + CORRECTION.get(p, 0.0)
        proj[p] = dict(mean=float(mean), sd=float(math.sqrt(f["ps"][NDAYS])),
                       now=float(f["xs"][tday]), now_sd=float(math.sqrt(f["ps"][tday])), q=f["q"])
    V, out, total, seat_win, maori_detail, nat_elec, over_by = simulate(proj, nsim)
    g = govern(out, total)
    if not full:
        return dict(asof=asof.isoformat(), luxon=g["stated_luxon"], hipkins=g["stated_hipkins"],
                    stuck=g["stated_stuck"], soft_luxon=g["soft_luxon"], soft_hipkins=g["soft_hipkins"],
                    right_alone=g["right_alone"], opp_decides=g["opp_decides"],
                    opp_over5=float((V["OPP"] >= 5).mean()),
                    nat=proj["NAT"]["now"], lab=proj["LAB"]["now"])
    # how much the National overhang matters: same simulation, National held to its list share
    RNG_state = RNG.bit_generator.state
    _, out2, total2, _, _, _, _ = simulate(proj, nsim // 2, nat_overhang=False)
    RNG.bit_generator.state = RNG_state
    g2 = govern(out2, total2)
    no_nat_ov = dict(luxon=g2["stated_luxon"], hipkins=g2["stated_hipkins"], stuck=g2["stated_stuck"],
                     soft_luxon=g2["soft_luxon"], soft_hipkins=g2["soft_hipkins"],
                     right_alone=g2["right_alone"], total_median=q(total2, 50))
    maj = total // 2 + 1
    right = out["NAT"] + out["ACT"] + out["NZF"]
    nat_ov = over_by["NAT"] > 0
    cond = {}
    for label, mask in (("nat_overhang", nat_ov), ("no_nat_overhang", ~nat_ov)):
        if mask.sum() > 0:
            cond[label] = dict(share=float(mask.mean()), right_alone=float((right[mask] >= maj[mask]).mean()))

    # ---- outputs
    days = [(T0 + dt.timedelta(days=int(t))).isoformat() for t in range(0, NDAYS + 1, 2)]
    worm = {p: {"mid": [round(float(x), 2) for x in fits[p]["xs"][::2]],
                "sd": [round(float(math.sqrt(v)), 2) for v in fits[p]["ps"][::2]]} for p in PARTIES}
    pts = []
    for _, r in df.iterrows():
        row = {"date": r["mid"].date().isoformat(), "pollster": r["pollster"], "n": int(r["n"]),
               "start": r["start"].date().isoformat(), "end": r["end"].date().isoformat()}
        for p in PARTIES:
            if pd.notna(r[p]):
                row[p] = float(r[p])
                row[p + "_adj"] = round(float(r[p] - fits[p]["h"].get(r["pollster"], 0.0)), 2)
        pts.append(row)
    leans = {}
    for pol in sorted(df["pollster"].unique()):
        leans[pol] = {p: round(float(fits[p]["h"].get(pol, 0.0)), 2) for p in PARTIES}
        leans[pol]["count_recent"] = int(((df["pollster"] == pol) & ((pd.Timestamp(asof) - df["mid"]).dt.days <= LEAN_WINDOW_DAYS)).sum())
    seats = {}
    for k in ["NAT", "LAB", "GRN", "ACT", "NZF", "TPM", "OPP", "TTT", "IND"]:
        a = out[k]
        seats[k] = dict(median=q(a, 50), lo=q(a, 10), hi=q(a, 90), mean=float(a.mean()),
                        dist={str(int(v)): float((a == v).mean()) for v in np.unique(a)})
    votes = {p: dict(mean=float(V[p].mean()), lo=q(V[p], 10), hi=q(V[p], 90)) for p in PARTIES}
    over = total - 120
    res = {
        "generated": dt.datetime.now(dt.timezone(dt.timedelta(hours=13))).strftime("%Y-%m-%d %H:%M NZDT"),
        "today": TODAY.isoformat(), "eday": EDAY.isoformat(), "npolls": int(len(df)),
        "proj": proj, "votes_eday": votes, "seats": seats,
        "total_seats": dict(median=q(total, 50), lo=q(total, 10), hi=q(total, 90),
                            dist={str(int(v)): float((total == v).mean()) for v in np.unique(total)}),
        "overhang_any": float((over > 0).mean()),
        "nat_elec": dict(median=q(nat_elec, 50), lo=q(nat_elec, 10), hi=q(nat_elec, 90)),
        "overhang_by": {k: dict(p_any=float((v > 0).mean()), mean=float(v.mean())) for k, v in over_by.items()},
        "opp_over5": float((V["OPP"] >= 5).mean()),
        "opp_in": float((out["OPP"] > 0).mean()),
        "nat_most_seats": float((out["NAT"] > out["LAB"]).mean()),
        "lab_most_seats": float((out["LAB"] > out["NAT"]).mean()),
        "tie_most_seats": float((out["LAB"] == out["NAT"]).mean()),
        "nat_more_votes": float((V["NAT"] > V["LAB"]).mean()),
        "govern": {k: v for k, v in g.items() if not isinstance(v, np.ndarray)},
        "conditional": cond,
        "no_nat_overhang": no_nat_ov,
        "bloc_seats": {"right": dict(median=q(g["right_seats"], 50), lo=q(g["right_seats"], 10), hi=q(g["right_seats"], 90)),
                       "left": dict(median=q(g["left_seats"], 50), lo=q(g["left_seats"], 10), hi=q(g["left_seats"], 90)),
                       "maj": dict(median=q(g["maj"], 50))},
        "worm": {"days": days, "series": worm},
        "polls": pts, "leans": leans, "seat_win": seat_win, "maori": maori_detail,
    }
    # National overhang chance: electorates beyond its list share
    return res


def main():
    import sys
    res = run(TODAY)
    hist_path = "history.json"
    if "--history" in sys.argv:
        hist = []
        d = dt.date(2026, 6, 1)
        while d < TODAY:
            hist.append(run(d, nsim=6000, full=False))
            print("history", d, hist[-1]["luxon"], hist[-1]["hipkins"], flush=True)
            d += dt.timedelta(days=7)
        with open(hist_path, "w") as fh:
            json.dump(hist, fh)
    try:
        hist = json.load(open(hist_path))
    except Exception:
        hist = []
    hist = [h for h in hist if h["asof"] < TODAY.isoformat()]
    hist.append(dict(asof=TODAY.isoformat(), luxon=res["govern"]["stated_luxon"], hipkins=res["govern"]["stated_hipkins"],
                     stuck=res["govern"]["stated_stuck"], soft_luxon=res["govern"]["soft_luxon"],
                     soft_hipkins=res["govern"]["soft_hipkins"], right_alone=res["govern"]["right_alone"],
                     opp_decides=res["govern"]["opp_decides"], opp_over5=res["opp_over5"],
                     nat=res["proj"]["NAT"]["now"], lab=res["proj"]["LAB"]["now"]))
    res["history"] = hist
    with open(hist_path, "w") as fh:
        json.dump(hist, fh)
    with open("data.json", "w") as fh:
        json.dump(res, fh)
    # quick console summary
    proj, leans, seats, maori_detail = res["proj"], res["leans"], res["seats"], res["maori"]
    print("polls:", res["npolls"])
    for p in PARTIES:
        print(f"{p}: now {proj[p]['now']:.1f} (sd {proj[p]['now_sd']:.2f}) eday {proj[p]['mean']:.1f} q={proj[p]['q']}")
    print("leans:")
    for pol, l in leans.items():
        print(f"  {pol:13s}", " ".join(f"{p}:{l[p]:+.1f}" for p in PARTIES), "n", l["count_recent"])
    for k, v in seats.items():
        print(f"seats {k}: {v['median']} ({v['lo']}-{v['hi']})")
    print("total", res["total_seats"], "overhang any", res["overhang_any"])
    print("nat electorates", res["nat_elec"])
    print("OPP >=5%", res["opp_over5"], "OPP in", res["opp_in"])
    print("govern", json.dumps(res["govern"], indent=1))
    print("bloc", res["bloc_seats"])
    print("most seats NAT", res["nat_most_seats"], "LAB", res["lab_most_seats"], "tie", res["tie_most_seats"], "nat more votes", res["nat_more_votes"])
    print("no NAT overhang", res["no_nat_overhang"])
    print("conditional", res["conditional"], "overhang_by", res["overhang_by"])
    print("maori", json.dumps(maori_detail))


if __name__ == "__main__":
    main()
