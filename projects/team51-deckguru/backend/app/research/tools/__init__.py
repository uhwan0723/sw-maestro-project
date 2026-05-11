"""Live Research에서 호출하는 외부 도구 모음.

각 도구는 네트워크 실패를 자체적으로 흡수하거나 `ResearchToolError`로 통일해
graph가 graceful degrade할 수 있게 만든다.
"""
