package com.skillsmarket.demo.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.awaitility.Awaitility.await;

import com.skillsmarket.demo.domain.GenerationStatus;
import com.skillsmarket.demo.domain.SkillGenerationRequest;
import com.skillsmarket.demo.dto.SkillGenerateResponse;
import com.skillsmarket.demo.repository.SkillGenerationRequestRepository;
import java.time.Duration;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
@EnabledIfEnvironmentVariable(named = "OPENAI_API_KEY", matches = ".+")
class SkillGenerationPipelineIntegrationTest {

    @Autowired
    private SkillGenerationService skillGenerationService;

    @Autowired
    private SkillGenerationRequestRepository repository;

    @Test
    void 전체_파이프라인_통합_테스트_userPrompt_입력부터_COMPLETED까지() {
        // given
        SkillGenerateResponse response = skillGenerationService.submitGenerationRequest(
                "Spring Boot REST API를 자동으로 생성하는 Claude Code 스킬을 만들어주세요"
        );
        Long requestId = response.requestId();

        // when
        skillGenerationService.runPipeline(requestId);

        // then
        await().atMost(Duration.ofMinutes(5)).untilAsserted(() -> {
            SkillGenerationRequest result = repository.findById(requestId).orElseThrow();
            assertThat(result.getStatus()).isEqualTo(GenerationStatus.COMPLETED);
            assertThat(result.getFinalSkillContent()).isNotBlank();
            assertThat(result.getReviewFeedback()).isNotBlank();
            assertThat(result.getGeneratedSkillContent()).isNotBlank();
            assertThat(result.getClarifiedRequirements()).isNotBlank();
        });
    }
}
