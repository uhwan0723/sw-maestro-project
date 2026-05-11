package com.skillsmarket.demo.dto;

import com.skillsmarket.demo.domain.GenerationStatus;
import com.skillsmarket.demo.domain.SkillGenerationRequest;

public record SkillGenerationStatusResponse(
        Long requestId,
        GenerationStatus status,
        String finalSkillContent
) {

    public static SkillGenerationStatusResponse from(SkillGenerationRequest request) {
        String content = request.getStatus() == GenerationStatus.COMPLETED
                ? request.getFinalSkillContent()
                : null;
        return new SkillGenerationStatusResponse(request.getId(), request.getStatus(), content);
    }
}
