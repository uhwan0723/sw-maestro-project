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
class SkillReviewAgentServiceIntegrationTest {

    @Autowired
    private SkillReviewAgentService skillReviewAgentService;

    @Autowired
    private SkillGenerationRequestRepository repository;

    @Test
    void 생성된_스킬_입력_시_구체적_리뷰_피드백_반환() {
        // given
        SkillGenerationRequest request = SkillGenerationRequest.create("코드 리뷰 자동화 스킬");
        request.updateGeneratedSkillContent("""
                # 코드 리뷰 자동화 스킬
                코드를 자동으로 리뷰하는 스킬입니다.

                ## 트리거 조건
                - 코드 리뷰 요청 시

                ## 지시사항
                1. 코드를 분석합니다.
                2. 문제점을 찾습니다.
                3. 개선 사항을 제안합니다.

                ## 제약사항
                - Python, Java, TypeScript 지원

                ## 예시
                코드 리뷰 예시입니다.
                """);
        request.updateStatus(GenerationStatus.REVIEWING);
        SkillGenerationRequest saved = repository.save(request);

        // when
        String result = skillReviewAgentService.review(saved.getId());

        // then
        assertThat(result).isNotBlank();
    }
}
