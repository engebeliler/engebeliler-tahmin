import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path

from config import APP_TITLE, ADMIN_PASSWORD
from database import init_db, fetch_df, execute, fetchone, set_setting, get_setting
from scoring import calculate_points
from backup import create_backup
from export import to_excel_bytes

st.set_page_config(page_title="Engebeliler Tahmin", layout="wide")
init_db()

if Path("assets/logo.png").exists():
    st.image("assets/logo.png", width=120)

st.title(APP_TITLE)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    pwd = st.text_input("Yönetici Şifresi", type="password")
    if st.button("Giriş Yap"):
        if pwd == ADMIN_PASSWORD:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Şifre hatalı.")
    st.stop()

menu = st.sidebar.radio("Menü", [
    "Puan Durumu",
    "Kullanıcı Yönetimi",
    "Maç Yönetimi",
    "Tahmin Gir",
    "Sonuç Gir / Düzelt",
    "Bonus Tahminler",
    "Tahmin Listesi",
    "Excel / Yedek"
])

def match_label_df():
    return fetch_df("""
        SELECT id,
        home_team || ' - ' || away_team || ' (' || match_type || ')' AS mac,
        match_datetime
        FROM matches
        ORDER BY id
    """)

if menu == "Puan Durumu":
    scores = calculate_points()
    rows = []
    for v in scores.values():
        rows.append([v["name"], v["points"]])
    df = pd.DataFrame(rows, columns=["Kullanıcı", "Puan"]).sort_values("Puan", ascending=False).reset_index(drop=True)
    medals = ["🥇", "🥈", "🥉"]
    df.insert(0, "Sıra", [medals[i] if i < 3 else str(i+1) for i in range(len(df))])
    st.dataframe(df, use_container_width=True)

elif menu == "Kullanıcı Yönetimi":
    st.subheader("Kullanıcı Ekle")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Kullanıcı Adı")
    with col2:
        initial = st.number_input("Başlangıç Puanı", min_value=0, max_value=10000, value=0)
    if st.button("Kullanıcı Ekle"):
        try:
            execute("INSERT INTO users(name, initial_points) VALUES(?,?)", (name.strip(), initial))
            st.success("Kullanıcı eklendi.")
        except Exception as e:
            st.error(f"Kullanıcı eklenemedi: {e}")

    users = fetch_df("SELECT id, name AS Kullanıcı, initial_points AS Başlangıç_Puanı FROM users ORDER BY name")
    st.dataframe(users, use_container_width=True)

    st.divider()
    st.subheader("Kullanıcı Düzenle / Sil")
    if len(users) > 0:
        selected = st.selectbox("Kullanıcı Seç", users["Kullanıcı"])
        row = users[users["Kullanıcı"] == selected].iloc[0]
        new_name = st.text_input("Yeni Ad", value=row["Kullanıcı"])
        new_points = st.number_input("Yeni Başlangıç Puanı", min_value=0, max_value=10000, value=int(row["Başlangıç_Puanı"]))
        if st.button("Güncelle"):
            execute("UPDATE users SET name=?, initial_points=? WHERE id=?", (new_name.strip(), new_points, int(row["id"])))
            st.success("Kullanıcı güncellendi.")
        if st.button("Seçili Kullanıcıyı Sil"):
            execute("DELETE FROM users WHERE id=?", (int(row["id"]),))
            st.warning("Kullanıcı ve ilişkili tahminleri silindi.")

elif menu == "Maç Yönetimi":
    st.subheader("Maç Ekle")
    c1, c2, c3 = st.columns(3)
    with c1:
        home = st.text_input("Ev Sahibi")
    with c2:
        away = st.text_input("Deplasman")
    with c3:
        mtype = st.selectbox("Maç Türü", ["Normal", "Final"])
    dt = st.text_input("Maç Tarihi/Saati", placeholder="YYYY-MM-DD HH:MM")
    if st.button("Maç Ekle"):
        execute("INSERT INTO matches(home_team,away_team,match_type,match_datetime) VALUES(?,?,?,?)",
                (home.strip(), away.strip(), mtype, dt.strip()))
        st.success("Maç eklendi.")

    matches = fetch_df("""
        SELECT id, home_team AS Ev_Sahibi, away_team AS Deplasman, match_type AS Tür,
        match_datetime AS Tarih, home_score AS Ev_Skor, away_score AS Dep_Skor
        FROM matches ORDER BY id
    """)
    st.dataframe(matches, use_container_width=True)

    st.divider()
    st.subheader("Maç Düzenle / Sil")
    labels = match_label_df()
    if len(labels) > 0:
        selected = st.selectbox("Maç Seç", labels["mac"])
        mid = int(labels[labels["mac"] == selected]["id"].iloc[0])
        r = fetchone("SELECT * FROM matches WHERE id=?", (mid,))
        eh = st.text_input("Ev Sahibi Düzenle", value=r["home_team"])
        ea = st.text_input("Deplasman Düzenle", value=r["away_team"])
        emt = st.selectbox("Tür Düzenle", ["Normal", "Final"], index=0 if r["match_type"] == "Normal" else 1)
        edt = st.text_input("Tarih Düzenle", value=r["match_datetime"] or "")
        if st.button("Maçı Güncelle"):
            execute("UPDATE matches SET home_team=?, away_team=?, match_type=?, match_datetime=? WHERE id=?",
                    (eh.strip(), ea.strip(), emt, edt.strip(), mid))
            st.success("Maç güncellendi.")
        if st.button("Seçili Maçı Sil"):
            execute("DELETE FROM matches WHERE id=?", (mid,))
            st.warning("Maç ve ilişkili tahminleri silindi.")

elif menu == "Tahmin Gir":
    users = fetch_df("SELECT id, name FROM users ORDER BY name")
    matches = match_label_df()
    if len(users) == 0 or len(matches) == 0:
        st.warning("Önce kullanıcı ve maç ekleyin.")
    else:
        user = st.selectbox("Kullanıcı", users["name"])
        match = st.selectbox("Maç", matches["mac"])
        ph = st.number_input("Ev Sahibi Gol", 0, 50, 0)
        pa = st.number_input("Deplasman Gol", 0, 50, 0)

        if st.button("Tahmin Kaydet"):
            uid = int(users[users["name"] == user]["id"].iloc[0])
            mrow = matches[matches["mac"] == match].iloc[0]
            mid = int(mrow["id"])

            if mrow["match_datetime"]:
                try:
                    start = datetime.strptime(mrow["match_datetime"], "%Y-%m-%d %H:%M")
                    if datetime.now() > start:
                        st.error("Maç başlamış. Tahmin girilemez.")
                        st.stop()
                except ValueError:
                    st.warning("Maç tarihi formatı okunamadı; tarih kilidi uygulanmadı.")

            exists = fetchone("SELECT id FROM predictions WHERE user_id=? AND match_id=?", (uid, mid))
            if exists:
                st.error("Bu kullanıcı bu maç için daha önce tahmin girmiştir. Tahmin değiştirilemez.")
            else:
                execute("INSERT INTO predictions(user_id,match_id,pred_home,pred_away) VALUES(?,?,?,?)", (uid, mid, ph, pa))
                st.success("Tahmin kaydedildi.")

elif menu == "Sonuç Gir / Düzelt":
    matches = match_label_df()
    if len(matches) == 0:
        st.warning("Maç yok.")
    else:
        selected = st.selectbox("Maç", matches["mac"])
        mid = int(matches[matches["mac"] == selected]["id"].iloc[0])
        r = fetchone("SELECT home_score, away_score FROM matches WHERE id=?", (mid,))
        hs_default = 0 if r["home_score"] is None else int(r["home_score"])
        as_default = 0 if r["away_score"] is None else int(r["away_score"])
        hs = st.number_input("Ev Sahibi Skoru", 0, 50, hs_default)
        away_s = st.number_input("Deplasman Skoru", 0, 50, as_default)
        if st.button("Sonucu Kaydet / Düzelt"):
            execute("UPDATE matches SET home_score=?, away_score=? WHERE id=?", (hs, away_s, mid))
            st.success("Sonuç kaydedildi.")

elif menu == "Bonus Tahminler":
    users = fetch_df("SELECT id, name FROM users ORDER BY name")
    st.subheader("Kullanıcı Bonus Tahminleri")
    if len(users) > 0:
        user = st.selectbox("Kullanıcı", users["name"])
        uid = int(users[users["name"] == user]["id"].iloc[0])
        old_champ = fetchone("SELECT team FROM champion_predictions WHERE user_id=?", (uid,))
        old_golden = fetchone("SELECT player FROM golden_boot_predictions WHERE user_id=?", (uid,))
        team = st.text_input("Şampiyon Tahmini", value=old_champ["team"] if old_champ else "")
        player = st.text_input("Gol Kralı Tahmini", value=old_golden["player"] if old_golden else "")
        if st.button("Bonus Tahminlerini Kaydet"):
            execute("INSERT OR REPLACE INTO champion_predictions(user_id,team) VALUES(?,?)", (uid, team.strip()))
            execute("INSERT OR REPLACE INTO golden_boot_predictions(user_id,player) VALUES(?,?)", (uid, player.strip()))
            st.success("Bonus tahminleri kaydedildi.")

    st.divider()
    st.subheader("Turnuva Gerçek Sonuçları")
    champion = st.text_input("Gerçek Şampiyon", value=get_setting("champion"))
    golden = st.text_input("Gerçek Gol Kralı", value=get_setting("golden_boot"))
    if st.button("Gerçek Sonuçları Kaydet"):
        set_setting("champion", champion.strip())
        set_setting("golden_boot", golden.strip())
        st.success("Gerçek sonuçlar kaydedildi.")

elif menu == "Tahmin Listesi":
    df = fetch_df("""
        SELECT u.name AS Kullanıcı,
        m.home_team || ' - ' || m.away_team AS Maç,
        m.match_type AS Tür,
        p.pred_home || '-' || p.pred_away AS Tahmin,
        COALESCE(m.home_score || '-' || m.away_score, '') AS Sonuç,
        p.created_at AS Kayıt_Zamanı
        FROM predictions p
        JOIN users u ON u.id=p.user_id
        JOIN matches m ON m.id=p.match_id
        ORDER BY m.id, u.name
    """)
    st.dataframe(df, use_container_width=True)

elif menu == "Excel / Yedek":
    st.subheader("Excel'e Aktar")
    scores = calculate_points()
    puan = pd.DataFrame([[v["name"], v["points"]] for v in scores.values()], columns=["Kullanıcı", "Puan"]).sort_values("Puan", ascending=False)
    tahminler = fetch_df("""
        SELECT u.name AS Kullanıcı, m.home_team || ' - ' || m.away_team AS Maç,
        m.match_type AS Tür, p.pred_home AS Ev_Tahmin, p.pred_away AS Dep_Tahmin,
        m.home_score AS Ev_Skor, m.away_score AS Dep_Skor
        FROM predictions p
        JOIN users u ON u.id=p.user_id
        JOIN matches m ON m.id=p.match_id
    """)
    excel = to_excel_bytes({"Puan Durumu": puan, "Tahminler": tahminler})
    st.download_button("Excel Dosyasını İndir", excel, file_name="engebeliler_tahmin.xlsx")

    st.divider()
    st.subheader("Veritabanı Yedekleme")
    if st.button("Yedek Oluştur"):
        path = create_backup()
        if path:
            st.success(f"Yedek oluşturuldu: {path}")
        else:
            st.error("Veritabanı bulunamadı.")
