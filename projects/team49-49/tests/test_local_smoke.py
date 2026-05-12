from scripts.smoke_local import run_smoke


def test_local_smoke_uses_sqlite_and_exercises_core_flow(tmp_path):
    db_path = tmp_path / "local_smoke.sqlite3"

    result = run_smoke(db_path)

    assert db_path.exists()
    assert result["health"]["status"] == "ok"
    assert result["database"].endswith("local_smoke.sqlite3")
    assert result["ingestion"]["chunk_count"] == 2
    assert result["ingestion"]["card_count"] == 2
    assert result["qa"]["answer"] == "UPSTAGE_API_KEY가 설정되지 않았습니다."
    assert result["qa"]["evidence_cards"]
