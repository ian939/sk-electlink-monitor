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
DEEP_SEARCH_KEYWORDS = ["워터", "채비"] # 심층 검색 키워드
EXCLUDE_WORDS = ["팝니다", "삽니다", "매입", "크레딧", "양도", "쿠폰", "판매", "구매"]
TARGET_CAFE_KEYWORDS = ["테슬라", "전기차", "EV", "아이오닉"] 

# ======================================================
# [설정 3] 유튜브 설정 (테스트 완료된 로직 적용)
# ======================================================
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY") 
# 넓게 검색할 주제
YOUTUBE_SEARCH_TOPICS = ["전기차 충전", "고속도로 충전", "전기차 요금", "급속 충전", "휴게소 충전"]
# 강조할 브랜드 (볼드 처리)
TARGET_BRANDS = ["SK일렉링크", "일렉링크", "에스에스차저", "SS차저", "워터", "채비", "이브이시스"]

# ======================================================
# [기능 1] 유튜브 크롤링 함수 (조회수 10회 이상, 브랜드 필터)
# ======================================================
def crawl_youtube():
    print(f"\n📺 [YouTube] 크롤링 시작 (조회수 10회↑, 브랜드 강조)...")
    results = []
    
    if not YOUTUBE_API_KEY:
        print("⚠️ [YouTube] API 키가 없습니다. (GitHub Secrets 확인 필요)")
        return []

    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        
        # 24시간 이내 영상만
        search_date = datetime.utcnow() - timedelta(days=1) 
        published_after = search_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        query = "|".join(YOUTUBE_SEARCH_TOPICS)

        # 1. 검색 (영상 ID 수집)
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

        # 2. 상세 정보 조회 (조회수 확인용)
        video_response = youtube.videos().list(
            id=','.join(video_ids), part='snippet,statistics'
        ).execute()

        items = video_response.get("items", [])
        # 조회수 내림차순 정렬
        items.sort(key=lambda x: int(x['statistics'].get('viewCount', 0)), reverse=True)

        print(f"   🔎 1차 검색된 영상 {len(items)}개 분석 중...")

        for item in items:
            vid_id = item['id']
            stats = item['statistics']
            snippet = item['snippet']
            
            # [필터] 조회수 10회 미만 제외
            view_count = int(stats.get('viewCount', 0))
            if view_count < 10:
                continue

            raw_title = snippet['title']
            channel = snippet['channelTitle']

            # [제목 처리] 브랜드 *볼드*
            title_display = raw_title
            brand_detected = False
            for brand in TARGET_BRANDS:
                if brand in raw_title:
                    title_display = title_display.replace(brand, f"*{brand}*")
                    brand_detected = True
            
            # [영상 저장] 브랜드 언급이 있거나, 조회수가 높은 관련 영상
            # (여기서는 브랜드 언급 여부와 상관없이 주제가 맞고 조회수 통과하면 저장하되, 
            # 브랜드가 있으면 제목에 볼드처리됨)
            results.append({
                "작성일": datetime.now().strftime("%Y-%m-%d") + " (New)",
                "키워드": "유튜브(영상)",
                "카페명": f"[YouTube] {channel}",
                "제목": f"[영상] {title_display} (조회수 {view_count}회)",
                "링크": f"https://www.youtube.com/watch?v={vid_id}",
                "수집시점": datetime.now().strftime("%Y-%m-%d %H:%M")
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

                    # 댓글 내용 브랜드 *볼드* 처리
                    found_brand_in_comment = False
                    for brand in TARGET_BRANDS:
                        if brand in text:
                            text = text.replace(brand, f"*{brand}*")
                            found_brand_in_comment = True
                    
                    # 브랜드가 언급된 댓글만 저장 (댓글은 필터링 강화)
                    if found_brand_in_comment:
                        if len(text) > 80: text = text[:80] + "..."
                        results.append({
                            "작성일": datetime.now().strftime("%Y-%m-%d") + " (New)",
                            "키워드": "유튜브(댓글)",
                            "카페명": f"[YouTube] {author}",
                            "제목": f"💬 {text}",
                            "링크": f"https://www.youtube.com/watch?v={vid_id}",
                            "수집시점": datetime.now().strftime("%Y-%m-%d %H:%M")
                        })
            except HttpError:
                pass 

    except Exception as e:
        print(f"❌ [YouTube] 에러 발생: {e}")
    
    print(f"   ✅ 유튜브 데이터 {len(results)}건 수집 완료")
    return results

# ======================================================
# [기능 2] 네이버 카페 크롤링 함수 (기존 로직 유지)
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

            # 심층 검색 로직
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
                    # 카페명
                    cafe_name = ""
                    try: cafe_name = article.find_element(By.CSS_SELECTOR, "a.txt_name").text
                    except: 
                        try: cafe_name = article.find_element(By.CSS_SELECTOR, "a.name").text
                        except: pass

                    # 필터
                    if not any(target in cafe_name for target in TARGET_CAFE_KEYWORDS): continue
                    if not any(x in article.text for x in ["분 전", "시간 전", "방금 전"]): continue
                    
                    # 제목/링크
                    try:
                        title_ele = article.find_element(By.CSS_SELECTOR, "a.title_link")
                        title = title_ele.text
                        link = title_ele.get_attribute("href")
                    except: continue

                    if any(bad_word in title for bad_word in EXCLUDE_WORDS): continue

                    data_list.append({
                        "작성일": datetime.now().strftime("%Y-%m-%d") + " (New)",
                        "키워드": keyword, 
                        "카페명": cafe_name,
                        "제목": title,
                        "링크": link,
                        "수집시점": datetime.now().strftime("%Y-%m-%d %H:%M")
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
# [기능 3] 메인 실행 및 저장/업로드
# ======================================================
if __name__ == "__main__":
    # 1. 수집
    naver_data = crawl_naver()
    youtube_data = crawl_youtube()
    
    # 2. 합치기
    all_data = naver_data + youtube_data
    
    # 3. 데이터 처리 및 저장
    if all_data:
        df_new = pd.DataFrame(all_data)
        # 컬럼 순서 강제 고정
        df_new = df_new[["작성일", "키워드", "카페명", "제목", "링크", "수집시점"]]

        if os.path.exists(FILE_NAME):
            try:
                df_old = pd.read_csv(FILE_NAME)
                # 구버전 파일 호환성 체크
                if "키워드" not in df_old.columns:
                     df_new.to_csv(FILE_NAME, mode='w', header=True, index=False, encoding="utf-8-sig")
                else:
                    existing_links = df_old['링크'].tolist()
                    df_final = df_new[~df_new['링크'].isin(existing_links)]
                    
                    if not df_final.empty:
                        df_final.to_csv(FILE_NAME, mode='a', header=False, index=False, encoding="utf-8-sig")
                        print(f"\n💾 로컬 저장 완료 ({len(df_final)}건 추가)")
                        
                        # GitHub 업로드 (데이터가 추가되었을 때만 수행)
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
                             print("   -> 커밋할 변경사항이 없습니다.")
                    else:
                        print("\n👌 새로운 글이 없습니다 (전체 중복).")
            except Exception as e:
                print(f"파일 처리 에러: {e}")
                # 에러 시 덮어쓰기 안전장치
                df_new.to_csv(FILE_NAME, mode='w', header=True, index=False, encoding="utf-8-sig")
        else:
            # 파일이 아예 없을 때
            df_new.to_csv(FILE_NAME, mode='w', header=True, index=False, encoding="utf-8-sig")
            print(f"\n✅ 신규 파일 생성 완료.")
            subprocess.run(["git", "add", FILE_NAME], check=True)
            subprocess.run(["git", "commit", "-m", "Init data"], check=True)
            subprocess.run(["git", "push"], check=True)
    else:
        print("\n💤 수집된 데이터가 없습니다.")
