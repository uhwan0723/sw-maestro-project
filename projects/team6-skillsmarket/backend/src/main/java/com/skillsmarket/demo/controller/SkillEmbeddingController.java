package com.skillsmarket.demo.controller;

import com.skillsmarket.demo.dto.SimilarSkillResponses;
import com.skillsmarket.demo.service.SkillEmbeddingService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "Skill Embedding", description = "스킬 임베딩 및 추천 API")
@RestController
@RequestMapping("/skills")
@RequiredArgsConstructor
public class SkillEmbeddingController {

    private final SkillEmbeddingService skillEmbeddingService;

    @Operation(summary = "전체 스킬 임베딩", description = "DB에 저장된 모든 스킬을 벡터 임베딩합니다.")
    @PostMapping("/embed-all")
    public ResponseEntity<Void> embedAllSkills() {
        skillEmbeddingService.embedAllSkills();
        return ResponseEntity.ok().build();
    }

    @Operation(summary = "유사 스킬 추천", description = "입력 쿼리와 유사한 스킬을 추천합니다.")
    @GetMapping("/recommendation")
    public ResponseEntity<SimilarSkillResponses> searchSimilarSkills(
            @Parameter(description = "검색 쿼리") @RequestParam String query,
            @Parameter(description = "추천 결과 수 (기본값: 3)") @RequestParam(defaultValue = "3") int topK
    ) {
        SimilarSkillResponses results = skillEmbeddingService.findSimilarSkills(query, topK);
        return ResponseEntity.ok(results);
    }
}
