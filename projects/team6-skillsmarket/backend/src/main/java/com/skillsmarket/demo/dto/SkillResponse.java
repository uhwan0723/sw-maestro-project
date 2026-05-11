package com.skillsmarket.demo.dto;

import com.skillsmarket.demo.domain.Skills;

public record SkillResponse(
        long id,
        String title,
        String description
) {

    public static SkillResponse from(Skills skill) {
        return new SkillResponse(
                skill.getId(),
                skill.getTitle(),
                skill.getDescription()
        );
    }
}
