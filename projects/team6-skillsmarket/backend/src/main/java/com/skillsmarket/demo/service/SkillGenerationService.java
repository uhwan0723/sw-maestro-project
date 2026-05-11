package com.skillsmarket.demo.service;

import com.skillsmarket.demo.domain.GenerationStatus;
import com.skillsmarket.demo.domain.SkillGenerationRequest;
import com.skillsmarket.demo.dto.SkillGenerateResponse;
import com.skillsmarket.demo.dto.SkillGenerationStatusResponse;
import com.skillsmarket.demo.repository.SkillGenerationRequestRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Slf4j
@Service
@RequiredArgsConstructor
public class SkillGenerationService {

    private final SkillGenerationRequestRepository skillGenerationRequestRepository;
    private final SseEmitterService sseEmitterService;
    private final DeepthinkService deepthinkService;
    private final SkillCreatorAgentService skillCreatorAgentService;
    private final SkillReviewAgentService skillReviewAgentService;

    @Transactional
    public SkillGenerateResponse submitGenerationRequest(String userPrompt) {
        SkillGenerationRequest request = SkillGenerationRequest.create(userPrompt);
        SkillGenerationRequest saved = skillGenerationRequestRepository.save(request);
        return SkillGenerateResponse.from(saved);
    }

    @Transactional(readOnly = true)
    public SkillGenerationStatusResponse getStatus(Long requestId) {
        SkillGenerationRequest request = skillGenerationRequestRepository.findById(requestId)
                .orElseThrow(() -> new IllegalArgumentException("Request not found: " + requestId));
        return SkillGenerationStatusResponse.from(request);
    }

    @Async("skillGenerationExecutor")
    public void runPipeline(Long requestId) {
        log.info("Starting skill generation pipeline for requestId={}", requestId);

        SkillGenerationRequest request = skillGenerationRequestRepository.findById(requestId)
                .orElseThrow(() -> new IllegalArgumentException("Request not found: " + requestId));

        try {
            // Step 1: Clarifying (Deepthink)
            request.updateStatus(GenerationStatus.CLARIFYING);
            skillGenerationRequestRepository.save(request);
            sseEmitterService.sendEvent(requestId, GenerationStatus.CLARIFYING);
            log.info("Pipeline step CLARIFYING for requestId={}", requestId);

            deepthinkService.clarify(requestId);
            // After clarify(), status is GENERATING and SSE event is sent
            request = skillGenerationRequestRepository.findById(requestId)
                    .orElseThrow(() -> new IllegalArgumentException("Request not found: " + requestId));
            log.info("Pipeline step GENERATING for requestId={}", requestId);

            // Step 2: Generating (SkillCreatorAgentService)
            skillCreatorAgentService.generate(requestId);
            // After generate(), status is REVIEWING and S1SE event is sent
            request = skillGenerationRequestRepository.findById(requestId)
                    .orElseThrow(() -> new IllegalArgumentException("Request not found: " + requestId));
            log.info("Pipeline step REVIEWING for requestId={}", requestId);

            // Step 3: Reviewing (SkillReviewAgentService)
            String reviewFeedback = skillReviewAgentService.review(requestId);
            request = skillGenerationRequestRepository.findById(requestId)
                    .orElseThrow(() -> new IllegalArgumentException("Request not found: " + requestId));
            log.info("Pipeline step REVIEWING completed for requestId={}", requestId);

            // Step 4: Refining (SkillCreatorAgentService.refine)
            request.updateStatus(GenerationStatus.REFINING);
            skillGenerationRequestRepository.save(request);
            sseEmitterService.sendEvent(requestId, GenerationStatus.REFINING);
            log.info("Pipeline step REFINING for requestId={}", requestId);

            String finalSkillContent = skillCreatorAgentService.refine(requestId, reviewFeedback);
            request.updateFinalSkillContent(finalSkillContent);
            skillGenerationRequestRepository.save(request);

            // Step 5: Completed
            request.updateStatus(GenerationStatus.COMPLETED);
            skillGenerationRequestRepository.save(request);
            sseEmitterService.sendCompletedEvent(requestId, finalSkillContent);
            sseEmitterService.completeEmitter(requestId);
            log.info("Pipeline COMPLETED for requestId={}", requestId);

        } catch (Exception e) {
            log.error("Pipeline FAILED for requestId={}", requestId, e);
            request.updateStatus(GenerationStatus.FAILED);
            skillGenerationRequestRepository.save(request);
            sseEmitterService.sendEvent(requestId, GenerationStatus.FAILED);
            sseEmitterService.completeEmitter(requestId);
        }
    }
}
