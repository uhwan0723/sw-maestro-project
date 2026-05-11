package com.skillsmarket.demo.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.skillsmarket.demo.domain.GenerationStatus;
import com.skillsmarket.demo.domain.SkillGenerationRequest;
import com.skillsmarket.demo.repository.SkillGenerationRequestRepository;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.InOrder;
import org.springframework.test.util.ReflectionTestUtils;

class SkillGenerationPipelineTest {

    private SkillGenerationRequestRepository repository;
    private SseEmitterService sseEmitterService;
    private DeepthinkService deepthinkService;
    private SkillCreatorAgentService skillCreatorAgentService;
    private SkillReviewAgentService skillReviewAgentService;
    private SkillGenerationService skillGenerationService;

    @BeforeEach
    void setUp() {
        repository = mock(SkillGenerationRequestRepository.class);
        sseEmitterService = mock(SseEmitterService.class);
        deepthinkService = mock(DeepthinkService.class);
        skillCreatorAgentService = mock(SkillCreatorAgentService.class);
        skillReviewAgentService = mock(SkillReviewAgentService.class);

        skillGenerationService = new SkillGenerationService(
                repository,
                sseEmitterService,
                deepthinkService,
                skillCreatorAgentService,
                skillReviewAgentService
        );
    }

    private SkillGenerationRequest createRequestWithId(Long id) {
        SkillGenerationRequest request = SkillGenerationRequest.create("테스트 프롬프트");
        ReflectionTestUtils.setField(request, "id", id);
        return request;
    }

    @Test
    void review_후_refine_후_COMPLETED_상태_전환_순서_검증() {
        // given
        Long requestId = 1L;
        String reviewFeedback = "리뷰 피드백 내용";
        String finalContent = "최종 스킬 내용";

        SkillGenerationRequest request = createRequestWithId(requestId);

        when(repository.findById(requestId)).thenReturn(Optional.of(request));
        when(repository.save(any())).thenReturn(request);
        when(deepthinkService.clarify(requestId)).thenReturn("clarified");
        when(skillCreatorAgentService.generate(requestId)).thenReturn("generated");
        when(skillReviewAgentService.review(requestId)).thenReturn(reviewFeedback);
        when(skillCreatorAgentService.refine(requestId, reviewFeedback)).thenReturn(finalContent);

        // when
        skillGenerationService.runPipeline(requestId);

        // then
        InOrder inOrder = inOrder(skillReviewAgentService, skillCreatorAgentService, sseEmitterService);
        inOrder.verify(skillReviewAgentService).review(requestId);
        inOrder.verify(sseEmitterService).sendEvent(requestId, GenerationStatus.REFINING);
        inOrder.verify(skillCreatorAgentService).refine(requestId, reviewFeedback);
        inOrder.verify(sseEmitterService).sendCompletedEvent(eq(requestId), eq(finalContent));
        inOrder.verify(sseEmitterService).completeEmitter(requestId);

        assertThat(request.getFinalSkillContent()).isEqualTo(finalContent);
        assertThat(request.getStatus()).isEqualTo(GenerationStatus.COMPLETED);
    }

    @Test
    void 파이프라인_중_예외_발생_시_status가_FAILED로_전환() {
        // given
        Long requestId = 1L;
        SkillGenerationRequest request = createRequestWithId(requestId);

        when(repository.findById(requestId)).thenReturn(Optional.of(request));
        when(repository.save(any())).thenReturn(request);
        doThrow(new RuntimeException("Review failed")).when(skillReviewAgentService).review(requestId);
        when(deepthinkService.clarify(requestId)).thenReturn("clarified");
        when(skillCreatorAgentService.generate(requestId)).thenReturn("generated");

        // when
        skillGenerationService.runPipeline(requestId);

        // then
        assertThat(request.getStatus()).isEqualTo(GenerationStatus.FAILED);
        verify(sseEmitterService).sendEvent(requestId, GenerationStatus.FAILED);
        verify(sseEmitterService).completeEmitter(requestId);
    }
}
