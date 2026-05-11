"""브리핑 응답을 화면에 렌더한다."""
from textwrap import dedent

import streamlit as st

from app.schemas import BriefingResponse, NewsResult, WeatherData

_DEGRADED_LABEL = {
    "weather": "날씨",
    "news": "뉴스",
    "llm": "AI 요약",
}

_CATEGORY_ICON = {
    "IT": "💻",
    "경제": "📈",
    "사회": "🏛️",
    "문화": "🎭",
    "정치": "⚖️",
    "스포츠": "⚽",
}


def _weather_icon(precip: int) -> str:
    if precip >= 80:
        return "⛈️"
    if precip >= 60:
        return "🌧️"
    if precip >= 40:
        return "🌥️"
    if precip >= 20:
        return "🌤️"
    return "☀️"


def _temp_icon(temp: float) -> str:
    if temp <= 0:
        return "❄️"
    if temp <= 10:
        return "🧣"
    if temp <= 20:
        return "🍃"
    if temp <= 30:
        return "☀️"
    return "🔥"


def _pm_level(pm25: int) -> tuple[str, str, str]:
    if pm25 <= 15:
        return "좋음", "😊", "#2ecc71"
    if pm25 <= 35:
        return "보통", "🙂", "#f1c40f"
    if pm25 <= 75:
        return "나쁨", "😷", "#e67e22"
    return "매우나쁨", "🤢", "#e74c3c"


def _precip_icon(precip: int) -> str:
    if precip >= 60:
        return "☂️"
    if precip >= 40:
        return "🌂"
    return "💧"


def _inject_css() -> None:
    st.markdown(
        """
    <style>
    .hero-card {
        background: transparent;
        border: 1px solid #ddd;
        border-radius: 12px;
        padding: 24px 28px;
        margin-bottom: 20px;
        color: #2d3436;
    }
    .hero-card .tip {
        font-size: 1.05rem;
        font-weight: 600;
        margin-bottom: 10px;
        color: #4a6cf7;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .hero-card .summary {
        font-size: 0.92rem;
        line-height: 1.75;
        color: #4a4a4a;
    }
    .weather-card {
        background: linear-gradient(160deg, #74b9ff 0%, #0984e3 100%);
        border-radius: 16px;
        padding: 28px 24px;
        color: white;
        text-align: center;
        box-shadow: 0 8px 32px rgba(9, 132, 227, 0.2);
    }
    .weather-card .location {
        font-size: 1rem;
        opacity: 0.9;
        margin-bottom: 4px;
        letter-spacing: 0.5px;
    }
    .weather-card .big-icon {
        font-size: 4rem;
        margin: 10px 0;
        filter: drop-shadow(0 4px 8px rgba(0,0,0,0.15));
    }
    .weather-card .temp-main {
        font-size: 2.6rem;
        font-weight: 700;
        margin: 4px 0 2px 0;
    }
    .weather-card .temp-range {
        font-size: 0.95rem;
        opacity: 0.85;
        margin-bottom: 4px;
    }
    .weather-detail-row {
        display: flex;
        justify-content: space-around;
        margin-top: 18px;
        padding-top: 18px;
        border-top: 1px solid rgba(255,255,255,0.25);
    }
    .weather-detail-item {
        text-align: center;
    }
    .weather-detail-item .wd-icon {
        font-size: 1.4rem;
    }
    .weather-detail-item .wd-label {
        font-size: 0.72rem;
        opacity: 0.75;
        margin-top: 2px;
    }
    .weather-detail-item .wd-value {
        font-size: 0.95rem;
        font-weight: 600;
    }
    .weather-summary-box {
        margin-top: 16px;
        padding-top: 14px;
        font-size: 0.85rem;
        opacity: 0.9;
        line-height: 1.5;
        border-top: 1px solid rgba(255,255,255,0.2);
    }
    .news-item {
        background: rgba(248, 249, 250, 0.6);
        border-radius: 12px;
        padding: 16px 18px;
        margin-bottom: 10px;
        border-left: 4px solid #667eea;
        backdrop-filter: blur(4px);
    }
    [data-testid="stAppViewContainer"][data-theme="dark"] .news-item,
    .stApp[data-theme="dark"] .news-item {
        background: rgba(45, 52, 54, 0.5);
    }
    .news-item .ni-title {
        font-size: 0.95rem;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .news-item .ni-title a {
        color: inherit;
        text-decoration: none;
    }
    .news-item .ni-title a:hover {
        color: #667eea;
        text-decoration: underline;
    }
    .news-item .ni-summary {
        font-size: 0.85rem;
        color: #636e72;
        line-height: 1.55;
    }
    .news-item .ni-time {
        font-size: 0.73rem;
        color: #b2bec3;
        margin-top: 6px;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )


def render_briefing(briefing: BriefingResponse) -> None:
    _inject_css()
    _render_degraded_banner(briefing.degraded)
    _render_hero_card(briefing.action_tip, briefing.integrated_summary)

    col_weather, col_news = st.columns([1, 2], gap="large")
    with col_weather:
        st.markdown("### ☁️ 오늘의 날씨")
        if briefing.weather is None:
            st.caption("날씨 정보를 일시적으로 가져오지 못했습니다.")
        else:
            _render_weather(briefing.weather)

    with col_news:
        st.markdown("### 📰 오늘의 뉴스")
        if not briefing.news:
            st.caption("뉴스 정보를 일시적으로 가져오지 못했습니다.")
        else:
            _render_news(briefing.news)

    st.markdown("")
    local_time = briefing.generated_at.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    st.caption(f"🕐 생성 시각: {local_time}")


def _render_degraded_banner(degraded: list[str]) -> None:
    if not degraded:
        return
    labels = [_DEGRADED_LABEL.get(k, k) for k in degraded]
    st.warning(f"⚠️ 일부 정보를 일시적으로 가져오지 못했습니다: {', '.join(labels)}")


def _render_hero_card(action_tip: str, integrated_summary: str) -> None:
    if not action_tip and not integrated_summary:
        return
    tip_html = f'<div class="tip">💡 {action_tip}</div>' if action_tip else ""
    summary_html = (
        f'<div class="summary">{integrated_summary}</div>'
        if integrated_summary
        else ""
    )
    st.markdown(
        f'<div class="hero-card">{tip_html}{summary_html}</div>',
        unsafe_allow_html=True,
    )


def _render_weather(weather: WeatherData) -> None:
    icon = _weather_icon(weather.precipitation_probability)
    avg_temp = (weather.temperature_max + weather.temperature_min) / 2

    pm_html = ""
    if weather.pm25 is not None:
        pm_label, pm_emoji, pm_color = _pm_level(weather.pm25)
        pm_html = (
            f'<div class="weather-detail-item">'
            f'<div class="wd-icon">{pm_emoji}</div>'
            f'<div class="wd-value" style="color:{pm_color}">{pm_label}</div>'
            f'<div class="wd-label">미세먼지 PM2.5 {weather.pm25}</div>'
            f"</div>"
        )
    elif weather.pm10 is not None:
        pm_html = (
            f'<div class="weather-detail-item">'
            f'<div class="wd-icon">🌫️</div>'
            f'<div class="wd-value">{weather.pm10} ㎍/㎥</div>'
            f'<div class="wd-label">미세먼지 PM10</div>'
            f"</div>"
        )

    precip_emoji = _precip_icon(weather.precipitation_probability)

    summary_html = ""
    if weather.summary:
        summary_html = f'<div class="weather-summary-box">📝 {weather.summary}</div>'

    temp_low = _temp_icon(weather.temperature_min)
    temp_high = _temp_icon(weather.temperature_max)

    html = dedent(f"""\
<div class="weather-card">
<div class="location">📍 {weather.location}</div>
<div class="big-icon">{icon}</div>
<div class="temp-main">{avg_temp:.0f}°C</div>
<div class="temp-range">{temp_low} {weather.temperature_min:.1f}° &nbsp;~&nbsp; {weather.temperature_max:.1f}° {temp_high}</div>
<div class="weather-detail-row">
<div class="weather-detail-item">
<div class="wd-icon">{precip_emoji}</div>
<div class="wd-value">{weather.precipitation_probability}%</div>
<div class="wd-label">강수확률</div>
</div>
{pm_html}
</div>
{summary_html}
</div>""")
    st.markdown(html, unsafe_allow_html=True)


def _render_news(news_results: list[NewsResult]) -> None:
    tabs = st.tabs([r.category for r in news_results])
    for tab, result in zip(tabs, news_results, strict=True):
        with tab:
            if not result.items:
                st.caption("이 카테고리에는 표시할 뉴스가 없습니다.")
                continue
            for item in result.items:
                time_str = item.published_at.astimezone().strftime("%m/%d %H:%M")
                news_html = (
                    f'<div class="news-item">'
                    f'<div class="ni-title"><a href="{item.url}" target="_blank">📌 {item.title}</a></div>'
                    f'<div class="ni-summary">{item.summary}</div>'
                    f'<div class="ni-time">🕐 {time_str}</div>'
                    f"</div>"
                )
                st.markdown(news_html, unsafe_allow_html=True)
