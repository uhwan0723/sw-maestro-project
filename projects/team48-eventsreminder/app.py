"""Streamlit 캘린더 UI"""

import streamlit as st
from streamlit_calendar import calendar
from datetime import datetime
from db import init_db, get_all_events, get_reminders_for_event, update_reminder, add_reminder, delete_reminder

init_db()

CATEGORY_COLORS = {
    "면접": "#FF6B6B",
    "시험": "#4ECDC4",
    "약속": "#45B7D1",
    "마감": "#FFA07A",
    "기타": "#95A5A6",
}

st.set_page_config(page_title="AI 캘린더 리마인더", layout="wide")
st.title("AI 캘린더 리마인더")

events = get_all_events()

calendar_events = []
for e in events:
    calendar_events.append({
        "id": e["id"],
        "title": f"[{e.get('category', '기타')}] {e['title']}",
        "start": e["start_time"],
        "end": e.get("end_time", e["start_time"]),
        "color": CATEGORY_COLORS.get(e.get("category", "기타"), "#95A5A6"),
    })

calendar_options = {
    "initialView": "dayGridMonth",
    "headerToolbar": {
        "left": "prev,next today",
        "center": "title",
        "right": "dayGridMonth,timeGridWeek,timeGridDay",
    },
    "selectable": True,
    "editable": False,
    "locale": "ko",
}

selected = calendar(events=calendar_events, options=calendar_options, key="cal")

st.divider()

if selected and selected.get("eventClick"):
    event_id = selected["eventClick"]["event"]["id"]

    event = next((e for e in events if e["id"] == event_id), None)
    if event:
        st.subheader(event["title"])
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**카테고리:** {event.get('category', '미분류')}")
            st.write(f"**시작:** {event['start_time']}")
            if event.get("end_time"):
                st.write(f"**종료:** {event['end_time']}")
        with col2:
            if event.get("description"):
                st.write(f"**설명:** {event['description']}")

        st.subheader("리마인더 목록")
        reminders = get_reminders_for_event(event_id)

        if not reminders:
            st.info("등록된 리마인더가 없습니다.")
        else:
            for r in reminders:
                existing = datetime.fromisoformat(r["remind_at"])
                col_date, col_time, col_msg, col_status, col_del = st.columns([2, 2, 4, 1, 1])
                with col_date:
                    new_date = st.date_input("날짜", value=existing.date(), key=f"date_{r['id']}", label_visibility="collapsed")
                with col_time:
                    new_time = st.time_input("시각", value=existing.time(), key=f"time_{r['id']}", label_visibility="collapsed")
                new_dt = datetime.combine(new_date, new_time)
                existing_truncated = existing.replace(microsecond=0)
                if new_dt != existing_truncated:
                    update_reminder(r["id"], new_dt.isoformat())
                    st.rerun()
                with col_msg:
                    st.write(r["message"])
                with col_status:
                    st.write("발송완료" if r["is_sent"] else "대기중")
                with col_del:
                    if st.button("삭제", key=f"del_{r['id']}"):
                        delete_reminder(r["id"])
                        st.rerun()

        st.subheader("리마인더 추가")
        with st.form(key=f"add_form_{event_id}", clear_on_submit=True):
            col_date, col_time, col_msg, col_btn = st.columns([2, 2, 4, 1])
            with col_date:
                new_date = st.date_input("날짜", label_visibility="collapsed")
            with col_time:
                new_time = st.time_input("시각", label_visibility="collapsed")
            with col_msg:
                new_message = st.text_input("메시지", label_visibility="collapsed", placeholder="알림 메시지")
            with col_btn:
                submitted = st.form_submit_button("추가")
            if submitted and new_message:
                remind_at = datetime.combine(new_date, new_time).isoformat()
                add_reminder(event_id, remind_at, new_message)
                st.rerun()
else:
    st.info("캘린더에서 일정을 클릭하면 상세 정보와 리마인더를 볼 수 있습니다.")
