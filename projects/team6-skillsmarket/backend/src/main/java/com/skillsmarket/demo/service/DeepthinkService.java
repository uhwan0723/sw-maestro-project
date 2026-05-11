package com.skillsmarket.demo.service;

import com.skillsmarket.demo.domain.GenerationStatus;
import com.skillsmarket.demo.domain.SkillGenerationRequest;
import com.skillsmarket.demo.repository.SkillGenerationRequestRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.stereotype.Service;

@Slf4j
@Service
public class DeepthinkService {

    private static final String SYSTEM_PROMPT = """
            당신은 유저의 스킬 생성 요청을 분석하고 구조화하는 전문가입니다.
            유저의 모호한 요청을 받아서 다음 항목으로 구조화하여 반환하세요:

            1. **목적**: 이 스킬이 해결하고자 하는 문제 또는 달성하고자 하는 목표
            2. **대상**: 이 스킬의 주요 사용자 또는 대상 시스템
            3. **핵심기능**: 이 스킬이 제공해야 하는 주요 기능 목록
            4. **제약사항**: 기술적 제약, 보안 요구사항, 성능 요구사항 등

            구조화된 결과를 명확하고 상세하게 작성하세요.
            """;

    private final ChatClient chatClient;
    private final SkillGenerationRequestRepository repository;
    private final SseEmitterService sseEmitterService;

    public DeepthinkService(ChatClient.Builder chatClientBuilder,
                            SkillGenerationRequestRepository repository,
                            SseEmitterService sseEmitterService) {
        this.chatClient = chatClientBuilder.build();
        this.repository = repository;
        this.sseEmitterService = sseEmitterService;
    }

    public String clarify(Long requestId) {
        log.info("Starting deepthink clarification for requestId={}", requestId);

        SkillGenerationRequest request = repository.findById(requestId)
                .orElseThrow(() -> new IllegalArgumentException("Request not found: " + requestId));

        String result = chatClient.prompt()
                .system(SYSTEM_PROMPT)
                .user(request.getUserPrompt())
                .call()
                .content();

        request.updateClarifiedRequirements(result);
        request.updateStatus(GenerationStatus.GENERATING);
        repository.save(request);

        sseEmitterService.sendEvent(requestId, GenerationStatus.GENERATING);

        log.info("Deepthink clarification completed for requestId={}", requestId);
        return result;
    }
}
