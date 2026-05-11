package com.skillsmarket.demo.dto;

import com.skillsmarket.demo.domain.Skills;

public record SkillDetailResponse(
        long id,
        String title,
        String description,
        String category,
        String content
) {

    public static SkillDetailResponse from(Skills skill) {
        return new SkillDetailResponse(
                skill.getId(),
                skill.getTitle(),
                skill.getDescription(),
                skill.getCategory().name(),
                skill.getContent()
        );
    }
}
