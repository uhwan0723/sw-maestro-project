package com.skillsmarket.demo.dto;

import com.skillsmarket.demo.domain.GenerationStatus;
import com.skillsmarket.demo.domain.SkillGenerationRequest;

public record SkillGenerateResponse(
        Long requestId,
        GenerationStatus status
) {

    public static SkillGenerateResponse from(SkillGenerationRequest request) {
        return new SkillGenerateResponse(request.getId(), request.getStatus());
    }
}
