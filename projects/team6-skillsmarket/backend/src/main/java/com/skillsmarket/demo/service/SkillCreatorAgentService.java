package com.skillsmarket.demo.service;

import com.skillsmarket.demo.domain.GenerationStatus;
import com.skillsmarket.demo.domain.SkillGenerationRequest;
import com.skillsmarket.demo.repository.SkillGenerationRequestRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.stereotype.Service;

@Slf4j
@Service
public class SkillCreatorAgentService {

    private static final String SYSTEM_PROMPT = """
            당신은 Claude Code skill을 생성하는 전문가(skill-creator)입니다.
            유저의 구조화된 요구사항을 받아서 Claude Code에서 사용 가능한 마크다운 포맷의 스킬을 생성하세요.

            생성하는 스킬은 다음 마크다운 구조를 따라야 합니다:

            # 스킬 이름
            스킬에 대한 간략한 설명.

            ## 트리거 조건
            이 스킬이 활성화되는 조건 목록.

            ## 지시사항
            스킬이 수행해야 하는 상세한 단계별 지시사항.

            ## 제약사항
            스킬 실행 시 지켜야 하는 제약조건.

            ## 예시
            스킬 사용 예시.

            마크다운 헤더(#)를 반드시 포함하고, 구조화된 요구사항의 모든 항목을 반영하세요.
            """;

    private static final String REFINE_SYSTEM_PROMPT = """
            당신은 Claude Code skill을 개선하는 전문가입니다.
            기존 스킬과 리뷰 피드백을 받아서 개선된 버전의 스킬을 생성하세요.
            마크다운 포맷을 유지하면서 피드백에서 지적된 사항을 반영하여 스킬을 수정하세요.
            마크다운 헤더(#)를 반드시 포함하세요.
            """;

    private final ChatClient chatClient;
    private final SkillGenerationRequestRepository repository;
    private final SseEmitterService sseEmitterService;

    public SkillCreatorAgentService(ChatClient.Builder chatClientBuilder,
                                    SkillGenerationRequestRepository repository,
                                    SseEmitterService sseEmitterService) {
        this.chatClient = chatClientBuilder.build();
        this.repository = repository;
        this.sseEmitterService = sseEmitterService;
    }

    public String generate(Long requestId) {
        log.info("Starting skill generation for requestId={}", requestId);

        SkillGenerationRequest request = repository.findById(requestId)
                .orElseThrow(() -> new IllegalArgumentException("Request not found: " + requestId));

        String result = chatClient.prompt()
                .system(SYSTEM_PROMPT)
                .user(request.getClarifiedRequirements())
                .call()
                .content();

        request.updateGeneratedSkillContent(result);
        request.updateStatus(GenerationStatus.REVIEWING);
        repository.save(request);

        sseEmitterService.sendEvent(requestId, GenerationStatus.REVIEWING);

        log.info("Skill generation completed for requestId={}", requestId);
        return result;
    }

    public String refine(Long requestId, String reviewFeedback) {
        log.info("Starting skill refinement for requestId={}", requestId);

        SkillGenerationRequest request = repository.findById(requestId)
                .orElseThrow(() -> new IllegalArgumentException("Request not found: " + requestId));

        String userMessage = """
                ## 기존 스킬
                %s

                ## 리뷰 피드백
                %s
                """.formatted(request.getGeneratedSkillContent(), reviewFeedback);

        String result = chatClient.prompt()
                .system(REFINE_SYSTEM_PROMPT)
                .user(userMessage)
                .call()
                .content();

        log.info("Skill refinement completed for requestId={}", requestId);
        return result;
    }
}
