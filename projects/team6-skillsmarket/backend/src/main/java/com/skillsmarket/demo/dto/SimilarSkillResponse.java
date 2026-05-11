package com.skillsmarket.demo.dto;

import org.springframework.ai.document.Document;

public record SimilarSkillResponse(
        long id,
        String title,
        String description,
        int percentage
) {

    public SimilarSkillResponse(Document document) {
        this(
                ((Number) document.getMetadata().get("skillId")).longValue(),
                (String) document.getMetadata().get("title"),
                (String) document.getMetadata().get("description"),
                toPercentage(document.getScore())
        );
    }

    private static int toPercentage(Double score) {
        return (int) Math.round(score * 100);
    }
}
