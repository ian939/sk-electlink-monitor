# VoC 수집 필터: 판매글 배제, 브랜드별 관련성 판정, 네이버 링크 정규화 공용 모듈 (crawler.py / clean_history.py에서 사용)
import re

# ======================================================
# [1] VoC가 아닌 글 배제 (판매/거래/주식)
# ======================================================
# "42,100 -> 32,000", "48500 -->37000", "45100 ~> 3만" 같은 가격 화살표는 포인트 거래글의 시그니처
# ('~' 단독은 "30~80% 충전" 같은 정상 범위 표기에 오탐되어 넣지 않음. '>'로 끝나는 변형만 인정)
PRICE_ARROW_RE = re.compile(r"\d[\d,.]*\s*(?:원|포인트|만|p)?\s*(?:[-=~]{1,3}>|→|--)\s*\d", re.IGNORECASE)

EXCLUDE_WORDS = [
    # 기존 목록
    "팝니다", "삽니다", "매입", "크레딧", "양도", "쿠폰", "판매", "구매",
    # 보강: 실데이터에서 걸러지지 않던 거래글 표현
    "팔아요", "팔어요", "팜", "거래", "매매", "급처", "처분", "나눔",
    "넘깁니다", "넘겨요", "구합니다", "구해요",
]

# 주식/상장 글은 고객 VoC가 아님 (채비 코스닥 상장 이후 유입. '주가'는 "이번주가"에 오탐되어 제외)
FINANCE_WORDS = ["공모주", "공모가", "코스닥", "상장", "주가 종합", "증권신고서"]


def is_excluded_post(title: str) -> bool:
    """포인트/카드 판매·거래 글, 주식/상장 글 등 VoC가 아닌 글이면 True."""
    title = str(title)
    if PRICE_ARROW_RE.search(title):
        return True
    return any(word in title for word in EXCLUDE_WORDS + FINANCE_WORDS)


# ======================================================
# [2] 브랜드별 관련성 판정
# ======================================================
# 제목이 충전 관련임을 나타내는 문맥 단어 ('전기차'/'휴게소'는 시승기·여행글까지 통과시켜 제외)
CHARGING_CONTEXT_KR = ["충전", "급속", "완속", "중속", "슈퍼차저", "로밍", "콤보", "요금", "과금"]
CHARGING_CONTEXT_EN = ["nacs", "kw"]

# 브랜드별 수집 규칙
#  - names:    브랜드로 인정하는 표기 (기본: 키워드 자신)
#  - noise:    브랜드와 무관한 합성어·관용구 — 제거 후에도 브랜드명이 남아야 인정
#  - in_title: True면 제목에 브랜드명이 반드시 있어야 함 (일반명사와 겹치는 브랜드)
#  - context:  True면 제목에 충전 문맥 단어도 함께 있어야 함
KEYWORD_RULES = {
    "워터": {
        "in_title": True,
        "context": True,
        "noise": [
            "워터파크", "베이스워터", "워터펌프", "워터밤", "워터마크",
            "미네랄워터", "스파클링워터", "워터프루프", "워터슬라이드",
            "워터게이트", "워터테마",
        ],
    },
    "채비": {
        "in_title": True,
        "context": False,  # "채비 개인정보 유출" 같은 실제 VoC가 충전 단어 없이도 존재
        "noise": [
            "진출 채비", "출발 채비", "떠날 채비", "갈 채비", "나들이 채비",
            "겨울 채비", "월동 채비", "장마 채비", "출근 채비", "이사 채비",
            "여행 채비", "채비를", "채비하", "채비 중", "채비중",
            "채비 본격화", "채비 나서",
        ],
    },
    "일렉링크": {
        "in_title": False,
        "context": False,
        # "sk 일렉 선넘은거 아닌가요?", "SK일렉트링크" 같은 축약/오기 표기도 브랜드로 인정
        "names": ["일렉링크", "sk일렉", "sk 일렉"],
        "noise": [],
    },
    "이브이시스": {
        "in_title": False,
        "context": False,
        "names": ["이브이시스", "EVSIS"],
        "noise": [],
    },
    # 그 외 키워드는 기본 규칙(in_title=False, noise 없음) 적용
}


def has_charging_context(title: str) -> bool:
    """제목에 충전 관련 문맥 단어가 있으면 True."""
    title = str(title)
    lower = title.lower()
    return any(w in title for w in CHARGING_CONTEXT_KR) or any(w in lower for w in CHARGING_CONTEXT_EN)


def _strip_noise(text: str, noise_words) -> str:
    for word in noise_words:
        text = text.replace(word, "")
    return text


def _contains_name(text: str, names) -> bool:
    # 대소문자 무시 비교 (한글은 lower()에 영향 없음, "SK일렉"/"sk일렉"/"EVSIS"/"evsis" 모두 인식)
    lower = text.lower()
    return any(name.lower() in lower for name in names)


def is_relevant(keyword: str, title: str) -> bool:
    """검색 키워드(브랜드) 기준으로 제목이 VoC 수집 대상이면 True."""
    title = str(title)
    rule = KEYWORD_RULES.get(keyword, {})
    names = rule.get("names", [keyword])
    stripped = _strip_noise(title, rule.get("noise", []))
    brand_in_title = _contains_name(stripped, names)

    if rule.get("in_title"):
        # 일반명사와 겹치는 브랜드: 노이즈 제거 후에도 제목에 브랜드명이 남아야 함
        if not brand_in_title:
            return False
        return has_charging_context(title) if rule.get("context") else True

    # 고유 브랜드명: 제목에 있으면 수집, 없으면(본문 매칭) 충전 관련 제목일 때만 수집
    return brand_in_title or has_charging_context(title)


def contains_brand(text: str, brand: str) -> bool:
    """유튜브 댓글 등 자유 텍스트에 브랜드 언급이 있으면 True (동음이의어 노이즈 제거 후 판정)."""
    text = str(text)
    rule = KEYWORD_RULES.get(brand, {})
    stripped = _strip_noise(text, rule.get("noise", []))
    return _contains_name(stripped, rule.get("names", [brand]))


# ======================================================
# [3] 네이버 링크 정규화
# ======================================================
def canonicalize_link(url: str) -> str:
    """네이버 검색이 붙이는 ?art=<토큰>을 제거 (검색 시점마다 달라져 중복 제거를 방해함)."""
    return re.sub(r"\?art=.*$", "", str(url))
