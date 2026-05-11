package com.skillsmarket.demo.service;

import com.skillsmarket.demo.domain.SkillGenerationRequest;
import com.skillsmarket.demo.repository.SkillGenerationRequestRepository;
import lombok.extern.slf4j.Slf4j;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.stereotype.Service;

@Slf4j
@Service
public class SkillReviewAgentService {

    private static final String SYSTEM_PROMPT = """
            당신은 Claude Code skill을 리뷰하는 전문가(skill-reviewer)입니다.
            생성된 스킬을 다음 관점에서 리뷰하고 구체적인 개선 제안을 해주세요:

            1. **품질**: 스킬의 지시사항이 명확하고 구체적인가? 모호한 표현은 없는가?
            2. **완성도**: 필수 섹션(스킬 이름, 트리거 조건, 지시사항, 제약사항, 예시)이 모두 포함되어 있는가? 빠진 내용은 없는가?
            3. **보안**: 민감한 정보 노출 위험, 위험한 명령어 실행 가능성 등 보안 관련 우려사항은 없는가?
            4. **사용성**: 사용자가 이 스킬을 실제로 사용할 때 불편한 점은 없는가? 트리거 조건이 적절한가?

            각 관점에 대해 구체적인 개선 제안을 포함하여 피드백을 작성해주세요.
            개선이 필요 없는 항목도 간단히 언급해주세요.
            """;

    private final ChatClient chatClient;
    private final SkillGenerationRequestRepository repository;

    public SkillReviewAgentService(ChatClient.Builder chatClientBuilder,
                                   SkillGenerationRequestRepository repository) {
        this.chatClient = chatClientBuilder.build();
        this.repository = repository;
    }

    public String review(Long requestId) {
        log.info("Starting skill review for requestId={}", requestId);

        SkillGenerationRequest request = repository.findById(requestId)
                .orElseThrow(() -> new IllegalArgumentException("Request not found: " + requestId));

        String result = chatClient.prompt()
                .system(SYSTEM_PROMPT)
                .user(request.getGeneratedSkillContent())
                .call()
                .content();

        request.updateReviewFeedback(result);
        repository.save(request);

        log.info("Skill review completed for requestId={}", requestId);
        return result;
    }
}
