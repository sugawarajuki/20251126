import os
import json
import random
from datetime import datetime
import streamlit as st


SUGGESTIONS = {
    "攻撃型": [
        ("VISCARIA", "DHS Hurricane 3 Neo", "Tenergy 05"),
        ("ALC", "Tenergy 05", "Tenergy 64")
    ],
    "守備型": [
        ("Defensive Blade", "XIOM Vega Europe", "Palio CJ8000")
    ],
    "オールラウンド": [
        ("Allround Classic", "Tenergy 64", "Donic Bluefire M2")
    ],
    "その他": [
        ("Custom", "Custom Rubber", "Custom Rubber")
    ]
}

STORAGE = os.path.join(os.path.dirname(__file__), "saved_simple.json")


def load_saved():
    if not os.path.exists(STORAGE):
        return []
    try:
        with open(STORAGE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_combo(obj):
    data = load_saved()
    data.insert(0, obj)
    with open(STORAGE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_all(data):
    with open(STORAGE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def safe_rerun():
    """Streamlit の再実行を安全に試みるヘルパー。
    バージョン差分で `st.experimental_rerun` が無い場合は代替手段を順に試す。
    最終的に失敗したらユーザーに手動リロードを促す。
    """
    try:
        # まず通常の API を試す
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
            return
    except Exception:
        pass

    # 新しい内部 API を使って強制再実行を試みる
    try:
        from streamlit.runtime.scriptrunner import RerunException

        raise RerunException()
    except Exception:
        pass

    # 最終フォールバック: サーバ API を使う（存在すれば）
    try:
        from streamlit.web.server.server import Server

        srv = Server.get_current()
        if srv is not None:
            srv.request_rerun()
            return
    except Exception:
        pass

    # ここまで来たら手動でのリロードを促す
    try:
        st.warning("ページを手動でリロードしてください（自動再実行が利用できません）。")
    except Exception:
        pass


def main():
    st.set_page_config(page_title="卓球組み合わせ (簡潔)")
    st.title("卓球用具の組み合わせ提案")

    play = st.selectbox("戦型を選んでください", list(SUGGESTIONS.keys()))

    # 提案ボタン: 結果を session_state に保存しておく
    if st.button("提案する"):
        opt = random.choice(SUGGESTIONS.get(play, SUGGESTIONS["その他"]))
        racket, front, back = opt
        st.session_state['last_suggestion'] = {
            "playstyle": play,
            "racket": racket,
            "rubber_front": front,
            "rubber_back": back,
        }

    # 最後の提案があれば表示（保存ボタンは常に有効）
    last = st.session_state.get('last_suggestion')
    if last:
        st.success(f"提案: {last['racket']} + {last['rubber_front']} / {last['rubber_back']}")
        st.write("---")
        st.write("**ラケット:**", last['racket'])
        st.write("**表ラバー:**", last['rubber_front'])
        st.write("**裏ラバー:**", last['rubber_back'])

        if st.button("保存する"):
            obj = {
                "playstyle": last['playstyle'],
                "racket": last['racket'],
                "rubber_front": last['rubber_front'],
                "rubber_back": last['rubber_back'],
                "saved_at": datetime.now().isoformat()
            }
            try:
                save_combo(obj)
                st.info("保存しました")
                # 保存したら最後の提案をクリア
                st.session_state.pop('last_suggestion', None)
                safe_rerun()
            except Exception as e:
                st.error(f"保存失敗: {e}")

    st.write("\n")
    st.subheader("保存済み（最新5件）")
    saved = load_saved()
    if not saved:
        st.info("まだ保存がありません。")
    else:
        for idx, item in enumerate(saved[:5]):
            label = f"{item['playstyle']} — {item['racket']} + {item['rubber_front']}/{item['rubber_back']} ({item.get('saved_at','')})"
            with st.expander(label):
                st.write("**戦型:**", item['playstyle'])
                st.write("**ラケット:**", item['racket'])
                st.write("**表ラバー:**", item['rubber_front'])
                st.write("**裏ラバー:**", item['rubber_back'])
                st.write("**保存日時:**", item.get('saved_at',''))

                c1, c2 = st.columns([1,1])
                if c1.button("削除", key=f"del_{idx}"):
                    # 削除
                    new = load_saved()
                    # global index: idx corresponds to the same position in the saved list because we show latest first
                    if idx < len(new):
                        new.pop(idx)
                        save_all(new)
                        safe_rerun()
                if c2.button("複製", key=f"dup_{idx}"):
                    new = load_saved()
                    if idx < len(new):
                        copy = dict(new[idx])
                        copy['saved_at'] = datetime.now().isoformat()
                        new.insert(0, copy)
                        save_all(new)
                        safe_rerun()

        st.download_button("保存データをJSONでダウンロード", data=json.dumps(saved, ensure_ascii=False, indent=2).encode('utf-8'), file_name='saved_simple.json', mime='application/json')


if __name__ == '__main__':
    main()
