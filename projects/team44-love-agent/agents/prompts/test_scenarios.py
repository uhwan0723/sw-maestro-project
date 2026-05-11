"""
프롬프트 검증 테스트 스크립트
시나리오 3개로 전체 파이프라인 (supervisor → agents × 3 rounds → final summary) 을 검증한다.

실행 전 준비:
    pip install anthropic
    export ANTHROPIC_API_KEY=sk-ant-...

실행:
    python test_scenarios.py
"""

import json
import os
import sys
from pathlib import Path
import anthropic

PROMPTS_DIR = Path(__file__).parent
MODEL = "claude-sonnet-4-6"

SCENARIOS = [
    {
        "id": 1,
        "user_concern": (
            "썸 타는 상대가 있는데, 카톡 답장이 항상 2~3일씩 늦어요. "
            "보내면 읽음 표시는 바로 뜨는데 답장은 한참 후에 와요. "
            "물어보면 바빠서 그렇다고 하는데, 정말 바쁜 건지 관심이 없는 건지 모르겠어요."
        ),
        "check_point": "6개 에이전트 의견이 실제로 다른지",
    },
    {
        "id": 2,
        "user_concern": (
            "3개월 전에 헤어진 전 남자친구가 갑자기 연락이 왔어요. "
            "별 내용은 없고 '잘 지내냐'는 말 한마디였어요. "
            "제가 먼저 정리하자고 했던 이별이었는데, 지금도 미련이 좀 남아 있어서 "
            "어떻게 반응해야 할지 모르겠어요."
        ),
        "check_point": "슈퍼바이저가 쟁점을 정확히 추출하는지",
    },
    {
        "id": 3,
        "user_concern": (
            "남자친구가 약속을 자꾸 취소해요. 한 달에 서너 번은 되는 것 같아요. "
            "이유는 거의 설명 안 하고 '미안, 오늘 못 갈 것 같아'라고만 해요. "
            "따지면 예민하다고 하고, 이해하려고 하면 제 마음이 너무 힘들어요."
        ),
        "check_point": "최종 요약이 한쪽 편에 치우치지 않는지",
    },
]

AGENT_NAMES = ["현실주의자", "공감형 감성론자", "신중한 분석가", "행동파 조언자", "균형형 중재자", "친구형 상담자"]

ROUND1_FIELDS = {"agent_name", "stance", "advice", "rationale", "suggested_action", "risk_note"}
ROUND2_FIELDS = {"agent_name", "agrees_with", "disagrees_with", "rebuttal", "supplement"}
ROUND3_FIELDS = {"agent_name", "final_stance", "stance_changed", "change_reason", "final_action"}
SUMMARY_FIELDS = {"situation_summary", "main_conflict", "consensus", "final_advice", "action_steps", "caution"}


def load_prompt(filename: str) -> str:
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8")


def call_llm(client: anthropic.Anthropic, system: str, user: str) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text.strip()


def parse_json_output(raw: str) -> dict:
    start = raw.find("{")
    end = raw.rfind("}") + 1
    return json.loads(raw[start:end])


def check_fields(data: dict, required: set, label: str) -> list[str]:
    missing = required - set(data.keys())
    errors = []
    if missing:
        errors.append(f"[{label}] 누락 필드: {missing}")
    for k, v in data.items():
        if v is None or v == "" and k not in {"change_reason", "consensus"}:
            errors.append(f"[{label}] 빈 값 필드: {k}")
    return errors


def run_scenario(client: anthropic.Anthropic, scenario: dict, prompts: dict) -> dict:
    concern = scenario["user_concern"]
    errors = []
    warnings = []

    # ── Supervisor 1단계 ──────────────────────────────────────────
    sup_raw = call_llm(
        client,
        prompts["supervisor"],
        f"user_concern: {concern}",
    )
    try:
        sup1 = parse_json_output(sup_raw)
    except json.JSONDecodeError as e:
        return {"scenario": scenario["id"], "passed": False, "errors": [f"Supervisor 1단계 JSON 파싱 실패: {e}"]}

    sup1_required = {"situation_brief", "key_issues", "emotional_state", "debate_goal"}
    errors += check_fields(sup1, sup1_required, "supervisor_round1")

    # ── Round 1: 6개 에이전트 독립 의견 ──────────────────────────
    round1_outputs = {}
    stances = {}
    for agent in AGENT_NAMES:
        raw = call_llm(
            client,
            prompts["agents"],
            json.dumps(
                {
                    "round": 1,
                    "agent": agent,
                    "user_concern": concern,
                    "supervisor_analysis": sup1,
                },
                ensure_ascii=False,
            ),
        )
        try:
            out = parse_json_output(raw)
        except json.JSONDecodeError as e:
            errors.append(f"[Round1/{agent}] JSON 파싱 실패: {e}")
            continue
        errors += check_fields(out, ROUND1_FIELDS, f"Round1/{agent}")
        round1_outputs[agent] = out
        stances[agent] = out.get("stance", "")

    # 에이전트 의견 다양성 확인 (시나리오 1 핵심 검증)
    unique_stances = set(stances.values())
    if len(unique_stances) < 4:
        warnings.append(f"Round1 stance 다양성 부족: {len(unique_stances)}개 고유 입장 (기대값 ≥ 4)")

    # ── Supervisor 2단계 ──────────────────────────────────────────
    sup2_raw = call_llm(
        client,
        prompts["supervisor"],
        json.dumps({"round": 2, "round1_opinions": list(round1_outputs.values())}, ensure_ascii=False),
    )
    try:
        sup2 = parse_json_output(sup2_raw)
    except json.JSONDecodeError as e:
        errors.append(f"Supervisor 2단계 JSON 파싱 실패: {e}")
        sup2 = {}

    sup2_required = {"agreements", "conflicts", "focus_for_round2"}
    errors += check_fields(sup2, sup2_required, "supervisor_round2")

    # 쟁점 추출 품질 확인 (시나리오 2 핵심 검증)
    if sup2.get("conflicts") and len(sup2["conflicts"]) < 1:
        warnings.append("Supervisor 2단계: conflicts 배열이 비어 있음")

    # ── Round 2: 반박 및 보완 ─────────────────────────────────────
    round2_outputs = {}
    for agent in AGENT_NAMES:
        raw = call_llm(
            client,
            prompts["agents"],
            json.dumps(
                {
                    "round": 2,
                    "agent": agent,
                    "user_concern": concern,
                    "supervisor_round2_analysis": sup2,
                    "round1_opinions": list(round1_outputs.values()),
                },
                ensure_ascii=False,
            ),
        )
        try:
            out = parse_json_output(raw)
        except json.JSONDecodeError as e:
            errors.append(f"[Round2/{agent}] JSON 파싱 실패: {e}")
            continue
        errors += check_fields(out, ROUND2_FIELDS, f"Round2/{agent}")
        round2_outputs[agent] = out

        # 단순 반복 여부 확인
        r1_stance = round1_outputs.get(agent, {}).get("stance", "")
        r2_rebuttal = out.get("rebuttal", "")
        if r1_stance and r2_rebuttal and r1_stance.strip() == r2_rebuttal.strip():
            warnings.append(f"[Round2/{agent}] rebuttal이 Round1 stance와 동일 (단순 반복 의심)")

    # ── Round 3: 최종 입장 ────────────────────────────────────────
    round3_outputs = {}
    for agent in AGENT_NAMES:
        raw = call_llm(
            client,
            prompts["agents"],
            json.dumps(
                {
                    "round": 3,
                    "agent": agent,
                    "user_concern": concern,
                    "round1_opinions": list(round1_outputs.values()),
                    "round2_opinions": list(round2_outputs.values()),
                },
                ensure_ascii=False,
            ),
        )
        try:
            out = parse_json_output(raw)
        except json.JSONDecodeError as e:
            errors.append(f"[Round3/{agent}] JSON 파싱 실패: {e}")
            continue
        errors += check_fields(out, ROUND3_FIELDS, f"Round3/{agent}")
        round3_outputs[agent] = out

    # ── Final Summary ─────────────────────────────────────────────
    summary_raw = call_llm(
        client,
        prompts["final_summary"],
        json.dumps(
            {
                "user_concern": concern,
                "round1_opinions": list(round1_outputs.values()),
                "round2_opinions": list(round2_outputs.values()),
                "round3_opinions": list(round3_outputs.values()),
            },
            ensure_ascii=False,
        ),
    )
    try:
        summary = parse_json_output(summary_raw)
    except json.JSONDecodeError as e:
        errors.append(f"Final summary JSON 파싱 실패: {e}")
        summary = {}

    errors += check_fields(summary, SUMMARY_FIELDS, "final_summary")

    # action_steps 개수 확인 (시나리오 3 핵심 검증)
    action_steps = summary.get("action_steps", [])
    if len(action_steps) < 2:
        errors.append(f"Final summary action_steps 부족: {len(action_steps)}개 (최소 2개 필요)")

    # 중립성 확인: caution에 면책 문구 포함 여부
    caution = summary.get("caution", "")
    if "전문 심리상담" not in caution:
        warnings.append("Final summary caution에 면책 문구 누락")

    passed = len(errors) == 0
    return {
        "scenario": scenario["id"],
        "check_point": scenario["check_point"],
        "passed": passed,
        "errors": errors,
        "warnings": warnings,
        "supervisor_analysis": sup1,
        "summary": summary,
    }


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("오류: ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    prompts = {
        "supervisor": load_prompt("supervisor.md"),
        "agents": load_prompt("relationship_agents.md"),
        "round_prompts": load_prompt("round_prompts.md"),
        "final_summary": load_prompt("final_summary.md"),
    }

    all_passed = True
    for scenario in SCENARIOS:
        print(f"\n{'='*60}")
        print(f"시나리오 {scenario['id']}: {scenario['check_point']}")
        print(f"고민: {scenario['user_concern'][:50]}...")
        print("=" * 60)

        result = run_scenario(client, scenario, prompts)

        status = "PASS" if result["passed"] else "FAIL"
        print(f"결과: {status}")

        if result.get("errors"):
            print("오류:")
            for e in result["errors"]:
                print(f"  ✗ {e}")

        if result.get("warnings"):
            print("경고:")
            for w in result["warnings"]:
                print(f"  △ {w}")

        if not result["passed"]:
            all_passed = False

    print(f"\n{'='*60}")
    print(f"전체 결과: {'전체 통과' if all_passed else '일부 실패'}")
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
