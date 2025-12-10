import os
import sqlite3
from datetime import datetime
import streamlit as st

# ページ設定
st.title("卓球用具の組み合わせ")

# データベースパス
db_path = os.path.join(os.path.dirname(__file__), "combinations.db")

# データベース初期化
def init_db():
    conn = sqlite3.connect(db_path)
    # 基本テーブル定義（表ラバー/裏ラバー対応）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS combinations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            playstyle TEXT NOT NULL,
            racket TEXT NOT NULL,
            rubber_front TEXT,
            rubber_back TEXT,
            notes TEXT,
            created_at TIMESTAMP NOT NULL
        )
    """)
    conn.commit()

    # 既存テーブルに旧カラム 'rubber' がある場合は安全にマイグレーション
    cur = conn.cursor()
    cur.execute("PRAGMA table_info('combinations')")
    cols = [row[1] for row in cur.fetchall()]
    # 'rubber' カラムが存在し、新しい 'rubber_front' カラムが無ければマイグレーションを行う
    if 'rubber' in cols and 'rubber_front' not in cols:
        try:
            # 新しいテーブルを作成してデータをコピーし、旧テーブルを置き換える方法で NOT NULL 制約を取り除く
            conn.executescript("""
            BEGIN;
            CREATE TABLE IF NOT EXISTS combinations_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                playstyle TEXT NOT NULL,
                racket TEXT NOT NULL,
                rubber_front TEXT,
                rubber_back TEXT,
                notes TEXT,
                created_at TIMESTAMP NOT NULL
            );
            INSERT INTO combinations_new (id, playstyle, racket, rubber_front, rubber_back, notes, created_at)
                SELECT id, playstyle, racket, rubber AS rubber_front, '' AS rubber_back, notes, created_at FROM combinations;
            DROP TABLE combinations;
            ALTER TABLE combinations_new RENAME TO combinations;
            COMMIT;
            """)
        except Exception:
            # マイグレーション失敗しても処理継続（手動での対応を想定）
            conn.rollback()

    cur.close()
    conn.close()

init_db()

# --- UI 入力 ---
st.subheader("新しい組み合わせを保存")
playstyle = st.selectbox("戦型を選択してください", [
    "攻撃型",
    "守備型",
    "オールラウンド",
    "カウンター",
    "両ハンド",
    "その他"
])

# テキスト入力は session_state を使う（提案を適用しやすくするため）
if 'racket' not in st.session_state:
    st.session_state['racket'] = ''
if 'rubber_front' not in st.session_state:
    st.session_state['rubber_front'] = ''
if 'rubber_back' not in st.session_state:
    st.session_state['rubber_back'] = ''

# 戦型ごとのおすすめ（簡易例）
SUGGESTIONS = {
    "攻撃型": [
        ("VISCARIA", "DHS Hurricane 3 Neo", "Tenergy 05"),
        ("ALC", "Tenergy 05", "Tenergy 64")
    ],
    "守備型": [
        ("Jpenhold Defensive", "XIOM Vega Europe", "Palio CJ8000"),
        ("Defensive Blade", "Tibhar Evolution MX-P", "XIOM Vega Europe")
    ],
    "オールラウンド": [
        ("Allround Classic", "Donic Bluefire M2", "Tenergy 64"),
        ("Primorac", "Tenergy 64", "Donic Bluefire M2")
    ],
    "カウンター": [
        ("Counter Blade", "Yasaka Rakza 7", "Rakza Z"),
    ],
    "両ハンド": [
        ("Penhold Two-sided", "Palio CJ8000", "Palio CJ8000"),
    ],
    "その他": [
        ("Custom", "Custom Rubber", "Custom Rubber")
    ]
}

# おすすめ表示
st.markdown("**おすすめの組み合わせ（戦型に基づく）**")
options = SUGGESTIONS.get(playstyle, [])
if options:
    for i, tup in enumerate(options):
        # tup may be (racket, front, back) or shorter
        rkt = tup[0] if len(tup) >= 1 else ''
        front = tup[1] if len(tup) >= 2 else ''
        back = tup[2] if len(tup) >= 3 else ''
        c1, c2 = st.columns([3,1])
        with c1:
            st.write(f"{rkt} + {front} / {back}")
        with c2:
            if st.button("適用", key=f"apply_{playstyle}_{i}"):
                st.session_state['racket'] = rkt
                st.session_state['rubber_front'] = front
                st.session_state['rubber_back'] = back
else:
    st.write("提案がありません。ラケットとラバーを手動で入力してください。")

# 入力欄（session_state と同期）
racket = st.text_input("ラケット名", key='racket')
rubber_front = st.text_input("表ラバー名", key='rubber_front')
rubber_back = st.text_input("裏ラバー名（任意）", key='rubber_back')
notes = st.text_area("備考（任意）", height=120)

if st.button("保存"):
    # session_state から取得（表／裏）
    rkt_val = st.session_state.get('racket', '').strip()
    rfront = st.session_state.get('rubber_front', '').strip()
    rback = st.session_state.get('rubber_back', '').strip()
    notes_val = (notes or '').strip()

    if not rkt_val or not rfront:
        st.warning("ラケット名と表ラバー名を入力してください")
    else:
        try:
            # with ブロックで確実に接続を閉じる
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    "INSERT INTO combinations (playstyle, racket, rubber_front, rubber_back, notes, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (playstyle, rkt_val, rfront, rback, notes_val, datetime.now())
                )
                conn.commit()

            st.success(f"保存しました：{playstyle} | {rkt_val} + {rfront}/{rback}")

            # 入力欄をクリアして再入力をしやすくする
            st.session_state['racket'] = ''
            st.session_state['rubber_front'] = ''
            st.session_state['rubber_back'] = ''
        except Exception as e:
            st.error(f"保存中にエラーが発生しました: {e}")

# 保存済み組み合わせ一覧
st.subheader("保存済みの組み合わせ")
conn = sqlite3.connect(db_path)
rows = conn.execute(
    "SELECT id, playstyle, racket, rubber_front, rubber_back, notes, created_at FROM combinations ORDER BY created_at DESC"
).fetchall()
conn.close()

def describe_combo(racket_name: str, front: str, back: str) -> str:
    """簡易ヒューリスティックで組み合わせの特徴を推定して返す。"""
    score = {"speed": 0, "spin": 0, "control": 0}

    def eval_rubber(name: str):
        name = (name or '').lower()
        s = {"speed": 0, "spin": 0, "control": 0}
        if not name:
            return s
        if 'tenergy' in name or 'tenergy' in name:
            s['speed'] += 2
            s['spin'] += 3
            s['control'] += 0
        if 'hurricane' in name or 'dhs' in name:
            s['spin'] += 3
            s['control'] += 1
            s['speed'] -= 1
        if 'vega' in name or 'donic' in name:
            s['speed'] += 1
            s['control'] += 1
        if 'rakza' in name or 'yasaka' in name:
            s['speed'] += 1
            s['spin'] += 1
        if 'palio' in name or 'cj8000' in name:
            s['control'] += 2
        if 'bluefire' in name:
            s['speed'] += 2
            s['control'] += 0
        return s

    for nm in (front, back):
        r = eval_rubber(nm)
        score['speed'] += r['speed']
        score['spin'] += r['spin']
        score['control'] += r['control']

    # ラケット影響（簡易）
    rname = (racket_name or '').lower()
    if 'alc' in rname or 'viscaria' in rname:
        score['speed'] += 2
        score['control'] += 1
    if 'allround' in rname or 'primorac' in rname:
        score['control'] += 2
    if 'defensive' in rname:
        score['control'] += 3
        score['speed'] -= 1

    # 正規化的な説明文生成
    parts = []
    if score['speed'] >= 3:
        parts.append('速い球速')
    elif score['speed'] >= 1:
        parts.append('中〜速')
    else:
        parts.append('落ち着いた球速')

    if score['spin'] >= 4:
        parts.append('高い回転性能')
    elif score['spin'] >= 2:
        parts.append('回転が出やすい')
    else:
        parts.append('控えめなスピン')

    if score['control'] >= 3:
        parts.append('高いコントロール性')
    elif score['control'] >= 1:
        parts.append('扱いやすさは標準的')
    else:
        parts.append('やや扱いが難しい')

    return '、'.join(parts)

for cid, play, rkt, rfront, rback, nts, created_at in rows:
    label = f"{play} — {rkt} + {rfront}/{rback} ({created_at})"
    with st.expander(label):
        st.write("**戦型:**", play)
        st.write("**ラケット:**", rkt)
        st.write("**表ラバー:**", rfront)
        st.write("**裏ラバー:**", rback if rback else '(なし)')
        if nts:
            st.write("**備考:**", nts)
        st.write("**保存日時:**", created_at)
        # 特徴表示
        desc = describe_combo(rkt, rfront, rback)
        st.info(f"推定特徴: {desc}")
