package com.skillsmarket.demo.repository;

import static org.assertj.core.api.Assertions.assertThat;
import static org.junit.jupiter.api.Assertions.assertAll;

import com.skillsmarket.demo.domain.GenerationStatus;
import com.skillsmarket.demo.domain.SkillGenerationRequest;
import jakarta.validation.ConstraintViolationException;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.util.ReflectionTestUtils;

@SpringBootTest
@ActiveProfiles("test")
class SkillGenerationRequestRepositoryTest {

    @Autowired
    private SkillGenerationRequestRepository repository;

    @Test
    void 모든_필드_정상_persist_확인() {
        // given
        SkillGenerationRequest request = createRequest(
                "Spring Boot REST API 스킬 만들어줘",
                GenerationStatus.COMPLETED
        );
        ReflectionTestUtils.setField(request, "clarifiedRequirements", "구조화된 요구사항");
        ReflectionTestUtils.setField(request, "generatedSkillContent", "생성된 스킬 내용");
        ReflectionTestUtils.setField(request, "reviewFeedback", "리뷰 피드백");
        ReflectionTestUtils.setField(request, "finalSkillContent", "최종 스킬 내용");

        // when
        SkillGenerationRequest saved = repository.save(request);
        SkillGenerationRequest found = repository.findById(saved.getId()).orElseThrow();

        // then
        assertAll(
                () -> assertThat(found.getId()).isNotNull(),
                () -> assertThat(found.getUserPrompt()).isEqualTo("Spring Boot REST API 스킬 만들어줘"),
                () -> assertThat(found.getClarifiedRequirements()).isEqualTo("구조화된 요구사항"),
                () -> assertThat(found.getGeneratedSkillContent()).isEqualTo("생성된 스킬 내용"),
                () -> assertThat(found.getReviewFeedback()).isEqualTo("리뷰 피드백"),
                () -> assertThat(found.getFinalSkillContent()).isEqualTo("최종 스킬 내용"),
                () -> assertThat(found.getStatus()).isEqualTo(GenerationStatus.COMPLETED),
                () -> assertThat(found.getCreatedAt()).isNotNull(),
                () -> assertThat(found.getUpdatedAt()).isNotNull()
        );
    }

    @Test
    void status_enum_값_전환_후_저장_조회_시_값_유지_확인() {
        // given
        SkillGenerationRequest request = createRequest("테스트 프롬프트", GenerationStatus.PENDING);
        SkillGenerationRequest saved = repository.save(request);

        // when - PENDING → CLARIFYING
        ReflectionTestUtils.setField(saved, "status", GenerationStatus.CLARIFYING);
        repository.save(saved);
        SkillGenerationRequest found = repository.findById(saved.getId()).orElseThrow();

        // then
        assertThat(found.getStatus()).isEqualTo(GenerationStatus.CLARIFYING);

        // when - CLARIFYING → GENERATING
        ReflectionTestUtils.setField(found, "status", GenerationStatus.GENERATING);
        repository.save(found);
        SkillGenerationRequest found2 = repository.findById(saved.getId()).orElseThrow();

        // then
        assertThat(found2.getStatus()).isEqualTo(GenerationStatus.GENERATING);
    }

    @Test
    void userPrompt가_null일_때_validation_실패() {
        // given
        SkillGenerationRequest request = new SkillGenerationRequest();
        ReflectionTestUtils.setField(request, "status", GenerationStatus.PENDING);
        // userPrompt를 설정하지 않음 (null)

        // when & then
        org.junit.jupiter.api.Assertions.assertThrows(
                ConstraintViolationException.class,
                () -> repository.saveAndFlush(request)
        );
    }

    @Test
    void userPrompt가_blank일_때_validation_실패() {
        // given
        SkillGenerationRequest request = new SkillGenerationRequest();
        ReflectionTestUtils.setField(request, "userPrompt", "   ");
        ReflectionTestUtils.setField(request, "status", GenerationStatus.PENDING);

        // when & then
        org.junit.jupiter.api.Assertions.assertThrows(
                ConstraintViolationException.class,
                () -> repository.saveAndFlush(request)
        );
    }

    private SkillGenerationRequest createRequest(String userPrompt, GenerationStatus status) {
        SkillGenerationRequest request = new SkillGenerationRequest();
        ReflectionTestUtils.setField(request, "userPrompt", userPrompt);
        ReflectionTestUtils.setField(request, "status", status);
        return request;
    }
}
