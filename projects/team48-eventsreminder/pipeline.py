from calendar_sync import fetch_events
from classifier import classify_event
from reminder import generate_reminders
from db import init_db, save_event, save_reminders, delete_ai_reminders


def run_pipeline(ical_url: str):
    init_db()

    events = fetch_events(ical_url)
    print(f"{len(events)}개 일정을 가져왔습니다.")

    for event in events:
        event["category"] = classify_event(
            event["title"],
            event.get("description", "")
        )
        print(f"  [{event['category']}] {event['title']}")

        reminders = generate_reminders(event) or []
        print(f"    → 리마인더 {len(reminders)}개 생성")

        save_event(event)
        delete_ai_reminders(event["id"])
        save_reminders(reminders)

    print("파이프라인 완료.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("사용법: python pipeline.py <iCal URL>")
        sys.exit(1)
    run_pipeline(sys.argv[1])
