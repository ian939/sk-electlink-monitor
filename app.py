import streamlit as st
import pandas as pd

# 1. 페이지 설정
st.set_page_config(page_title="EV 충전소 여론 모니터링", layout="wide")

st.title("🔋 EV 충전소 여론 모니터링 Dashboard")
st.caption("전기차 동호회 및 유튜브의 실시간 반응을 분석합니다. (SK일렉링크 vs 경쟁사)")
st.markdown("---")

# 2. 데이터 불러오기
try:
    df = pd.read_csv("electlink_voc.csv")
    df = df.sort_values(by="작성일", ascending=False)
    
    if "키워드" not in df.columns:
        st.error("⚠️ CSV 파일 양식이 오래되었습니다. 기존 CSV를 삭제 후 crawler.py를 다시 실행해주세요.")
        st.stop()
except FileNotFoundError:
    st.error("데이터 파일이 없습니다. 크롤러를 먼저 실행해주세요.")
    st.stop()

# ---------------------------------------------------------
# [데이터 분리] SK vs 경쟁사 vs 유튜브
# ---------------------------------------------------------
# 1. SK (네이버 카페)
sk_keywords = ["SK일렉링크", "일렉링크"]
df_sk = df[df['키워드'].isin(sk_keywords)].copy()

# 2. 경쟁사 (네이버 카페)
competitor_keywords = ["워터", "채비", "이브이시스"]
df_comp = df[df['키워드'].isin(competitor_keywords)].copy()

# 3. 유튜브 (키워드에 '유튜브'가 포함된 모든 행)
df_youtube = df[df['키워드'].str.contains("유튜브", na=False)].copy()

# 화면에 보여줄 컬럼 설정
display_columns = ["작성일", "키워드", "카페명", "제목", "링크"]

# =========================================================
# [섹션 1] 🔵 SK일렉링크 (메인)
# =========================================================
st.subheader("🔵 SK일렉링크 최신 여론 (Naver Cafe)")

col1, col2, col3 = st.columns(3)
issue_keywords = ["고장", "오류", "실패", "안됨", "불편", "느림", "점검", "대기", "화남", "비싸"]
sk_issue_df = df_sk[df_sk['제목'].str.contains('|'.join(issue_keywords), na=False)]

with col1:
    st.metric("SK 수집 글", f"{len(df_sk)} 건")
with col2:
    st.metric("🚨 이슈 감지", f"{len(sk_issue_df)} 건", delta_color="inverse")
with col3:
    last_time = df['수집시점'].iloc[0] if '수집시점' in df.columns and not df.empty else "-"
    st.write(f"최근 업데이트: {last_time}")

st.dataframe(
    df_sk[display_columns],
    column_config={
        "링크": st.column_config.LinkColumn("바로가기", display_text="Link"),
        "제목": st.column_config.TextColumn("제목", width="large"),
    },
    hide_index=True,
    use_container_width=True,
    height=300 
)

st.markdown("---")

# =========================================================
# [섹션 2] ⚔️ 경쟁사 동향 (워터/채비/EVSIS)
# =========================================================
st.subheader("⚔️ 경쟁사 최신 동향 (Naver Cafe)")

if not df_comp.empty:
    tab1, tab2, tab3, tab4 = st.tabs(["전체 보기", "워터(WATER)", "채비(CHAEVI)", "이브이시스(EVSIS)"])
    
    with tab1:
        st.caption(f"총 {len(df_comp)}건의 경쟁사 글이 있습니다.")
        st.dataframe(
            df_comp[display_columns],
            column_config={"링크": st.column_config.LinkColumn("바로가기", display_text="Link")},
            hide_index=True, use_container_width=True, height=400
        )

    def show_competitor(brand_list):
        target_df = df_comp[df_comp['키워드'].isin(brand_list)]
        if target_df.empty:
            st.info("수집된 글이 없습니다.")
        else:
            st.dataframe(
                target_df[display_columns],
                column_config={"링크": st.column_config.LinkColumn("바로가기", display_text="Link")},
                hide_index=True, use_container_width=True, height=400
            )

    with tab2: show_competitor(["워터"])
    with tab3: show_competitor(["채비"])
    with tab4: show_competitor(["이브이시스"])

else:
    st.info("아직 수집된 경쟁사 데이터가 없습니다.")

st.markdown("---")

# =========================================================
# [섹션 3] 📺 유튜브 여론 (YouTube) - ✨ 업데이트됨
# =========================================================
st.subheader("📺 유튜브 여론 모니터링 (YouTube)")

if not df_youtube.empty:
    # 데이터 분리 (영상 vs 댓글)
    df_yt_videos = df_youtube[df_youtube['키워드'] == "유튜브(영상)"]
    df_yt_comments = df_youtube[df_youtube['키워드'] == "유튜브(댓글)"]
    
    # 상단 통계
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("총 유튜브 데이터", f"{len(df_youtube)} 건")
    with c2: st.metric("수집된 영상", f"{len(df_yt_videos)} 개")
    with c3: st.metric("브랜드 언급 댓글", f"{len(df_yt_comments)} 개")
    
    # 탭 분리: 영상 목록 / 댓글 반응
    yt_tab1, yt_tab2 = st.tabs(["🎥 수집된 영상 목록", "💬 주요 댓글 반응 (Key Comments)"])
    
    # [탭 1] 영상 목록 (기존처럼 테이블로)
    with yt_tab1:
        if not df_yt_videos.empty:
            st.dataframe(
                df_yt_videos[display_columns],
                column_config={
                    "링크": st.column_config.LinkColumn("바로가기", display_text="Watch"),
                    "제목": st.column_config.TextColumn("제목 (내용)", width="large"),
                    "카페명": st.column_config.TextColumn("채널명"),
                    "키워드": st.column_config.TextColumn("구분"),
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("최근 24시간 내 수집된 영상이 없습니다.")

    # [탭 2] 댓글 반응 (✨ 볼드 처리를 위해 마크다운 사용)
    with yt_tab2:
        if not df_yt_comments.empty:
            st.info("💡 댓글 내 '일렉링크', '채비', '워터', '이브이시스' 등 브랜드 키워드가 포함된 내용만 표시됩니다.")
            
            for index, row in df_yt_comments.iterrows():
                # 스타일링된 카드 형태로 출력
                with st.chat_message("user"):
                    st.write(f"**{row['카페명']}** (작성일: {row['작성일']})")
                    # 여기서 row['제목']에는 이미 '*브랜드*' 처리가 되어 있음 -> 마크다운이 볼드로 변환해줌
                    # 제목 앞의 '💬 ' 아이콘 제거 후 출력
                    clean_content = row['제목'].replace("💬 ", "")
                    st.markdown(f"{clean_content}")
                    st.caption(f"[원본 영상 보러가기]({row['링크']})")
        else:
            st.write("🤐 아직 브랜드가 언급된 주요 댓글이 없습니다.")

else:
    st.info("📺 최근 24시간 내 수집된 유튜브 데이터가 없습니다.")

# ---------------------------------------------------------
# 새로고침 버튼
# ---------------------------------------------------------
st.markdown("<br>", unsafe_allow_html=True)
if st.button('데이터 새로고침 🔄'):
    st.rerun()
