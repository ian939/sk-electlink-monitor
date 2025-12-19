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
    # 1. 한국 시간 설정 (서버시간 UTC+9)
    # (필터링에는 안 쓰지만, 리포트 제목의 날짜 표시용으로 필요함)
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

    # ======================================================
    # ✨ [핵심 수정] 날짜 대신 '(New)' 태그로 최신 데이터 필터링
    # ======================================================
    # 크롤러가 방금 수집한 데이터에만 '(New)'를 붙여뒀으므로, 이것만 가져오면 됩니다.
    # regex=True를 써서 괄호()를 문자로 인식하게 처리했습니다.
    today_df = df[df['작성일'].str.contains(r"\(New\)", regex=True, na=False)]
    
    print(f"🔍 전송할 신규 데이터: 총 {len(today_df)}건 감지됨")

    # ------------------------------------------------------
    # [데이터 분류] 네이버 카페 vs 유튜브
    # ------------------------------------------------------
    sk_keywords = ["SK일렉링크", "일렉링크"]
    comp_keywords = ["워터", "채비", "이브이시스"]

    # (1) SK일렉링크 (네이버 카페)
    sk_df = today_df[today_df['키워드'].isin(sk_keywords)]
    sk_count = len(sk_df)

    # (2) 경쟁사 현황 (네이버 카페)
    comp_counts = []
    for comp in comp_keywords:
        count = len(today_df[today_df['키워드'] == comp])
        comp_counts.append(f"{comp} {count}건")
    comp_msg_str = ", ".join(comp_counts)

    # (3) 유튜브 데이터 (영상/댓글 포함)
    # 키워드 컬럼에 '유튜브'라는 단어가 포함된 모든 행
    youtube_df = today_df[today_df['키워드'].str.contains("유튜브", na=False)]
    
    # ------------------------------------------------------
    # [메시지 작성]
    # ------------------------------------------------------
    message = f"📢 *[{today_str}] SK일렉링크 일일 모니터링*\n\n"
    
    # [섹션 1] 요약 통계
    message += f"오늘자 SK일렉링크 커뮤니티 언급된 수는 *{sk_count}건*입니다\n"
    message += f"(경쟁사 현황: {comp_msg_str})\n\n"
    
    message += f"📊 *전체 현황 대시보드 보러가기*:\n{DASHBOARD_URL}\n\n"
    
    # [섹션 2] 커뮤니티(네이버) 리스트
    message += "📝 *오늘자 당사로 언급된 키워드 (Community)*\n"
    if sk_count > 0:
        for index, row in sk_df.iterrows():
            title = row['제목']
            link = row['링크']
            message += f"• <{link}|{title}>\n"
    else:
        message += "• (특이 사항 없음)\n"

    # [섹션 3] 유튜브 리스트
    message += "\n📺 *[유튜브] 모니터링 이슈 (Video/Comment)*\n"
    if not youtube_df.empty:
        for index, row in youtube_df.iterrows():
            title = row['제목'] # 이미 크롤러에서 볼드 처리됨 (*브랜드*)
            link = row['링크']
            message += f"• <{link}|{title}>\n"
    else:
        message += "• (특이 사항 없음)\n"

    # ------------------------------------------------------
    # [전송]
    # ------------------------------------------------------
    payload = {
        "text": message,
        "unfurl_links": False # 링크 미리보기 끄기 (깔끔하게 보려고)
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
