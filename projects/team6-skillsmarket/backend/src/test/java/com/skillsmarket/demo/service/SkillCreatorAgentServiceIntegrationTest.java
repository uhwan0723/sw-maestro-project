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
class SkillCreatorAgentServiceIntegrationTest {

    @Autowired
    private SkillCreatorAgentService skillCreatorAgentService;

    @Autowired
    private SkillGenerationRequestRepository repository;

    @Test
    void 구조화된_요구사항_입력_시_마크다운_스킬_생성() {
        // given
        SkillGenerationRequest request = SkillGenerationRequest.create("Spring Boot API 스킬");
        request.updateClarifiedRequirements("""
                **목적**: Spring Boot REST API를 자동으로 생성하는 스킬
                **대상**: Spring Boot 개발자
                **핵심기능**: CRUD 엔드포인트 자동 생성, DTO 생성, 예외 처리
                **제약사항**: Java 17 이상, Spring Boot 3.x 호환
                """);
        request.updateStatus(GenerationStatus.GENERATING);
        SkillGenerationRequest saved = repository.save(request);

        // when
        String result = skillCreatorAgentService.generate(saved.getId());

        // then
        assertThat(result).isNotBlank();
    }

    @Test
    void 생성된_스킬에_마크다운_헤더가_포함되어_있음() {
        // given
        SkillGenerationRequest request = SkillGenerationRequest.create("코드 리뷰 스킬");
        request.updateClarifiedRequirements("""
                **목적**: 코드 리뷰를 자동으로 수행하는 스킬
                **대상**: 개발팀
                **핵심기능**: 코드 품질 분석, 버그 탐지, 개선 제안
                **제약사항**: Python, Java, TypeScript 지원
                """);
        request.updateStatus(GenerationStatus.GENERATING);
        SkillGenerationRequest saved = repository.save(request);

        // when
        String result = skillCreatorAgentService.generate(saved.getId());

        // then
        assertThat(result).contains("#");
    }

    @Test
    void generate_후_DB_status가_REVIEWING으로_전환() {
        // given
        SkillGenerationRequest request = SkillGenerationRequest.create("테스트 스킬");
        request.updateClarifiedRequirements("""
                **목적**: 테스트 자동화 스킬
                **대상**: QA 엔지니어
                **핵심기능**: 단위 테스트 생성, 통합 테스트 생성
                **제약사항**: JUnit 5 기반
                """);
        request.updateStatus(GenerationStatus.GENERATING);
        SkillGenerationRequest saved = repository.save(request);

        // when
        skillCreatorAgentService.generate(saved.getId());

        // then
        SkillGenerationRequest found = repository.findById(saved.getId()).orElseThrow();
        assertThat(found.getStatus()).isEqualTo(GenerationStatus.REVIEWING);
    }
}
