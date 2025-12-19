import pandas as pd
import requests
import json
import os
from datetime import datetime, timedelta

# ======================================================
# [보안 설정] GitHub Secrets에서 'SLACK_WEBHOOK_URLS' 가져오기
# ======================================================
webhook_env = os.environ.get("SLACK_WEBHOOK_URLS", "")

if webhook_env:
    raw_list = webhook_env.split(',')
    SLACK_WEBHOOK_LIST = []
    for url in raw_list:
        clean_url = url.strip().replace('"', '').replace("'", "")
        if clean_url:
            SLACK_WEBHOOK_LIST.append(clean_url)
else:
    SLACK_WEBHOOK_LIST = []

CSV_FILE = "electlink_voc.csv"
DASHBOARD_URL = "https://sk-electlink-monitor-aj2cncmpcwo8rm3muzrylw.streamlit.app/"
# ======================================================

def send_daily_report():
    # 1. 한국 시간 설정
    kst_now = datetime.now() + timedelta(hours=9)
    today_str = kst_now.strftime("%Y-%m-%d")    
    print(f"📅 리포트 발송 기준 날짜: {today_str}")
    
    if not SLACK_WEBHOOK_LIST:
        print("❌ 오류: 슬랙 웹훅 URL을 찾을 수 없습니다.")
        return

    # 2. CSV 파일 읽기
    try:
        df = pd.read_csv(CSV_FILE)
    except FileNotFoundError:
        print("❌ 데이터 파일이 없습니다.")
        return

    # 3. 신규 데이터 필터링 ((New) 태그)
    today_df = df[df['작성일'].str.contains(r"\(New\)", regex=True, na=False)]
    
    print(f"🔍 전송할 신규 데이터: 총 {len(today_df)}건 감지됨")

    # ------------------------------------------------------
    # [데이터 분류]
    # ------------------------------------------------------
    sk_keywords = ["SK일렉링크", "일렉링크"]
    comp_keywords = ["워터", "채비", "이브이시스"]

    # (1) SK일렉링크
    sk_df = today_df[today_df['키워드'].isin(sk_keywords)]
    sk_count = len(sk_df)

    # (2) 경쟁사 카운트 계산 (요약 줄 표시용) ✨ 복구됨
    comp_counts = []
    for comp in comp_keywords:
        count = len(today_df[today_df['키워드'] == comp])
        comp_counts.append(f"{comp} {count}건")
    comp_msg_str = ", ".join(comp_counts)

    # (3) 유튜브
    youtube_df = today_df[today_df['키워드'].str.contains("유튜브", na=False)]

    # ------------------------------------------------------
    # [메시지 작성]
    # ------------------------------------------------------
    message = f"📢 *[{today_str}] SK일렉링크 일일 모니터링*\n\n"
    
    # [섹션 1] 요약 및 대시보드
    message += f"오늘자 SK일렉링크 커뮤니티 언급된 수는 *{sk_count}건*입니다\n"
    message += f"({comp_msg_str})\n\n" # ✨ 요청하신 요약 줄 (경쟁사 현황) 유지!
    
    message += f"📊 *전체 현황 대시보드 보러가기*:\n{DASHBOARD_URL}\n\n"
    
    # [섹션 2] SK일렉링크 커뮤니티 리스트
    message += "📝 *오늘자 당사로 언급된 키워드 (Community)*\n"
    if sk_count > 0:
        for index, row in sk_df.iterrows():
            title = row['제목']
            link = row['링크']
            message += f"• <{link}|{title}>\n"
    else:
        message += "• (특이 사항 없음)\n"

    # [섹션 3] 경쟁사 언급 현황 (상세 리스트)
    comp_exists = False
    comp_section_msg = ""
    
    for comp in comp_keywords:
        target_comp_df = today_df[today_df['키워드'] == comp]
        if not target_comp_df.empty:
            comp_exists = True
            comp_section_msg += f"\n🔹 *[{comp}]*\n"
            for index, row in target_comp_df.iterrows():
                title = row['제목']
                link = row['링크']
                comp_section_msg += f"• <{link}|{title}>\n"
    
    if comp_exists:
        message += "\n⚔️ *오늘자 경쟁사 언급 현황*\n"
        message += comp_section_msg
    
    # [섹션 4] 유튜브 리스트
    message += "\n📺 *[유튜브] 모니터링 이슈 (Video/Comment)*\n"
    if not youtube_df.empty:
        for index, row in youtube_df.iterrows():
            title = row['제목'] 
            link = row['링크']
            message += f"• <{link}|{title}>\n"
    else:
        message += "• (특이 사항 없음)\n"

    # ------------------------------------------------------
    # [전송]
    # ------------------------------------------------------
    payload = {
        "text": message,
        "unfurl_links": False, 
        "unfurl_media": False  # ✨ 유튜브 미리보기 끄기
    }

    print(f"🚀 총 {len(SLACK_WEBHOOK_LIST)}곳으로 전송을 시작합니다...")
    
    for i, webhook_url in enumerate(SLACK_WEBHOOK_LIST):
        if not webhook_url.startswith("http"): continue

        try:
            response = requests.post(webhook_url, json=payload)
            if response.status_code == 200:
                print(f"   ✅ [{i+1}] 전송 성공")
            else:
                print(f"   ❌ [{i+1}] 전송 실패 ({response.status_code})")
        except Exception as e:
            print(f"   ❌ [{i+1}] 에러 발생: {e}")

if __name__ == "__main__":
    send_daily_report()
