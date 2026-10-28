"""Turn data.json (model output) into the dashboard's dataset files in out/."""
import json, os, datetime as dt

D = json.load(open("data.json"))
os.makedirs("out", exist_ok=True)
POLLSTER = {"Verian": "1News-Verian", "Reid": "RNZ-Reid Research", "Curia": "Taxpayers' Union-Curia",
            "Roy Morgan": "Roy Morgan", "Talbot Mills": "Talbot Mills", "Freshwater": "Post-Freshwater", "Anacta": "Anacta"}
NAMES = {"NAT": "National", "LAB": "Labour", "GRN": "Greens", "NZF": "NZ First", "ACT": "ACT",
         "OPP": "Opportunity", "TPM": "Te Pāti Māori", "TTT": "Te Tai Tokerau Party", "IND": "Independent", "OTH": "Others"}
SHOW = ["NAT", "LAB", "GRN", "NZF", "ACT", "OPP", "TPM"]
SHORT = {"NAT": "NAT", "LAB": "LAB", "GRN": "GRN", "NZF": "NZF", "ACT": "ACT", "OPP": "TOP", "TPM": "TPM", "TTT": "TTT"}
r2 = lambda x: None if x is None else round(float(x), 2)
r4 = lambda x: round(float(x), 4)


def dump(name, rows):
    with open(f"out/{name}.json", "w") as fh:
        json.dump(rows, fh, ensure_ascii=False, separators=(",", ":"))


g = D["govern"]
nn = D["no_nat_overhang"]
views = [("stated", "Stated positions", g["stated_luxon"], g["stated_stuck"], g["stated_hipkins"]),
         ("open", "If Opportunity is open to both sides", g["soft_luxon"], g["soft_hung"], g["soft_hipkins"]),
         ("no_overhang", "Stated positions, if National gets no extra electorate seats", nn["luxon"], nn["stuck"], nn["hipkins"])]
chances = []
for key, label, l, s, h in views:
    chances += [dict(view=key, view_label=label, outcome="Luxon-led", chance=r4(l)),
                dict(view=key, view_label=label, outcome="No clear majority", chance=r4(s)),
                dict(view=key, view_label=label, outcome="Hipkins-led", chance=r4(h))]
dump("chances", chances)

# trend (every second day), from the 2023 election to election day
days = D["worm"]["days"]
today = D["today"]
trend = []
for i, d in enumerate(days):
    for p in SHOW:
        m = D["worm"]["series"][p]["mid"][i]
        s = D["worm"]["series"][p]["sd"][i]
        trend.append(dict(date=d, party=p, mid=r2(m), lo=r2(max(0, m - 1.645 * s)), hi=r2(m + 1.645 * s),
                          ahead=d > today))
dump("trend", trend)

polls_long, latest = [], []
for r in D["polls"]:
    pid = f"{POLLSTER[r['pollster']]} {dt.date.fromisoformat(r['start']).strftime('%-d %b %Y')}"
    for p in SHOW:
        if p in r:
            polls_long.append(dict(poll=pid, pollster=POLLSTER[r["pollster"]], date=r["date"], party=p,
                                   published=r[p], lean_removed=r[p + "_adj"]))
srt = sorted(D["polls"], key=lambda r: (r["end"], r["start"]), reverse=True)[:14]
for r in srt:
    s, e = dt.date.fromisoformat(r["start"]), dt.date.fromisoformat(r["end"])
    when = f"{s.day}–{e.strftime('%-d %b')}" if s.month == e.month else f"{s.strftime('%-d %b')}–{e.strftime('%-d %b')}"
    row = dict(poll=f"{POLLSTER[r['pollster']]} {s.strftime('%-d %b')}", pollster=POLLSTER[r["pollster"]], fieldwork=when, end=r["end"], sample=r["n"])
    for p in SHOW:
        row[p] = r.get(p)
    latest.append(row)
dump("polls", polls_long)
dump("latest", latest)

leans = []
for pol, l in D["leans"].items():
    for p in ["NAT", "LAB", "GRN", "NZF", "ACT", "OPP"]:
        leans.append(dict(pollster=POLLSTER[pol], party=p, lean=r2(l[p]), recent_polls=l["count_recent"]))
dump("leans", leans)
leans_wide = []
for pol, l in D["leans"].items():
    row = dict(pollster=POLLSTER[pol])
    for p in ["NAT", "LAB", "GRN", "NZF", "ACT", "OPP"]:
        row[p] = r2(l[p])
    row["recent_polls"] = l["count_recent"]
    leans_wide.append(row)
leans_wide.sort(key=lambda r: -r["recent_polls"])
dump("leans_wide", leans_wide)

eday = []
for p in SHOW + ["TTT"]:
    v = D["votes_eday"].get(p)
    st = D["seats"][p]
    eday.append(dict(party=p, name=NAMES[p], short=SHORT[p],
                     now=r2(D["proj"][p]["now"]) if p in D["proj"] else None,
                     vote_mid=r2(v["mean"]) if v else None, vote_lo=r2(v["lo"]) if v else None, vote_hi=r2(v["hi"]) if v else None,
                     seats_mid=st["median"], seats_lo=st["lo"], seats_hi=st["hi"]))
dump("eday", eday)

bs = D["bloc_seats"]
ob = D["overhang_by"]
summary_vals = dict(
    polls_count=D["npolls"], total_mid=D["total_seats"]["median"], total_lo=D["total_seats"]["lo"],
    total_hi=D["total_seats"]["hi"], maj_mid=bs["maj"]["median"],
    right_mid=bs["right"]["median"], right_lo=bs["right"]["lo"], right_hi=bs["right"]["hi"],
    left_mid=bs["left"]["median"], left_lo=bs["left"]["lo"], left_hi=bs["left"]["hi"],
    opp_mid=D["seats"]["OPP"]["median"],
    nat_elec_mid=D["nat_elec"]["median"], nat_elec_lo=D["nat_elec"]["lo"], nat_elec_hi=D["nat_elec"]["hi"],
    nat_overhang_p=r4(ob["NAT"]["p_any"]), nat_overhang_mean=r2(ob["NAT"]["mean"]),
    tpm_overhang_p=r4(ob["TPM"]["p_any"]), tpm_overhang_mean=r2(ob["TPM"]["mean"]),
    overhang_any=r4(D["overhang_any"]), opp_over5=r4(D["opp_over5"]), opp_decides=r4(g["opp_decides"]),
    nat_most_seats=r4(D["nat_most_seats"]), lab_most_seats=r4(D["lab_most_seats"]),
    nat_more_votes=r4(D["nat_more_votes"]), right_alone=r4(g["right_alone"]),
    left_alone=r4(g["left_alone"]), left_with_opp=r4(g["left_with_opp"]),
    right_needs_opp=r4(g["right_needs_opp_only"]), simulations=20000,
    updated=dt.datetime.strptime(D["generated"][:16], "%Y-%m-%d %H:%M").strftime("%-d %b, %-I:%M%p").replace("AM", "am").replace("PM", "pm"),
    nonat_luxon=r4(nn["luxon"]), nonat_hipkins=r4(nn["hipkins"]),
)
summary = [dict(metric=k, value=v) for k, v in summary_vals.items()]
dump("summary", summary)

hist = [dict(asof=h["asof"], luxon=r4(h["luxon"]), hipkins=r4(h["hipkins"]), stuck=r4(h["stuck"]),
             open_luxon=r4(h["soft_luxon"]), open_hipkins=r4(h["soft_hipkins"]), opp_over5=r4(h["opp_over5"]))
        for h in D.get("history", [])]
dump("history", hist)

dist = D["total_seats"]["dist"]
dump("parliament", [dict(seats=int(k), chance=r4(v)) for k, v in sorted(dist.items(), key=lambda kv: int(kv[0])) if v >= 0.002])

MAORI_NAMES = {"Hauraki-Waikato": "Hauraki-Waikato", "Waiariki": "Waiariki", "Te Tai Hauauru": "Te Tai Hauāuru",
               "Tamaki Makaurau": "Tāmaki Makaurau", "Te Tai Tokerau": "Te Tai Tokerau", "Ikaroa-Rawhiti": "Ikaroa-Rāwhiti",
               "Te Tai Tonga": "Te Tai Tonga"}
maori = []
for seat, probs in D["maori"].items():
    row = dict(seat=MAORI_NAMES[seat])
    for k in ["TPM", "LAB", "GRN", "TTT", "IND"]:
        row[k] = r4(probs.get(k, 0.0))
    maori.append(row)
maori.sort(key=lambda r: -r["TPM"])
dump("maori", maori)

SEAT_NAMES = {"Otaki / Kapiti": "Ōtaki / Kāpiti", "Kaikoura": "Kaikōura", "Rangitikei": "Rangitīkei", "Taupo": "Taupō",
              "Whangaparaoa": "Whangaparāoa", "Whangarei": "Whangārei", "Mangere": "Māngere",
              "Panmure-Otahuhu": "Panmure-Ōtāhuhu", "Ohariu": "Ōhāriu", "Te Atatu": "Te Atatū"}
HELD = {"Mount Albert": "Labour", "Nelson": "Labour", "Te Atatu": "Labour", "Ohariu": "Labour", "Taieri": "Labour",
        "Wigram": "Labour", "Christchurch Central": "Labour", "Christchurch East": "Labour", "Palmerston North": "Labour",
        "Auckland Central": "Greens"}
POLLED = {"Hutt South": "Labour +12 (Sept poll)", "Otaki / Kapiti": "Labour +4 (July poll)", "Waitaki": "National +23 (Sept poll)",
          "West Coast-Tasman": "National +6 (Sept poll)", "Mount Albert": "Labour +1 to +5 (Sept–Oct polls)",
          "Auckland Central": "National +5 over Greens (July poll)"}
close = []
for seat, p in D["seat_win"].items():
    if 0.05 <= p <= 0.95:
        close.append(dict(seat=SEAT_NAMES.get(seat, seat), held_2023=HELD.get(seat, "National"),
                          national_chance=r4(p), local_poll=POLLED.get(seat, "None published")))
close.sort(key=lambda r: -r["national_chance"])
dump("close_seats", close)

# Market rows are kept by hand in markets_in.json (see the inclusion rule on the page)
markets = json.load(open("markets_in.json"))
dump("markets", markets)
print("wrote", sorted(os.listdir("out")))
for f in sorted(os.listdir("out")):
    print(f, os.path.getsize("out/" + f))
