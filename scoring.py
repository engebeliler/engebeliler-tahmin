from database import fetchall, get_setting

def calculate_points():
    users = fetchall("SELECT id,name,initial_points FROM users")
    scores = {u["id"]: {"name": u["name"], "points": int(u["initial_points"] or 0)} for u in users}

    matches = fetchall("""
        SELECT id, home_score, away_score, match_type
        FROM matches
        WHERE home_score IS NOT NULL AND away_score IS NOT NULL
    """)

    for m in matches:
        mid = m["id"]
        hs = m["home_score"]
        away_s = m["away_score"]
        mtype = m["match_type"]

        preds = fetchall("""
            SELECT user_id, pred_home, pred_away
            FROM predictions
            WHERE match_id=?
        """, (mid,))

        exact_users = [p["user_id"] for p in preds if p["pred_home"] == hs and p["pred_away"] == away_s]

        if len(exact_users) == 1:
            scores[exact_users[0]]["points"] += 6 if mtype == "Final" else 4
        elif len(exact_users) > 1:
            for uid in exact_users:
                scores[uid]["points"] += 5 if mtype == "Final" else 3

        actual_result = 1 if hs > away_s else -1 if hs < away_s else 0

        for p in preds:
            uid = p["user_id"]
            if uid in exact_users:
                continue
            pred_result = 1 if p["pred_home"] > p["pred_away"] else -1 if p["pred_home"] < p["pred_away"] else 0
            if pred_result == actual_result:
                scores[uid]["points"] += 1

    champion = get_setting("champion")
    if champion:
        for r in fetchall("SELECT user_id, team FROM champion_predictions"):
            if r["team"] and r["team"].strip().lower() == champion.strip().lower():
                scores[r["user_id"]]["points"] += 8

    golden_boot = get_setting("golden_boot")
    if golden_boot:
        for r in fetchall("SELECT user_id, player FROM golden_boot_predictions"):
            if r["player"] and r["player"].strip().lower() == golden_boot.strip().lower():
                scores[r["user_id"]]["points"] += 6

    return scores
