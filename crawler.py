import time
import os
import pandas as pd
import subprocess 
from datetime import datetime, timedelta

# [네이버용 라이브러리]
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys

# [유튜브용 라이브러리]
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ======================================================
# [설정 1] 공통 및 파일 설정
# ======================================================
FILE_NAME = "electlink_voc.csv"

# ======================================================
# [설정 2] 네이버 카페 설정
# ======================================================
NAVER_SEARCH_KEYWORDS = ["일렉링크", "워터", "채비", "이브이시스"] 
DEEP_SEARCH_KEYWORDS = ["워터", "채비"] 
EXCLUDE_WORDS = ["팝니다", "삽니다", "매입", "크레딧", "양도", "쿠폰", "판매", "구매"]
TARGET_CAFE_KEYWORDS = ["테슬라", "전기차", "EV", "아이오닉"] 

# ======================================================
# [설정 3] 유튜브 설정
# ======================================================
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY") 
YOUTUBE_SEARCH_TOPICS = ["전기차 충전", "고속도로 충전", "전기차 요금", "급속 충전", "휴게소 충전"]
TARGET_BRANDS = ["SK일렉링크", "일렉링크", "에스에스차저", "SS차저", "워터", "채비", "이브이시스"]

# ======================================================
# [기능 1] 유튜브 크롤링 함수
# ======================================================
def crawl_youtube():
    print(f"\n📺 [YouTube] 크롤링 시작 (조회수 10회↑, 브랜드 강조)...")
    results = []
    
    if not YOUTUBE_API_KEY:
        print("⚠️ [YouTube] API 키가 없습니다. (GitHub Secrets 확인 필요)")
        return []

    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        
        # 24시간 이내
        search_date = datetime.utcnow() - timedelta(days=1) 
        published_after = search_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        query = "|".join(YOUTUBE_SEARCH_TOPICS)

        # 1. 영상 검색
        search_response = youtube.search().list(
            q=query, part="id", order="date",
            publishedAfter=published_after, type="video",
            maxResults=30 
        ).execute()

        video_ids = []
        seen_ids = set()
        for item in search_response.get("items", []):
            vid_id = item['id']['videoId']
            if vid_id not in seen_ids:
                video_ids.append(vid_id)
                seen_ids.add(vid_id)

        if not video_ids:
            print("   💨 최근 24시간 내 검색 결과 없음")
            return []

        # 2. 상세 정보 조회
        video_response = youtube.videos().list(
            id=','.join(video_ids), part='snippet,statistics'
        ).execute()

        items = video_response.get("items", [])
        items.sort(key=lambda x: int(x['statistics'].get('viewCount', 0)), reverse=True)

        print(f"   🔎 1차 검색된 영상 {len(items)}개 분석 중...")

        for item in items:
            vid_id = item['id']
            stats = item['statistics']
            snippet = item['snippet']
            
            view_count = int(stats.get('viewCount', 0))
            if view_count < 10: continue

            raw_title = snippet['title']
            channel = snippet['channelTitle']

            title_display = raw_title
            brand_detected = False
            for brand in TARGET_BRANDS:
                if brand in raw_title:
                    title_display = title_display.replace(brand, f"*{brand}*")
                    brand_detected = True
            
            # [날짜] 한국 시간 기준 적용
            kst_now = datetime.now() + timedelta(hours=9)
            date_str = kst_now.strftime("%Y-%m-%d") + " (New)"

            results.append({
                "작성일": date_str,
                "키워드": "유튜브(영상)",
                "카페명": f"[YouTube] {channel}",
                "제목": f"[영상] {title_display} (조회수 {view_count}회)",
                "링크": f"https://www.youtube.com/watch?v={vid_id}",
                "수집시점": kst_now.strftime("%Y-%m-%d %H:%M")
            })

            # 3. 댓글 수집
            try:
                comment_response = youtube.commentThreads().list(
                    videoId=vid_id, part="snippet", textFormat="plainText", maxResults=5
                ).execute()
                
                for c_item in comment_response.get("items", []):
                    comment = c_item['snippet']['topLevelComment']['snippet']
                    text = comment['textDisplay'].replace('\n', ' ').strip()
                    author = comment['authorDisplayName']

                    found_brand_in_comment = False
                    for brand in TARGET_BRANDS:
                        if brand in text:
                            text = text.replace(brand, f"*{brand}*")
                            found_brand_in_comment = True
                    
                    if found_brand_in_comment:
                        if len(text) > 80: text = text[:80] + "..."
                        results.append({
                            "작성일": date_str,
                            "키워드": "유튜브(댓글)",
                            "카페명": f"[YouTube] {author}",
                            "제목": f"💬 {text}",
                            "링크": f"https://www.youtube.com/watch?v={vid_id}",
                            "수집시점": kst_now.strftime("%Y-%m-%d %H:%M")
                        })
            except HttpError: pass 

    except Exception as e:
        print(f"❌ [YouTube] 에러 발생: {e}")
    
    print(f"   ✅ 유튜브 데이터 {len(results)}건 수집 완료")
    return results

# ======================================================
# [기능 2] 네이버 카페 크롤링 함수
# ======================================================
def crawl_naver():
    print(f"\n🚀 [Naver] 고성능 크롤러 시작")
    data_list = []

    options = webdriver.ChromeOptions()
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_argument("--headless") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    time.sleep(2)

    try:
        for keyword in NAVER_SEARCH_KEYWORDS:
            print(f"   🔍 '{keyword}' 검색 중...")
            base_url = "https://search.naver.com/search.naver?ssc=tab.cafe.all&st=date&nso=so%3Add%2Cp%3Aall&query="
            driver.get(base_url + keyword)
            time.sleep(3) 

            if keyword in DEEP_SEARCH_KEYWORDS:
                print(f"      👉 심층 검색 진행 (15 pg)")
                scroll_times = 15 
            else:
                scroll_times = 3 

            body = driver.find_element(By.TAG_NAME, "body")
            for i in range(scroll_times):
                body.send_keys(Keys.END)
                time.sleep(1.2)
            time.sleep(2)

            articles = driver.find_elements(By.CSS_SELECTOR, "li.bx")
            keyword_count = 0
            
            for article in articles:
                try:
                    cafe_name = ""
                    try: cafe_name = article.find_element(By.CSS_SELECTOR, "a.txt_name").text
                    except: 
                        try: cafe_name = article.find_element(By.CSS_SELECTOR, "a.name").text
                        except: pass

                    if not any(target in cafe_name for target in TARGET_CAFE_KEYWORDS): continue
                    if not any(x in article.text for x in ["분 전", "시간 전", "방금 전"]): continue
                    
                    try:
                        title_ele = article.find_element(By.CSS_SELECTOR, "a.title_link")
                        title = title_ele.text
                        link = title_ele.get_attribute("href")
                    except: continue

                    if any(bad_word in title for bad_word in EXCLUDE_WORDS): continue

                    # [날짜] 한국 시간 기준 적용
                    kst_now = datetime.now() + timedelta(hours=9)
                    date_str = kst_now.strftime("%Y-%m-%d") + " (New)"

                    data_list.append({
                        "작성일": date_str,
                        "키워드": keyword, 
                        "카페명": cafe_name,
                        "제목": title,
                        "링크": link,
                        "수집시점": kst_now.strftime("%Y-%m-%d %H:%M")
                    })
                    keyword_count += 1
                except Exception: continue
            
            print(f"      ✨ 수집: {keyword_count}건")
            time.sleep(1)

    except Exception as e:
        print(f"에러 발생: {e}")
    finally:
        driver.quit()
    
    return data_list

# ======================================================
# [기능 3] 메인 실행 및 저장 (초기화 로직 적용 ✨)
# ======================================================
if __name__ == "__main__":
    # 1. 수집
    naver_data = crawl_naver()
    youtube_data = crawl_youtube()
    
    # 2. 합치기
    all_data = naver_data + youtube_data
    
    # 3. 데이터 처리 및 저장
    df_new = pd.DataFrame(all_data)
    if not df_new.empty:
        df_new = df_new[["작성일", "키워드", "카페명", "제목", "링크", "수집시점"]]
        # 줄바꿈/캐리지리턴 제거 (CSV 깨짐 방지 → 다음 실행의 read_csv 실패 예방)
        for col in df_new.columns:
            df_new[col] = df_new[col].astype(str).str.replace(r"[\r\n]+", " ", regex=True).str.strip()

    if os.path.exists(FILE_NAME):
        try:
            # 기존 데이터 읽기 (깨진 행이 있어도 죽지 않도록 견고하게)
            try:
                df_old = pd.read_csv(FILE_NAME)
            except Exception as read_err:
                print(f"⚠️ 기본 파서 실패 → 견고 모드로 재시도: {read_err}")
                df_old = pd.read_csv(FILE_NAME, engine="python", on_bad_lines="skip")

            # 덮어쓰기 전 백업 (만일을 대비한 안전장치)
            df_old.to_csv(f"{FILE_NAME}.bak", index=False, encoding="utf-8-sig")

            # ✅ [핵심 수정] 기존 데이터에서 '(New)' 꼬리표 떼기! (초기화)
            if '작성일' in df_old.columns:
                df_old['작성일'] = df_old['작성일'].str.replace(" (New)", "", regex=False)
            
            # 구버전 파일 호환성 처리
            if "키워드" not in df_old.columns:
                # 파일 포맷이 다르면 그냥 덮어씀
                if not df_new.empty:
                    df_new.to_csv(FILE_NAME, mode='w', header=True, index=False, encoding="utf-8-sig")
            else:
                # 중복 제거 후 병합
                if not df_new.empty:
                    existing_links = df_old['링크'].tolist()
                    df_final = df_new[~df_new['링크'].isin(existing_links)]
                else:
                    df_final = pd.DataFrame()

                # ✅ [핵심 수정] Old(태그 뗌) + New(태그 있음) 합치기
                combined_df = pd.concat([df_old, df_final], ignore_index=True)
                
                # ✅ [핵심 수정] mode='w'로 전체 덮어쓰기 (그래야 태그 뗀 게 반영됨)
                combined_df.to_csv(FILE_NAME, index=False, encoding="utf-8-sig")
                
                if not df_final.empty:
                    print(f"\n💾 로컬 저장 및 갱신 완료 ({len(df_final)}건 신규 추가)")
                else:
                    print("\n💾 로컬 데이터 갱신 완료 (신규 데이터 없음, 태그만 정리됨)")

                # GitHub 업로드 (파일 내용이 바뀌었으므로 무조건 시도)
                print("\n🐙 GitHub 업로드 시작...")
                subprocess.run(["git", "config", "--global", "user.name", "GitHub Action Bot"], check=False)
                subprocess.run(["git", "config", "--global", "user.email", "actions@github.com"], check=False)
                subprocess.run(["git", "add", FILE_NAME], check=True)
                commit_msg = f"Update data: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                try:
                    subprocess.run(["git", "commit", "-m", commit_msg], check=True)
                    subprocess.run(["git", "push"], check=True)
                    print("✅ GitHub Push 완료!")
                except subprocess.CalledProcessError:
                    print("   -> (GitHub) 변경 사항 없음 (이미 최신)")

        except Exception as e:
            # ⛔ [중요] 여기서 절대 새 데이터만으로 덮어쓰지 않는다.
            #    과거 누적분 전체가 사라지는 초기화 사고의 직접 원인이었음.
            #    에러가 나면 기존 파일은 그대로 두고 종료한다.
            print(f"❌ 파일 처리 에러 (기존 데이터 보존, 덮어쓰기 안 함): {e}")
    else:
        # 파일이 없을 때
        if not df_new.empty:
            df_new.to_csv(FILE_NAME, mode='w', header=True, index=False, encoding="utf-8-sig")
            print(f"\n✅ 신규 파일 생성 완료.")
            subprocess.run(["git", "add", FILE_NAME], check=True)
            subprocess.run(["git", "commit", "-m", "Init data"], check=True)
            subprocess.run(["git", "push"], check=True)
        else:
            print("\n💤 수집된 데이터가 없습니다.")
