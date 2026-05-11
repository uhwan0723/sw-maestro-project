package com.skillsmarket.demo.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.skillsmarket.demo.domain.GenerationStatus;
import com.skillsmarket.demo.domain.SkillGenerationRequest;
import com.skillsmarket.demo.repository.SkillGenerationRequestRepository;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

@SpringBootTest
@ActiveProfiles("test")
@EnabledIfEnvironmentVariable(named = "OPENAI_API_KEY", matches = ".+")
class DeepthinkServiceIntegrationTest {

    @Autowired
    private DeepthinkService deepthinkService;

    @Autowired
    private SkillGenerationRequestRepository repository;

    @Test
    void 모호한_프롬프트_입력_시_구조화된_출력_반환() {
        // given
        SkillGenerationRequest request = SkillGenerationRequest.create("뭔가 좋은 스킬 만들어줘");
        request.updateStatus(GenerationStatus.CLARIFYING);
        SkillGenerationRequest saved = repository.save(request);

        // when
        String result = deepthinkService.clarify(saved.getId());

        // then
        assertThat(result).isNotBlank();
        assertThat(result).containsAnyOf("목적", "대상", "핵심기능", "제약사항");
    }

    @Test
    void clarify_후_DB_status가_GENERATING으로_전환() {
        // given
        SkillGenerationRequest request = SkillGenerationRequest.create("Spring Boot API 스킬 만들어줘");
        request.updateStatus(GenerationStatus.CLARIFYING);
        SkillGenerationRequest saved = repository.save(request);

        // when
        deepthinkService.clarify(saved.getId());

        // then
        SkillGenerationRequest found = repository.findById(saved.getId()).orElseThrow();
        assertThat(found.getStatus()).isEqualTo(GenerationStatus.GENERATING);
    }

    @Test
    void clarify_후_clarifiedRequirements_필드가_비어있지_않음() {
        // given
        SkillGenerationRequest request = SkillGenerationRequest.create("데이터 분석 도구 스킬 만들어줘");
        request.updateStatus(GenerationStatus.CLARIFYING);
        SkillGenerationRequest saved = repository.save(request);

        // when
        deepthinkService.clarify(saved.getId());

        // then
        SkillGenerationRequest found = repository.findById(saved.getId()).orElseThrow();
        assertThat(found.getClarifiedRequirements()).isNotBlank();
    }
}
