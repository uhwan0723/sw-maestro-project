package com.skillsmarket.demo.dto;

import jakarta.validation.constraints.NotBlank;

public record SkillGenerateRequest(
        @NotBlank String userPrompt
) {
}
